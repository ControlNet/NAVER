from PIL import Image

from hydra_vl4ai.util.console import logger

from .smb import NaverStateMemoryBank
from ..context.entity import Entity
from .perception import Perceptioner
from .logic_generation import LogicGenerator
from .logic_reasoning import LogicReasoner
from .answering import Answerer
from .states import PerceptionReturn, LogicGenerationReturn, LogicReasoningReturn, State, States, LogicAnsweringReturn


class Naver:

    def __init__(self, image_path: str, query: str):
        self.image_path = image_path
        self.image = Image.open(image_path)
        self.query = query
        self.state: State = States.Perception()  # init as perception state
        self.state_memory_bank = NaverStateMemoryBank()
        self.fallback_result: Entity | None = None

        # init components
        self.perceptioner = Perceptioner(self.image, query, self.state_memory_bank)
        self.logic_generator = LogicGenerator(self.query, self.state_memory_bank)
        self.logic_reasoner = LogicReasoner(self.state_memory_bank)
        self.answerer = Answerer(self.image, self.query, self.state_memory_bank)
        self.current_iter = 0  # the count for the self-corrections

    async def step(self) -> tuple[Entity | None, str]:
        # run one step in the Deterministic Finite-State Automaton (DFA)
        if self.current_iter > 5:
            logger.debug(f"[Iter {self.current_iter}] Exceed maximum iteration. Return fallback result.")
            return self.fallback_result or Entity(0, self.query, [0, 0, 0, 0], 0.), "Only Fallback"

        match self.state:
            # ------------ Perception State ------------
            case States.Perception(feedback):
                logger.debug(f"[Iter {self.current_iter}] Perception state with feedback: {feedback}")
                perception_return = await self.perceptioner.step(feedback)
                match perception_return:
                    case PerceptionReturn.MULTI_OBJECTS:
                        self.state = States.LogicGeneration()
                    case PerceptionReturn.SINGLE_OBJECT | PerceptionReturn.NO_OBJECT:
                        self.fallback_result, perception_fallback_return = self.perceptioner.fallback_step()
                        match perception_fallback_return:
                            case PerceptionReturn.NO_OBJECT:
                                self.state = States.Answering(None, None, 0)
                            case PerceptionReturn.SINGLE_OBJECT:
                                assert self.state_memory_bank.context is not None
                                self.state = States.Answering(self.state_memory_bank.context.first_entity, None, 0)
                    case PerceptionReturn.FAIL:
                        # just retry
                        self.current_iter += 1
                        self.state = States.Perception()

            # ------------ Logic Generation State ------------
            case States.LogicGeneration(feedback):
                logger.debug(f"[Iter {self.current_iter}] Logic Generation state")
                logic_generation_return, logic_query = await self.logic_generator.step(feedback)
                match logic_generation_return:
                    case LogicGenerationReturn.SUCCESS:
                        self.state = States.LogicReasoning(logic_query, 0)

            # ------------ Logic Reasoning State ------------
            case States.LogicReasoning(logic_query, skip_top):
                logger.debug(f"[Iter {self.current_iter}] Logic Reasoning state with target query: {logic_query}")
                logic_reasoning_return, logic_result = self.logic_reasoner.step(logic_query, skip_top)
                self.fallback_result, perception_fallback_return = self.perceptioner.fallback_step()
                match logic_reasoning_return:
                    case LogicReasoningReturn.SUCCESS:
                        self.state = States.Answering(logic_result, logic_query, skip_top)
                    case LogicReasoningReturn.EXCEED_TARGETS | LogicReasoningReturn.NO_TARGETS:
                        self.current_iter += 1
                        self.state = States.LogicGeneration("This code cannot find any target. Please correct it and provide a new code.")

            # ------------ Answering State ------------
            case States.Answering(None, None, skip_top):
                # if no logic result, we have to use the fallback result
                logger.debug(f"[Iter {self.current_iter}] Answering state with fallback result")
                return self.fallback_result, "Only Fallback"
            
            case States.Answering(logic_result, None, skip_top):
                logger.debug(f"[Iter {self.current_iter}] Answering state with fallback result")
                # if only one context entity with fallback result, we can directly return the result without further reasoning
                summarization_return, result, fb_text = await self.answerer.step(logic_result=logic_result, fallback_result=self.fallback_result)
                match summarization_return:
                    case LogicAnsweringReturn.YES:
                        return result, fb_text
                    case LogicAnsweringReturn.NO:
                        return self.fallback_result, "Only Fallback"

            case States.Answering(logic_result, logic_query, skip_top) if logic_query is not None:
                if logic_result is None:
                    logger.debug(f"[Iter {self.current_iter}] Answering state with fallback result")
                else:
                    logger.debug(f"[Iter {self.current_iter}] Answering state with logic result")
                summarization_return, result, fb_text = await self.answerer.step(logic_result=logic_result, fallback_result=self.fallback_result)
                match summarization_return:
                    case LogicAnsweringReturn.YES:
                        return result, fb_text
                    case LogicAnsweringReturn.NO:
                        self.current_iter += 1
                        self.state = States.LogicReasoning(logic_query, skip_top + 1)
            
        return None, ""

    async def run(self) -> Entity:
        # run the DFA until the result is found
        while True:
            result_entity, _ = await self.step()
            if result_entity is not None:
                break
        return result_entity
