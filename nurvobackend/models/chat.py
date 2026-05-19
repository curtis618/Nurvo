"""Chat and game session Pydantic models."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class SessionStatus(str, Enum):
    BRIEFING = "briefing"
    PLAYING = "playing"
    RECORDING = "recording"
    SCORING = "scoring"
    COMPLETED = "completed"


class ChatMessage(BaseModel):
    id: str
    sender: str  # "patient" | "family_0" | "family_1" | "family_2" | "nurse"
    content: str
    timestamp: datetime
    elapsed_seconds: float
    is_interjection: bool = False
    is_proactive: bool = False


class GameSession(BaseModel):
    session_id: str
    scenario_data: dict  # Raw scenario dict for flexibility
    conversation_history: list[ChatMessage] = []
    current_target: str = "patient"
    start_time: datetime | None = None
    status: SessionStatus = SessionStatus.BRIEFING
    patient_system_prompt: str = ""
    family_system_prompts: list[str] = []
    last_interjecting_family_index: int = -1
    last_activity_at: datetime | None = None
    is_user_active: bool = False
    proactive_streak: int = 0
    last_proactive_at: datetime | None = None
