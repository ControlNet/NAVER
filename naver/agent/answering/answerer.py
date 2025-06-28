from typing import Literal
import numpy as np
import torch
from PIL import Image
from tensorneko.evaluation.iou import iou_2d

from hydra_vl4ai.execution.toolbox import Toolbox
from hydra_vl4ai.util.config import Config
from hydra_vl4ai.util.console import logger

from ..smb import NaverStateMemoryBank
from ..states import LogicAnsweringReturn
from ...context import Entity
from ...utils.som import apply_som_for_one, apply_som_for_two


def _answerer_prompting_one_result(query: str, context_statement: str | None = None) -> str:
    context_statement = context_statement + "\n" if context_statement is not None else ""

    return f"""You're an image analyst designed to check if the highlighted object in the image meets the query description.

{context_statement}
The query is: "{query}"

Please check the highlighted object "A" in the image and answer the question: Does the highlighted object meet the query description? Your answer should be "Yes" or "No".
    
Your answer:"""


def _answerer_prompting_two_results(query: str, context_statement: str | None = None) -> str:
    context_statement = context_statement + "\n" if context_statement is not None else ""
    return f"""You're an image analyst designed to check if the highlighted objects in the image meets the query description, and which one is more likely to meet the query description.

{context_statement}
The query is: "{query}"

Please check the highlighted object "A" and "B" in the image and answer the question: Which object is more likely to meet the query description, or none of them meet the query description? Your answer should be "A", "B" or "None".

Your answer:"""


class Answerer:

    def __init__(self, image: Image.Image, query: str, state_memory_bank: NaverStateMemoryBank) -> None:
        self.image = np.asarray(image)
        self.state_memory_bank = state_memory_bank
        self.query = query

    def _vlm_predict(self, image: np.ndarray, prompt: str, threshold: float, two_target: bool = False) -> Literal["Yes", "No", "A", "B", "None"]:
        vlm_model = Config.base_config["vlm_model"]
        match vlm_model:
            case "internvl2":
                if two_target:
                    answer = Toolbox.consumers["internvl2"].model.forward_next_word_prediction(image, prompt, ["A", "B", "None"])
                    logger.debug(f"Summarizer Answer: {answer}")
                    answer = dict(answer)
                    answer = max(answer, key=lambda x: answer[x])
                else:
                    answer = Toolbox.consumers["internvl2"].model.forward_next_word_prediction(image, prompt, ["Yes", "No"])
                    logger.debug(f"Summarizer Answer: {answer}")
                    answer = "Yes" if dict(answer)["Yes"] > threshold else "No"
                return answer
            case _:
                raise ValueError(f"Invalid VLM model {vlm_model} for answering.")

    async def _step_one_result(self, result: Entity, threshold=0.5, context_statement: str | None = None) -> tuple[LogicAnsweringReturn, Entity | None]:
        if result.mask is None:
            result.mask = Toolbox["sam"].forward(self.image, result.bbox, False)
        mask_a = result.mask
        prompt_image = apply_som_for_one(self.image, mask_a, "red", anno_mode=["Mask", "Box", "Mark"])
        prompt_text = _answerer_prompting_one_result(self.query, context_statement)

        answer = self._vlm_predict(prompt_image, prompt_text, threshold, two_target=False)
        if answer == "Yes":
            return LogicAnsweringReturn.YES, result

        return LogicAnsweringReturn.NO, None

    async def _step_two_results(self, fallback_result: Entity, logic_result: Entity, context_statement: str | None = None) -> tuple[LogicAnsweringReturn, Entity | None, str]:
        if fallback_result.mask is None:
            fallback_result.mask = Toolbox["sam"].forward(self.image, fallback_result.bbox, False)

        if logic_result.mask is None:
            logic_result.mask = Toolbox["sam"].forward(self.image, logic_result.bbox, False)

        mask_a = fallback_result.mask
        mask_b = logic_result.mask

        prompt_image = apply_som_for_two(self.image, mask_a, mask_b, "red", "blue", ["Mask", "Box", "Mark"])
        prompt_text = _answerer_prompting_two_results(self.query, context_statement)

        answer = self._vlm_predict(prompt_image, prompt_text, 0.5, two_target=True)
        match answer:
            case "A":
                return LogicAnsweringReturn.YES, fallback_result, "Fallback"
            case "B":
                return LogicAnsweringReturn.YES, logic_result, "Logic"
            case "None":
                return LogicAnsweringReturn.NO, None, ""
            case _:
                raise ValueError(f"Invalid answer: {answer}")

    async def step(self, fallback_result: Entity | None, logic_result: Entity | None = None, context_statement: str | None = None) -> tuple[LogicAnsweringReturn, Entity | None, str]:
        assert fallback_result is not None

        # the fallback result and logic result is the bbox of the object
        if logic_result is None:
            return (await self._step_one_result(fallback_result, context_statement=context_statement)) + ("Only Fallback",)

        # if both results are available, we firstly compare if they are the same
        iou = iou_2d(
            torch.tensor([fallback_result.bbox]),
            torch.tensor([logic_result.bbox]),
        )[0, 0].item()
        if iou > 0.8:
            logger.debug("The two results are the same, we only need to check one.")
            return (await self._step_one_result(fallback_result, 0.1, context_statement)) + ("Both overlap",)

        return await self._step_two_results(fallback_result, logic_result, context_statement)