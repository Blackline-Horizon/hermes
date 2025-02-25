from pydantic import BaseModel, Field
from typing import List
from datetime import date

class ReportCreate(BaseModel):

    title: str = Field(...)
    username: str = Field(...)
    created_at: date= Field(...)
    industry: str = Field(...)
    location: str = Field(...)
    alerts: List[str]= Field(...)


class ReportResponse(BaseModel):

    id: int
    title: str
    created_at: date
    industry: str
    pdf_id: int

    class Config:
        from_attributes = True  # Updated from `orm_mode` to `from_attributes`
