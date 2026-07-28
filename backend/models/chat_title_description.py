
from pydantic import BaseModel, Field
class LLMTitleSchema(BaseModel):
    title: str = Field("New Chat", description="A short title of max 6 words for a chat conversation")
    description: str = Field("Chat Description", description = "A single short sentence description of a chat conversation")
