"""Text-to-Speech service using Eleven Labs API."""

import base64
import logging

import httpx

from config import (
    ELEVENLABS_API_KEY,
    ELEVENLABS_FAMILY_0_FEMALE_VOICE_ID,
    ELEVENLABS_FAMILY_0_MALE_VOICE_ID,
    ELEVENLABS_FAMILY_1_FEMALE_VOICE_ID,
    ELEVENLABS_FAMILY_1_MALE_VOICE_ID,
    ELEVENLABS_FAMILY_2_FEMALE_VOICE_ID,
    ELEVENLABS_FAMILY_2_MALE_VOICE_ID,
    ELEVENLABS_FAMILY_VOICE_ID_0,
    ELEVENLABS_FAMILY_VOICE_ID_1,
    ELEVENLABS_FAMILY_VOICE_ID_2,
    ELEVENLABS_PATIENT_FEMALE_VOICE_ID,
    ELEVENLABS_PATIENT_MALE_VOICE_ID,
    ELEVENLABS_PATIENT_VOICE_ID,
    ELEVENLABS_TTS_MODEL,
)

logger = logging.getLogger(__name__)

_TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
_TIMEOUT = 15.0


def _normalize_gender(gender: str | None) -> str | None:
    if not gender:
        return None

    normalized = gender.strip().lower()
    if normalized in {"男", "男性", "male", "m"}:
        return "male"
    if normalized in {"女", "女性", "female", "f"}:
        return "female"
    return None


def _unique_voice_ids(*voice_ids: str) -> list[str]:
    unique: list[str] = []
    for voice_id in voice_ids:
        if voice_id and voice_id not in unique:
            unique.append(voice_id)
    return unique


def _patient_voice_ids(gender: str | None) -> list[str]:
    normalized = _normalize_gender(gender)
    if normalized == "male":
        return _unique_voice_ids(ELEVENLABS_PATIENT_MALE_VOICE_ID, ELEVENLABS_PATIENT_VOICE_ID)
    if normalized == "female":
        return _unique_voice_ids(ELEVENLABS_PATIENT_FEMALE_VOICE_ID, ELEVENLABS_PATIENT_VOICE_ID)
    return _unique_voice_ids(ELEVENLABS_PATIENT_VOICE_ID)


def _family_voice_ids(family_index: int, gender: str | None) -> list[str]:
    legacy_voices = [
        ELEVENLABS_FAMILY_VOICE_ID_0,
        ELEVENLABS_FAMILY_VOICE_ID_1,
        ELEVENLABS_FAMILY_VOICE_ID_2,
    ]
    gendered_voices = [
        {
            "male": ELEVENLABS_FAMILY_0_MALE_VOICE_ID,
            "female": ELEVENLABS_FAMILY_0_FEMALE_VOICE_ID,
        },
        {
            "male": ELEVENLABS_FAMILY_1_MALE_VOICE_ID,
            "female": ELEVENLABS_FAMILY_1_FEMALE_VOICE_ID,
        },
        {
            "male": ELEVENLABS_FAMILY_2_MALE_VOICE_ID,
            "female": ELEVENLABS_FAMILY_2_FEMALE_VOICE_ID,
        },
    ]

    index = family_index if 0 <= family_index < len(legacy_voices) else 0
    normalized = _normalize_gender(gender)
    candidates: list[str] = []

    if normalized == "female":
        candidates.append(gendered_voices[index]["female"])
        candidates.extend(voice["female"] for voice in gendered_voices)
        candidates.append(ELEVENLABS_PATIENT_FEMALE_VOICE_ID)
        return _unique_voice_ids(*candidates)

    if normalized == "male":
        candidates.append(gendered_voices[index]["male"])
        candidates.extend(voice["male"] for voice in gendered_voices)
        candidates.extend([ELEVENLABS_PATIENT_MALE_VOICE_ID, ELEVENLABS_PATIENT_VOICE_ID])
        return _unique_voice_ids(*candidates)

    candidates.extend([legacy_voices[index], legacy_voices[0], ELEVENLABS_PATIENT_VOICE_ID])
    return _unique_voice_ids(*candidates)


async def _synthesize_with_fallbacks(text: str, voice_ids: list[str]) -> str:
    for voice_id in voice_ids:
        audio = await synthesize_speech(text, voice_id)
        if audio:
            return audio
        logger.warning("TTS returned no audio for voice_id=%s; trying fallback", voice_id)
    return ""


async def synthesize_speech(text: str, voice_id: str) -> str:
    """Synthesize speech from text using Eleven Labs TTS API.

    Returns base64-encoded audio on success, empty string on failure.
    """
    if not ELEVENLABS_API_KEY or not voice_id:
        logger.warning("TTS skipped: ELEVENLABS_API_KEY or voice_id is empty")
        return ""

    url = _TTS_URL.format(voice_id=voice_id)
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json",
    }
    body = {
        "text": text,
        "model_id": ELEVENLABS_TTS_MODEL,
    }

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(url, headers=headers, json=body)
            response.raise_for_status()
            audio_bytes = response.content
            return base64.b64encode(audio_bytes).decode("utf-8")
    except httpx.HTTPStatusError as exc:
        logger.error("TTS API error %s: %s", exc.response.status_code, exc.response.text[:200])
        return ""
    except Exception as exc:
        logger.error("TTS failed: %s", exc)
        return ""


async def get_patient_voice(text: str, gender: str | None = None) -> str:
    """Get TTS audio for patient voice."""
    return await _synthesize_with_fallbacks(text, _patient_voice_ids(gender))


async def get_family_voice(text: str, family_index: int = 0, gender: str | None = None) -> str:
    """Get TTS audio for family member voice."""
    return await _synthesize_with_fallbacks(text, _family_voice_ids(family_index, gender))
