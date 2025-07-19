from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    date: Optional[datetime] = None
    user_id: Optional[str]

class CalendarQueryRequest(BaseModel):
    user_id: str
    start: str  
    end: str   
    task_title_keyword: str
    category: str

class CalendarQueryResult(BaseModel):
    task_title: str
    sub_title: str
    start_at: str 
    end_at: str 

class CalendarQueryResponse(BaseModel):
    message: str
    data: list[CalendarQueryResult] 