from pydantic import BaseModel, Field
from typing import List
from datetime import date

class ReportCreate(BaseModel):

    username: str = Field(...)
    title: str = Field(...)
    date_start: date= Field(...)
    date_end: date= Field(...)
    industry: List[str] = Field(...)
    continents: List[str] = Field(...)
    alerts: List[str]= Field(...)
    devices: List[str] = Field(...)
    resolutions: List[str] = Field(...)
    events: List[str]=Field(...)


class ReportResponse(BaseModel):

    id: int
    title: str
    date_start: date
    date_end: date
    industry: list
    pdf_id: int

    class Config:
        from_attributes = True  # Updated from `orm_mode` to `from_attributes`
