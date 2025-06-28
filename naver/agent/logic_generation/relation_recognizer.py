import numpy as np
from PIL import Image
from hydra_vl4ai.execution.image_patch import ImagePatch
from hydra_vl4ai.agent.smb.state_memory_bank import StateMemoryBank

from ...context.relation import SymbolicRelationEstimator, VlmRelationEstimator
from ...context.entity import Entity
from ...context.relation import Relation
from ...context.attribute import Attribute


class GeometryAnalyzer:
    def __init__(self, image_pil: Image.Image) -> None:
        self.image_pil = image_pil
        self.symbolic_relation_recognizer = SymbolicRelationEstimator(np.array(self.image_pil))

    def __call__(self, entity_a: Entity, entity_b: Entity) -> tuple[Relation, Relation]:
        a_to_b, b_to_a = self.symbolic_relation_recognizer.generate_bidirectional_geometry_relations(entity_a, entity_b)
        return Relation(entity_a.id, entity_b.id, a_to_b), Relation(entity_b.id, entity_a.id, b_to_a)


class UniversalRelationAnalyzer:
    def __init__(self, image_pil: Image.Image) -> None:
        self.image_pil = image_pil
        self.vlm_relation_recognizer = VlmRelationEstimator(np.array(self.image_pil))

    def __call__(self, entity_a: Entity, entity_b: Entity, relation_names: list[str]) -> tuple[Relation, Relation]:
        a_to_b, b_to_a = self.vlm_relation_recognizer.generate_bidirectional_relations(entity_a, entity_b, relation_names)
        return Relation(entity_a.id, entity_b.id, a_to_b), Relation(entity_b.id, entity_a.id, b_to_a)


class AttributeRecognizer:
    def __init__(self, image_pil: Image.Image) -> None:
        self.image = np.array(image_pil)

    def __call__(self, entity: Entity, attribute_name: str) -> Attribute:
        # crop the image
        bbox = entity.bbox
        cropped_image = Image.fromarray(self.image[bbox[1]:bbox[3], bbox[0]:bbox[2]])
        image_patch = ImagePatch(cropped_image, state_memory_bank=StateMemoryBank())
        attribute_confidence = image_patch.verify_property_score(entity.category, attribute_name)
        return Attribute(entity.id, attribute_name, attribute_confidence)
