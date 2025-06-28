from enum import Enum
from dataclasses import dataclass, field
from typing import Union

from ..context.entity import Entity

@dataclass
class _PerceptionState:
    feedback: str | None = field(default=None)

@dataclass
class _LogicGenerationState:
    feedback: str | None = field(default=None)

@dataclass
class _LogicReasoningState:
    logic_query: str
    skip_top: int

@dataclass
class _AnsweringState:
    logic_result: Entity | None
    target_rule: str | None
    skip_top: int

State = Union[_PerceptionState, _LogicGenerationState, _LogicReasoningState, _AnsweringState]

class States:
    Perception = _PerceptionState
    LogicGeneration = _LogicGenerationState
    LogicReasoning = _LogicReasoningState
    Answering = _AnsweringState


class PerceptionReturn(Enum):
    MULTI_OBJECTS = 1
    SINGLE_OBJECT = 2
    NO_OBJECT = 3
    FAIL = 4


class LogicGenerationReturn(Enum):
    SUCCESS = 1
    RESPONSE_FORMAT_ERROR = 2


class LogicReasoningReturn(Enum):
    SUCCESS = 1
    EXCEED_TARGETS = 2
    NO_TARGETS = 3


class LogicAnsweringReturn(Enum):
    YES = 1
    NO = 2
