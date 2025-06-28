import re
from hydra_vl4ai.util.console import logger

from .problog2scallop import translate_problog_rule_to_scallop
from ..smb import NaverStateMemoryBank
from ..states import LogicReasoningReturn
from ...context import Entity, Attribute
from ...context.relation import GEOMETRY_RELATIONS
from ...logic.scallop import ScallopModel


class LogicReasoner:

    def __init__(self, state_memory_bank: NaverStateMemoryBank) -> None:
        self.scallop_model = ScallopModel()
        self.state_memory_bank = state_memory_bank

    @property
    def _context(self):
        return self.state_memory_bank.context

    def step(self, logic_query: str, skip_top: int = 0) -> tuple[LogicReasoningReturn, Entity | None]:
        assert self._context is not None

        # convert all "relation" to "relation_" in scallop query to avoid conflict with built-in name
        logic_query = logic_query.replace("relation(", "relation_(")

        # in this block, we perceive the requested context from the logic query.
        # note in the paper, we put this step in the "Logic Generation" state.
        # but for simpler implementation, we put this step here.
        # if the attribute is requested
        attribute_names = re.findall(r'attribute\s*\(\s*.+?\s*,\s*"([^"]+)"\s*\)', logic_query)
        for attribute_name in set(attribute_names):
            self._context.generate_attribute(attribute_name)

        # if the non-geometry relation is requested, we need to generate the universal/generic relations
        relation_names = set(re.findall(r'relation_\s*\(\s*.+?\s*,\s*"([^"]+)"\s*\)', logic_query))
        non_geometry_relation_names = relation_names - set(GEOMETRY_RELATIONS)
        if len(non_geometry_relation_names) > 0:
            self._context.generate_relations(list(non_geometry_relation_names))

        # entity and relation in scallop langauge
        context_facts = self.scallop_model.context_to_scallop(self._context)
        # target query in scallop langauge
        logic_query = "\n".join([translate_problog_rule_to_scallop(row) for row in logic_query.split("\n") if row.strip() != ""])

        # if the query is extremely long, the Logic inference will be too slow, so we skip it and give a retry.
        # for main stream datasets (e.g. RefCOCO), most query is less than this limit.
        if len(logic_query) > 200:
            return LogicReasoningReturn.NO_TARGETS, None

        # merge the attribute declaration to the code
        code = f"{context_facts}\n{logic_query}\n" + "\n".join(map(Attribute.to_scallop_rel, self._context.attributes))

        # execute the logic model code
        targets = self.scallop_model.execute(code)
        logger.debug(f"Targets: {targets}")

        if len(targets) == 0:
            return LogicReasoningReturn.NO_TARGETS, None

        if skip_top >= len(targets):
            return LogicReasoningReturn.EXCEED_TARGETS, None

        # ranked by top confidence
        targets = list(targets.items())
        targets = sorted(targets, key=lambda x: x[1], reverse=True)[skip_top:]
        target = self._context.entities[max(targets, key=lambda x: x[1])[0]]
        return LogicReasoningReturn.SUCCESS, target
