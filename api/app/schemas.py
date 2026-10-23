from pydantic import BaseModel, Field


class PolicyQuestion(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class ImportSummary(BaseModel):
    imported: int
    rejected: int
    duplicates: int
    message: str
