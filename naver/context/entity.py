from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Entity:
    num: int
    category: str
    bbox: list[int]
    bbox_confidence: float
    mask: np.ndarray | None = None
    
    _id: str | None = None

    @property
    def id(self) -> str:
        if self._id is None:
            self._id = self.category.replace(" ", "_") + "_" + str(self.num)
        return self._id

    @classmethod
    def new(cls, category: str, bbox: list[int], bbox_confidence: float, all_entities: list[Entity]) -> Entity:
        current_category_entities = filter(lambda x: x.category == category, all_entities)
        current_category_entity_id_nums = [*map(lambda x: x.num, current_category_entities)]
        max_nums = max(current_category_entity_id_nums) if len(current_category_entity_id_nums) > 0 else -1
        return cls(
            max_nums + 1,
            category,
            bbox,
            bbox_confidence
        )

    @classmethod
    def to_scallop_type(cls):
        return "type entity(id: String, category: String, x1: i32, y1: i32, x2: i32, y2: i32)"
    
    @classmethod
    def to_problog_type(cls):
        return r"% entity(ID: str, category: str, x1: int, y1: int, x2: int, y2: int)"

    def to_scallop_rel(self):
        x1, y1, x2, y2 = self.bbox
        return f"""rel {self.bbox_confidence}::entity("{self.id}", "{self.category}", {x1}, {y1}, {x2}, {y2})"""
    
    def to_problog_rel(self):
        x1, y1, x2, y2 = self.bbox
        return f"""{self.bbox_confidence}::entity("{self.id}", "{self.category}", {x1}, {y1}, {x2}, {y2})."""

    def to_statement(self):
        x1, y1, x2, y2 = self.bbox
        # round the bbox confidence to percentage
        bbox_conf = round(self.bbox_confidence * 100, 2)
        return f"""{self.id}: the {self.category} entity is at [{x1}, {y1}, {x2}, {y2}] (confidence: {bbox_conf}%)."""
