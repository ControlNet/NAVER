import logging
import tensorneko_util as N

from hydra_vl4ai.agent.llm import llm, llm_with_message
from hydra_vl4ai.util.config import Config
from hydra_vl4ai.util.console import logger
from problog.program import PrologString
from problog import get_evaluatable

from ._base import BaseLogicModel
from ..context.entity import Entity
from ..context.relation import GEOMETRY_RELATIONS, Relation
from ..context.context import Context

logging.getLogger("problog").setLevel(logging.WARN)


class ProbLogModel(BaseLogicModel):

    def __init__(self) -> None:
        super().__init__()

    def context_to_problog(self, context: Context) -> str:
        # convert context to problog language
        problog_rels = "\n".join(map(Entity.to_problog_rel, context.entities.values())) + "\n"
        problog_rels += "\n".join(map(Relation.to_problog_rel, context.relations))
        context_facts = f"""{Entity.to_problog_type()}
{Relation.to_problog_type()}

{problog_rels}"""
        return context_facts
        

    async def generate(self, context: Context, query: str, interested_entities: list[str], 
                       overwrite_feedback: str | None = None, previous_response: str | None = None) -> tuple[str, str]:
        context_facts = self.context_to_problog(context)
        
        # generate prompt
        assert (previous_response is None) == (overwrite_feedback is None), "Both previous_response and overwrite_feedback should be None or not None."
        if previous_response is None:
            prompt = gen_prompt_problog_query(context_facts, query, interested_entities)
            response = await llm(Config.base_config["llm_code_model"], prompt)
        else:
            previous_prompt = gen_prompt_problog_query(context_facts, query, interested_entities)
            response = await llm_with_message(Config.base_config["llm_code_model"], 
                [
                    {"role": "user", "content": previous_prompt}, 
                    {"role": "assistant", "content": previous_response}, 
                    {"role": "user", "content": overwrite_feedback} 
                ]
            )

        # add target rule and query
        logger.debug(f"ProbLog Code Generator: \n{response}")
        
        return response, context_facts

    def execute(self, code: str) -> dict[str, float]:
        code = f"{code}\nquery(target(ID))."
        model = PrologString(code)
        N.io.write.text("main_demo.pl", code)
        result = get_evaluatable().create_from(model).evaluate()
        return dict([(str(k.args[0]).strip('"'), v) for k, v in result.items() if v > 0])


def gen_prompt_problog_query(problog_code: str, query: str, interested_entities: list[str]) -> str:
    prompt = f"""You're an AI assistant designed to generate the ProbLog code (a logic programming language similar to Prolog). 

You need to generate a new rule "target" that will be used to query the target objects in the image based on given text prompt.

The preferred relation names are {GEOMETRY_RELATIONS}.

The names of entities are {interested_entities}.

The output is the code.

For example: 
```problog
target(ID) :- entity(ID, "<some category>", _, _, _, _), relation(ID, _, _).
```

More examples:
find the target "person left"
```problog
target(ID) :- entity(ID, "person", _, _, _, _), relation(ID, _, "left of"), relation(_, ID, "right of").
```

find the target "hot dog right"
```problog
target(ID) :- entity(ID, "hot dog", _, _, _, _), relation(ID, _, "right of"), relation(_, ID, "left of").
```

find the target "person right bottom"
```problog
target(ID) :- entity(ID, "person", _, _, _, _), relation(ID, _, "right of"), relation(_, ID, "left of"), relation(ID, _, "below of"), relation(_, ID, "above of").
```

find the target "woman on right in red"
```problog
target(ID) :- entity(ID, "woman", _, _, _, _), relation(ID, _, "right of"), relation(_, ID, "left of"), attribute(ID, "red").
```

Complete the following ProbLog code:
```problog
{problog_code}
```

Your output should be the ProbLog code.

find the target "{query}"
Your answer: """
    return prompt