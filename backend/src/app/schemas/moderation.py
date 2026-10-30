from pydantic import BaseModel, Field

from app.models.enums import ModerationAction


class ModerationDecisionRequest(BaseModel):
    action: ModerationAction
    reason: str | None = Field(default=None, max_length=1000)
