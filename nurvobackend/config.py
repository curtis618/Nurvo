"""Application configuration loaded from environment variables."""

import os

from dotenv import load_dotenv

load_dotenv()


OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
ELEVENLABS_API_KEY: str = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_PATIENT_VOICE_ID: str = os.getenv("ELEVENLABS_PATIENT_VOICE_ID", "")
ELEVENLABS_PATIENT_MALE_VOICE_ID: str = os.getenv(
    "ELEVENLABS_PATIENT_MALE_VOICE_ID",
    ELEVENLABS_PATIENT_VOICE_ID,
)
ELEVENLABS_PATIENT_FEMALE_VOICE_ID: str = os.getenv(
    "ELEVENLABS_PATIENT_FEMALE_VOICE_ID",
    ELEVENLABS_PATIENT_VOICE_ID,
)
ELEVENLABS_FAMILY_VOICE_ID_0: str = os.getenv(
    "ELEVENLABS_FAMILY_VOICE_ID_0",
    os.getenv("ELEVENLABS_FAMILY_VOICE_ID", ""),
)
ELEVENLABS_FAMILY_VOICE_ID_1: str = os.getenv(
    "ELEVENLABS_FAMILY_VOICE_ID_1",
    os.getenv("ELEVENLABS_FAMILY_VOICE_ID", ""),
)
ELEVENLABS_FAMILY_VOICE_ID_2: str = os.getenv(
    "ELEVENLABS_FAMILY_VOICE_ID_2",
    os.getenv("ELEVENLABS_FAMILY_VOICE_ID", ""),
)
ELEVENLABS_FAMILY_0_MALE_VOICE_ID: str = os.getenv(
    "ELEVENLABS_FAMILY_0_MALE_VOICE_ID",
    ELEVENLABS_FAMILY_VOICE_ID_0,
)
ELEVENLABS_FAMILY_0_FEMALE_VOICE_ID: str = os.getenv(
    "ELEVENLABS_FAMILY_0_FEMALE_VOICE_ID",
    ELEVENLABS_FAMILY_VOICE_ID_0,
)
ELEVENLABS_FAMILY_1_MALE_VOICE_ID: str = os.getenv(
    "ELEVENLABS_FAMILY_1_MALE_VOICE_ID",
    ELEVENLABS_FAMILY_VOICE_ID_1,
)
ELEVENLABS_FAMILY_1_FEMALE_VOICE_ID: str = os.getenv(
    "ELEVENLABS_FAMILY_1_FEMALE_VOICE_ID",
    ELEVENLABS_FAMILY_VOICE_ID_1,
)
ELEVENLABS_FAMILY_2_MALE_VOICE_ID: str = os.getenv(
    "ELEVENLABS_FAMILY_2_MALE_VOICE_ID",
    ELEVENLABS_FAMILY_VOICE_ID_2,
)
ELEVENLABS_FAMILY_2_FEMALE_VOICE_ID: str = os.getenv(
    "ELEVENLABS_FAMILY_2_FEMALE_VOICE_ID",
    ELEVENLABS_FAMILY_VOICE_ID_2,
)

OPENAI_MODEL: str = os.getenv("OPENAI_MODEL", "gpt-4o")
OPENAI_CONVERSATION_MODEL: str = os.getenv("OPENAI_CONVERSATION_MODEL", "gpt-4.1-mini")
OPENAI_TIMEOUT: int = int(os.getenv("OPENAI_TIMEOUT", "30"))

DALLE_MODEL: str = os.getenv("DALLE_MODEL", "dall-e-3")
DALLE_SIZE: str = os.getenv("DALLE_SIZE", "1792x1024")
DALLE_QUALITY: str = os.getenv("DALLE_QUALITY", "standard")
DALLE_TIMEOUT: int = int(os.getenv("DALLE_TIMEOUT", "60"))

ELEVENLABS_TTS_MODEL: str = os.getenv("ELEVENLABS_TTS_MODEL", "eleven_flash_v2_5")

GAME_TIME_LIMIT: int = int(os.getenv("GAME_TIME_LIMIT", "480"))


def _parse_thresholds(raw: str) -> list[int]:
    """Parse comma-separated idle thresholds into a list of positive ints."""
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    return [int(p) for p in parts] or [25, 20, 15]


PROACTIVE_ENABLED: bool = os.getenv("PROACTIVE_ENABLED", "true").lower() in ("1", "true", "yes", "on")
PROACTIVE_IDLE_THRESHOLDS: list[int] = _parse_thresholds(os.getenv("PROACTIVE_IDLE_THRESHOLDS", "25,20,15"))
PROACTIVE_COOLDOWN_SECONDS: int = int(os.getenv("PROACTIVE_COOLDOWN_SECONDS", "10"))
PROACTIVE_ENDGAME_GUARD_SECONDS: int = int(os.getenv("PROACTIVE_ENDGAME_GUARD_SECONDS", "30"))
RECONNECT_GRACE_SECONDS: int = int(os.getenv("RECONNECT_GRACE_SECONDS", "10"))
