from ..smb import NaverStateMemoryBank
from ..states import LogicGenerationReturn
from ...logic.problog import ProbLogModel


class LogicGenerator:
    def __init__(self, query: str, state_memory_bank: NaverStateMemoryBank) -> None:
        self.problog_model = ProbLogModel()
        self.state_memory_bank = state_memory_bank
        self.query = query
        self.previous_response = None

    @property
    def _context(self):
        return self.state_memory_bank.context

    async def step(self, overwrite_feedback: str | None = None) -> tuple[LogicGenerationReturn, str]:
        assert self._context is not None
        previous_response = self.previous_response if overwrite_feedback is not None else None
        response, _ = await self.problog_model.generate(
            self._context, self.query, self._context.entity_categories, overwrite_feedback=overwrite_feedback, previous_response=previous_response)
        self.previous_response = response
        # target_rule = json.loads(response)["output"]
        # match the code within the response ```problog ... ```
        try:
            target_rule_problog = response.split("```problog")[1].split("```")[0].strip()
        except IndexError:
            target_rule_problog = response

        return LogicGenerationReturn.SUCCESS, target_rule_problog
