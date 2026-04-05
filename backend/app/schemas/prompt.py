from datetime import datetime

from pydantic import BaseModel


class SystemPromptResponse(BaseModel):
    purpose: str
    display_name: str
    content: str
    is_editable: bool
    updated_at: datetime

    model_config = {"from_attributes": True}


class SystemPromptUpdate(BaseModel):
    content: str
