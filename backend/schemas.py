from pydantic import BaseModel
from typing import Optional, List, Dict

class ProfileUpdateRequest(BaseModel):
    persona: str
    preferred_language: str
    
class BriefingRequest(BaseModel):
    topic: str
    
class FollowUpRequest(BaseModel):
    context_type: str
    context_text: str
    query: str
    history: List[Dict[str, str]] = []
