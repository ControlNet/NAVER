import json
from typing import AsyncGenerator

from hydra_vl4ai.agent.llm import llm_with_message
from hydra_vl4ai.util.config import Config

from .captioner import Captioner


_system_prompt = """You're an AI assistant designed to find detailed information from image.

You need to find important objects based on the given query which is the object you need to find. The query normally is a set of words which includes a object name and the attributes of the object.

Here are some examples:
Query: "hot dog left"
Answer: ["hot dog"]

Query: "red apple"
Answer: ["apple"]

Query: "person in blue"
Answer: ["person"]

Query: "woman right"
Answer: ["woman"]

Query: "bird flying"
Answer: ["bird"]

Query: "right guy"
Answer: ["person"]

Query: "adult talking to the kids"
Answer: ["adult", "kid"]

Query: "green shirt"
Answer: ["shirt"]

Query: "woman in red"
Answer: ["woman"]

Your output must be a JSON object contains the flatten list of string. For example: {"output": ["apple", "orange", "chair", "umbrella"]}"""


def _gen_prompt_generate_entity_with_caption(caption: str, query: str, extra: str = ""):
    prompt = f"""Caption: {caption}

Query: {query}

Your answer:"""
    if extra != "":
        prompt += f"\n{extra}"
    return prompt


def _gen_prompt_generate_entity(query: str, extra: str = ""):
    prompt = f"""Query: {query}

Your answer:"""
    if extra != "":
        prompt += f"\n{extra}"
    return prompt


class EntityCategoryExtractor:
    """The Entity Category Extractor (ECE) in perception state."""

    def __init__(self, query: str, captioner: Captioner) -> None:
        self.query = query
        self.captioner = captioner
        self.interested_entities = []

    async def __call__(self, overwrite_feedback: str | None = None, max_trials: int = 3):
        if overwrite_feedback is not None:
            messages = [
                {"role": "system", "content": _system_prompt},
                {"role": "user", "content": _gen_prompt_generate_entity(self.query, "")},
                {"role": "assistant", "content": str(self.interested_entities)},
                {"role": "user", "content": _gen_prompt_generate_entity(self.query, overwrite_feedback)}
            ]
        else:
            messages = None
        entity_generator = self._build_generator(messages=messages)

        feedback = ""
        use_caption = False  # we firstly not use the caption for efficiency, if failed, then use the caption
        init = True

        for _ in range(max_trials):
            self.interested_entities = await entity_generator.asend((feedback, use_caption)) if not init else await entity_generator.asend(None)
            init = False
            if len(self.interested_entities) == 0:
                feedback = "You didn't give any important objects. Please find at least one object."
                use_caption = True
            elif len(self.interested_entities) > 3:
                feedback = "You gave too many objects. Please find at most three objects."
                use_caption = False
            else:
                break

        await entity_generator.aclose()
        return self.interested_entities

    async def _build_generator(self, messages: list[dict[str, str]] | None = None) -> AsyncGenerator[list[str], tuple[str, bool]]:
        query = self.query
        messages = messages or [{"role": "system", "content": _system_prompt}]
        extra = ""
        use_caption = False
        while True:
            if use_caption:
                prompt_interested_entities = _gen_prompt_generate_entity_with_caption(self.captioner(), query, extra)
            else:
                prompt_interested_entities = _gen_prompt_generate_entity(query, extra)
            messages.append({"role": "user", "content": prompt_interested_entities})
            interested_entities = json.loads(await llm_with_message(Config.base_config["llm_model"], messages, "json"))
            if "output" not in interested_entities:
                extra = """Your output must be a JSON object contains the flatten list of string. For example: {"output": ["apple", "orange", "chair", "umbrella"]}"""
                continue

            interested_entities = interested_entities["output"]
            messages.append({"role": "assistant", "content": str(interested_entities)})
            extra, use_caption = yield interested_entities
