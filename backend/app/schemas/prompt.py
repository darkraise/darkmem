from pydantic import BaseModel


class SystemPromptResponse(BaseModel):
    name: str
    display_name: str
    content: str
    extraction_depth: str
    is_default: bool

    model_config = {"from_attributes": True}
