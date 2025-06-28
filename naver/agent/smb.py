from hydra_vl4ai.agent.smb import StateMemoryBank
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..context.context import Context

class NaverStateMemoryBank(StateMemoryBank):
    def __init__(self):
        super().__init__()
        self.context: Context | None = None
        self.caption: str = ""
        self.code: str = ""

    def reset(self):
        self.context = None
        self.caption = ""
        self.code = ""
        return super().reset()
