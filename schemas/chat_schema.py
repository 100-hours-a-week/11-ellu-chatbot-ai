from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ChatRequest(BaseModel):
    message: str
    date: Optional[datetime] = None
    user_id: Optional[str] 