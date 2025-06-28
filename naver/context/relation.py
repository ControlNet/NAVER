from __future__ import annotations
import abc
from dataclasses import dataclass
from typing import TypedDict

import numpy as np
import tensorneko as N
import torch

from hydra_vl4ai.execution.toolbox import Toolbox
from hydra_vl4ai.util.config import Config

from ..utils.misc import clean_cache
from ..utils.som import apply_som_for_two
from .entity import Entity

GEOMETRY_RELATIONS = [
    "is",
    "next to",
    "contains",
    "inside",
    "left of",
    "right of",
    "above of",
    "below of",
    "front of",
    "behind of",
]


@dataclass
class Relation:
    subject_entity_id: str
    object_entity_id: str
    relation_name: list[tuple[str, float]]
    # scallop "relation" is a built-in name, so we have to use "relation_" instead.

    @classmethod
    def to_scallop_type(cls):
        return "type relation_(subject: String, object: String, relation_name: String)"
    
    @classmethod
    def to_problog_type(cls):
        return r"% relation(subject: str, object: str, relation_name: str)"

    def to_scallop_rel(self):
        scallop_rels = [
            f"""rel {prob}::relation_("{self.subject_entity_id}", "{self.object_entity_id}", "{rel}")"""
            for rel, prob in self.relation_name
        ]
        return "\n".join(scallop_rels)
    
    def to_problog_rel(self):
        problog_rels = [
            f"""{prob}::relation("{self.subject_entity_id}", "{self.object_entity_id}", "{rel}")."""
            for rel, prob in self.relation_name
        ]
        return "\n".join(problog_rels)
    
    def to_statement(self, threshold: float = 0.5):
        statements = [
            f"""{self.subject_entity_id}: the {self.subject_entity_id} is {rel if rel != "is" else ""} {self.object_entity_id} (confidence: {round(prob * 100, 2)}%)."""
            for rel, prob in self.relation_name
            if prob >= threshold
        ]
        return "\n".join(statements)


class RelationEstimator(abc.ABC):
    
    def __init__(self, image: np.ndarray) -> None:
        self.image = image

    def generate_bidirectional_geometry_relations(self, entity_a: Entity, entity_b: Entity) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        a_to_b, b_to_a = N.util.try_until_success(
            self.generate_geometry_relations, entity_a, entity_b, max_trials=5,
            exception_callback=lambda _: clean_cache()
        )
        return a_to_b, b_to_a
    
    @abc.abstractmethod
    def generate_geometry_relations(self, entity_a: Entity, entity_b: Entity) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        pass


class EntityPromptDict(TypedDict):
    entity: Entity
    color: str


class VlmRelationEstimator(RelationEstimator):
        
    def generate_geometry_relations(self, entity_a: Entity, entity_b: Entity) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        return self.generate_relations(entity_a, entity_b, GEOMETRY_RELATIONS)
    
    def generate_relations(self, entity_a: Entity, entity_b: Entity, relation_names: list[str]) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        a_to_b_prompt, b_to_a_prompt = _relation_prompting(
            {"entity": entity_a, "color": "red"}, 
            {"entity": entity_b, "color": "blue"}, 
            relation_names
        )

        if entity_a.mask is None:
            entity_a.mask = Toolbox["sam"].forward(self.image, entity_a.bbox, False)
        mask_a = entity_a.mask
        if entity_b.mask is None:
            entity_b.mask = Toolbox["sam"].forward(self.image, entity_b.bbox, False)
        mask_b = entity_b.mask

        a_to_b_prompt_image = apply_som_for_two(self.image, mask_a, mask_b, "red", "blue", ["Mask", "Box", "Mark"])
        b_to_a_prompt_image = apply_som_for_two(self.image, mask_b, mask_a, "blue", "red", ["Mask", "Box", "Mark"])

        if Config.base_config["vlm_model"] == "internvl2":
            a_to_b = Toolbox.consumers["internvl2"].model.forward_next_word_prediction(a_to_b_prompt_image, a_to_b_prompt, relation_names)
            b_to_a = Toolbox.consumers["internvl2"].model.forward_next_word_prediction(b_to_a_prompt_image, b_to_a_prompt, relation_names)
        else:
            raise NotImplementedError(f"VLM model {Config.base_config['vlm_model']} is not supported.")

        return a_to_b, b_to_a
    
    def generate_bidirectional_relations(self, entity_a: Entity, entity_b: Entity, relation_names: list[str]) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        a_to_b, b_to_a = N.util.try_until_success(
            self.generate_relations, entity_a, entity_b, relation_names, max_trials=5,
            exception_callback=lambda _: clean_cache()
        )
        return a_to_b, b_to_a
    

def _relation_prompting(entity_1: EntityPromptDict, entity_2: EntityPromptDict, relations: list[str]) -> list[str]:
    # entity_1 is {"entity": Entity, "color": "<COLOR FOR BBOX>"}
    # entity_2 is ...

    start_desc = """You're an AI assistant designed to find the relations of entities in the given image. 

The interested entities are highlighted by bounding boxes. They are:
"""

    obj1_desc = f"""the "{entity_1["entity"].category}" labeled by {entity_1["color"]} bounding box {entity_1["entity"].bbox}."""
    obj2_desc = f"""the "{entity_2["entity"].category}" labeled by {entity_2["color"]} bounding box {entity_2["entity"].bbox}."""

    end_desc = f"""The potential relations are {relations}.
For the relation A to B, you need to output exact the one relation from provided above. 

Your answer:"""
    objs_desc_list = (
        f"A: {obj1_desc}\nB: {obj2_desc}\n",
        f"A: {obj2_desc}\nB: {obj1_desc}\n",
    )
    
    return [f"{start_desc}\n{objs_desc}\n{end_desc}" for objs_desc in objs_desc_list]


def _sigmoid(z):
    return 1/(1 + np.exp(-z))


class SymbolicRelationEstimator(RelationEstimator):

    def __init__(self, image: np.ndarray) -> None:
        super().__init__(image)
        # a depth np array with same resolution as image, 0 means close, 1 means most far
        self.depth = Toolbox[Config.base_config["depth_model"]].forward(self.image)
        self.image_height = self.image.shape[0]
        self.image_width = self.image.shape[1]
        
    def generate_geometry_relations(self, entity_a: Entity, entity_b: Entity) -> tuple[list[tuple[str, float]], list[tuple[str, float]]]:
        if entity_a.mask is None:
            entity_a.mask = Toolbox["sam"].forward(self.image, entity_a.bbox, False)
        mask_a = entity_a.mask
        assert mask_a is not None
        if entity_b.mask is None:
            entity_b.mask = Toolbox["sam"].forward(self.image, entity_b.bbox, False)
        mask_b = entity_b.mask
        assert mask_b is not None

        # we find the depth of object as the average depth of the mask
        depth_a = np.mean(self.depth[mask_a])
        depth_b = np.mean(self.depth[mask_b])

        # we use the coordinate in image and the depth to find the relations
        a_to_b = self._generate_a_to_b_relation(entity_a, entity_b, mask_a, mask_b, depth_a, depth_b)
        b_to_a = self._generate_a_to_b_relation(entity_b, entity_a, mask_b, mask_a, depth_b, depth_a)

        return a_to_b, b_to_a
    
    def _generate_a_to_b_relation(self, entity_a: Entity, entity_b: Entity, mask_a: np.ndarray, mask_b: np.ndarray, depth_a: float, depth_b: float) -> list[tuple[str, float]]:
        ALPHA = 5

        # relation of "is", use the IoU score of the bbox
        prob_is = N.evaluation.iou_2d(
            torch.tensor(entity_a.bbox).unsqueeze(0), 
            torch.tensor(entity_b.bbox).unsqueeze(0)
        )[0, 0].item()

        # relation of "next to", use the distance between the center of the object
        center_a = np.array([np.mean([entity_a.bbox[0], entity_a.bbox[2]]) / self.image_width, np.mean([entity_a.bbox[1], entity_a.bbox[3]]) / self.image_height])
        center_b = np.array([np.mean([entity_b.bbox[0], entity_b.bbox[2]]) / self.image_width, np.mean([entity_b.bbox[1], entity_b.bbox[3]]) / self.image_height])
        # combined with depth
        center_a_with_depth = np.array([center_a[0], center_a[1], depth_a])
        center_b_with_depth = np.array([center_b[0], center_b[1], depth_b])
        distance = np.linalg.norm(center_a_with_depth - center_b_with_depth) / np.sqrt(3)
        prob_next_to = np.exp(-ALPHA * distance) * (1 - prob_is)

        # relation of "contains", 
        mask_b_in_a = np.logical_and(mask_a, mask_b)
        mask_a_in_b = np.logical_and(mask_b, mask_a)
        prob_contains = mask_b_in_a.sum() / mask_b.sum() if mask_b.sum() > 0 else 0
        prob_inside = mask_a_in_b.sum() / mask_a.sum() if mask_a.sum() > 0 else 0
        
        prob_left_of = _sigmoid(ALPHA * (center_b[0] - center_a[0]))
        prob_right_of = _sigmoid(ALPHA * (center_a[0] - center_b[0]))
        prob_above_of = _sigmoid(ALPHA * (center_a[1] - center_b[1]))
        prob_below_of = _sigmoid(ALPHA * (center_b[1] - center_a[1]))

        prob_front_of = _sigmoid(ALPHA * (depth_b - depth_a))
        prob_behind_of = _sigmoid(ALPHA * (depth_a - depth_b))

        return [
            ("is", prob_is),
            ("next to", prob_next_to),
            ("contains", prob_contains),
            ("inside", prob_inside),
            ("left of", prob_left_of),
            ("right of", prob_right_of),
            ("above of", prob_above_of),
            ("below of", prob_below_of),
            ("front of", prob_front_of),
            ("behind of", prob_behind_of),
        ]
