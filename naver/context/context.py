from __future__ import annotations

import numpy as np
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, TimeRemainingColumn
from typing import TYPE_CHECKING

from hydra_vl4ai.execution.image_patch import ImagePatch

from ..utils.misc import clean_cache
from .entity import Entity
from .relation import Relation
from .attribute import Attribute

if TYPE_CHECKING:
    from ..agent.logic_generation.relation_recognizer import GeometryAnalyzer, UniversalRelationAnalyzer, AttributeRecognizer


class Context:
    def __init__(
            self, 
            image: np.ndarray, 
            geometry_analyzer: GeometryAnalyzer, 
            universal_relation_analyzer: UniversalRelationAnalyzer, 
            attribute_recognizer: AttributeRecognizer
        ) -> None:
        self.image = image
        self.entities: dict[str, Entity] = {}
        self.relations: list[Relation] = []
        self.attributes: list[Attribute] = []
        self.geometry_analyzer = geometry_analyzer
        self.universal_relation_analyzer = universal_relation_analyzer
        self.attribute_recognizer = attribute_recognizer

    @property
    def entity_categories(self) -> list[str]:
        return list(set([entity.category for entity in self.entities.values()]))
    
    @property
    def first_entity(self) -> Entity | None:
        entities = list(self.entities.values())
        return entities[0] if len(entities) > 0 else None

    def init_entities(self, find_output: dict[str, list[ImagePatch]]) -> None:
        interested_entities_valid = [k for k, v in find_output.items() if len(v) > 0]
        result = []
        for entity_name in interested_entities_valid:
            patches = find_output[entity_name]
            for patch in patches:
                bbox = patch.to_bbox()
                result.append(Entity.new(entity_name, bbox[:4], bbox[4], result))
        self.entities = {entity.id: entity for entity in result}

    def generate_geometry_relations(self) -> None:
        # build relations for each entities pair
        entity_ids = list(self.entities.keys())
        pairs = []
        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                pairs.append((entity_ids[i], entity_ids[j]))
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("Generate Geometry Relations...", total=len(pairs))
            clean_cache()
            for entity_a_id, entity_b_id in pairs:
                entity_a = self.entities[entity_a_id]
                entity_b = self.entities[entity_b_id]
                a_to_b, b_to_a = self.geometry_analyzer(entity_a, entity_b)
                self.relations.append(a_to_b)
                self.relations.append(b_to_a)
                progress.update(task, advance=1)
        
    def generate_relations(self, relation_names: list[str]) -> None:
        # build relations for each entities pair
        entity_ids = list(self.entities.keys())
        pairs = []
        for i in range(len(entity_ids)):
            for j in range(i + 1, len(entity_ids)):
                pairs.append((entity_ids[i], entity_ids[j]))
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("Generate Universal Relations...", total=len(pairs))
            clean_cache()
            for entity_a_id, entity_b_id in pairs:
                entity_a = self.entities[entity_a_id]
                entity_b = self.entities[entity_b_id]
                a_to_b, b_to_a = self.universal_relation_analyzer(entity_a, entity_b, relation_names)
                self.relations.append(a_to_b)
                self.relations.append(b_to_a)
                progress.update(task, advance=1)
        
    def generate_attribute(self, attribute_name: str):
        entity_ids = list(self.entities.keys())
        with Progress(
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TextColumn("({task.completed}/{task.total})"),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        ) as progress:
            task = progress.add_task("Generate Attribute...", total=len(entity_ids))
            for entity_id in entity_ids:
                entity = self.entities[entity_id]
                self.attributes.append(self.attribute_recognizer(entity, attribute_name))
                progress.update(task, advance=1)
