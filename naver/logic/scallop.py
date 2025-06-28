import scallopy

from ._base import BaseLogicModel
from ..context.entity import Entity
from ..context.relation import Relation
from ..context.context import Context


class ScallopModel(BaseLogicModel):

    def __init__(self) -> None:
        super().__init__()

    def context_to_scallop(self, context: Context) -> str:
        # convert context to scallop language
        scallop_rels = "\n".join(map(Entity.to_scallop_rel, context.entities.values())) + "\n"
        scallop_rels += "\n".join(map(Relation.to_scallop_rel, context.relations))
        context_facts = f"""{Entity.to_scallop_type()}
{Relation.to_scallop_type()}

{scallop_rels}"""
        return context_facts

    async def generate(self, context: Context, query: str, interested_entities: list[str], 
                       overwrite_feedback: str | None = None, previous_response: str | None = None) -> tuple[str, str]:
        raise NotImplementedError("ScallopModel does not support generate method.")
    
    def execute(self, code: str) -> dict[str, float]:
        ctx = scallopy.ScallopContext("topkproofs")
        try:
            ctx.add_program(code)
        except Exception as e:
            import pdb; pdb.set_trace()
        ctx.run()
        result = list(ctx.relation("target"))
        result_dict = {entity[0]: confidence for confidence, entity in result if confidence > 0.}
        return result_dict
