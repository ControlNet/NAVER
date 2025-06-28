from __future__ import annotations

from PIL import Image
import numpy as np
import torchvision.transforms.functional as T
from hydra_vl4ai.execution.image_patch import ImagePatch
from hydra_vl4ai.util.config import Config
from hydra_vl4ai.util.console import logger

from ..states import PerceptionReturn
from ...context import Context, Entity
from ...context.relation import SymbolicRelationEstimator, VlmRelationEstimator
from ..logic_generation.relation_recognizer import GeometryAnalyzer, UniversalRelationAnalyzer, AttributeRecognizer
from ..smb import NaverStateMemoryBank

from .captioner import Captioner
from .entity_category_extractor import EntityCategoryExtractor
from .entity_detector import EntityDetector


class Perceptioner:
    """The pipeline in perception state."""

    def __init__(self, image: Image.Image, query: str, state_memory_bank: NaverStateMemoryBank) -> None:
        self.image_pil = image
        self.image_patch = ImagePatch(image, state_memory_bank=state_memory_bank)
        self.state_memory_bank = state_memory_bank
        self.query = query

        # Captioner (image -> caption, when needed)
        self.captioner = Captioner(self.image_patch, state_memory_bank)

        # Entity Category Extractor (query -> categories)
        self.entity_category_extractor = EntityCategoryExtractor(query, self.captioner)

        # Entity Detector (image + categories -> entities)
        self.entity_detector = EntityDetector(self.image_patch)

    def _init_context(self, interested_entities_patch: dict[str, list[ImagePatch]]):
        geometry_analyzer = GeometryAnalyzer(self.image_pil)
        universal_relation_analyzer = UniversalRelationAnalyzer(self.image_pil)
        attribute_recognizer = AttributeRecognizer(self.image_pil)

        context = Context(np.array(T.to_pil_image(self.image_patch.cropped_image)), 
                          geometry_analyzer, 
                          universal_relation_analyzer, 
                          attribute_recognizer)

        self.state_memory_bank.context = context
        context.init_entities(interested_entities_patch)
        logger.debug(f"Context Entities: {context.entities}")
        if len(context.entities) > 1:
            context.generate_geometry_relations()
            return PerceptionReturn.MULTI_OBJECTS
        elif len(context.entities) == 1:
            return PerceptionReturn.SINGLE_OBJECT
        elif len(context.entities) == 0:
            return PerceptionReturn.NO_OBJECT
        else:
            return PerceptionReturn.FAIL

    async def step(self, overwrite_feedback: str | None = None) -> PerceptionReturn:
        categories = await self.entity_category_extractor(overwrite_feedback)
        entities = self.entity_detector(categories)
        # note the generation of geometry-based relations are handled here for simplicity.
        # this will build the entities and the geometry-based relations as the logic context.
        # this can enrich the prior knowledge for Logic Query Generator.
        return_value = self._init_context(entities)
        return return_value

    def fallback_step(self) -> tuple[Entity | None, PerceptionReturn]:
        match Config.base_config["task"]:
            case "grounding":
                return self._fallback_grounding_step()
            case _:
                raise NotImplementedError(f"Fallback step for task {Config.base_config['task']} is not implemented.")
        
    def _fallback_grounding_step(self) -> tuple[Entity | None, PerceptionReturn]:
        # generate based on the grounding method
        # we temporally set a lower grounding threshold for the fallback
        prev_threshold = Config.base_config["florence2_threshold"]
        Config.base_config["florence2_threshold"] = 0.1
        patches = self.entity_detector([self.query])
        Config.base_config["florence2_threshold"] = prev_threshold  # reset the threshold

        if len(patches) == 0:
            return None, PerceptionReturn.NO_OBJECT
        else:
            # find the highest confidence one
            highest_confidence_patch = sorted(
                patches[self.query], 
                key=lambda image_patch: image_patch.confidence, 
                reverse=True)[0]
            
            fallback_result = Entity(0, self.query, highest_confidence_patch.to_bbox()[:4], highest_confidence_patch.confidence)
            
            return fallback_result, PerceptionReturn.SINGLE_OBJECT
