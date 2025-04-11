from pydantic import BaseModel
from typing import List, Dict, Any, Optional
# Định nghĩa các model Pydantic:
class HealthInfo(BaseModel):
    age: Optional[int] = None
    gender: Optional[str] = None
    weight: Optional[float] = None
    height: Optional[float] = None
    activity_level: Optional[str] = None
    goals: Optional[List[str]] = None
    restrictions: Optional[List[str]] = None
    allergies: Optional[List[str]] = None

class MealPreferences(BaseModel):
    meal_type: Optional[str] = None
    cuisine: Optional[str] = None
    time_constraint: Optional[int] = None

class MealSuggestionRequest(BaseModel):
    session_id: Optional[str] = None
    user_id: Optional[int] = None
    health_info: HealthInfo
    preferences: MealPreferences
    family_size: Optional[int] = 1

class QueryRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    user_id: Optional[int] = None
    health_info: Optional[HealthInfo] = None

class NewSessionRequest(BaseModel):
    user_id: Optional[int] = None