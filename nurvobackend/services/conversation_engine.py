"""Conversation engine service for patient and family NPC responses."""

import json
import logging
import re
from datetime import datetime, timezone

from fastapi import HTTPException
from openai import AsyncOpenAI

from config import (
    GAME_TIME_LIMIT,
    OPENAI_API_KEY,
    OPENAI_CONVERSATION_MODEL,
    OPENAI_TIMEOUT,
    PROACTIVE_COOLDOWN_SECONDS,
    PROACTIVE_ENDGAME_GUARD_SECONDS,
)
from models.chat import GameSession
from prompts.proactive_speech import build_proactive_decision_prompt
from services.tts_service import get_family_voice, get_patient_voice

logger = logging.getLogger(__name__)

# Regex to strip leading speaker labels like [病患], [家屬], [家屬1] from GPT output
_LABEL_RE = re.compile(r"^\[(?:病患|家屬\d*)\]\s*")


_client = AsyncOpenAI(api_key=OPENAI_API_KEY)

# Minimum nurse-to-patient messages between family interjections
_MIN_INTERJECTION_GAP = 2
# Max recent messages to include in interjection decision context
_MAX_DECISION_HISTORY = 10


def _count_messages_since_last_interjection(session: GameSession) -> int:
    """Count nurse messages to patient since the last family interjection."""
    count = 0
    for msg in reversed(session.conversation_history):
        if msg.is_interjection:
            break
        if msg.sender == "nurse":
            count += 1
    return count


def _family_label(sender: str) -> str:
    """Return a display label for a family sender like 'family_0' -> '[家屬1]'."""
    if sender.startswith("family_"):
        idx = int(sender.split("_")[1])
        return f"[家屬{idx + 1}]"
    return "[家屬]"


def _build_history(messages: list) -> list[dict[str, str]]:
    """Convert ChatMessage list to OpenAI message format with speaker labels."""
    history: list[dict[str, str]] = []
    for msg in messages:
        if msg.sender == "nurse":
            history.append({"role": "user", "content": msg.content})
        else:
            label = "[病患]" if msg.sender == "patient" else _family_label(msg.sender)
            history.append({"role": "assistant", "content": f"{label} {msg.content}"})
    return history


def _build_openai_messages(
    system_prompt: str,
    conversation_history: list[dict[str, str]],
    nurse_message: str,
) -> list[dict[str, str]]:
    """Build the OpenAI messages list from system prompt, history, and new nurse message."""
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt}]
    messages.extend(conversation_history)
    messages.append({"role": "user", "content": nurse_message})
    return messages


def _patient_gender(session: GameSession) -> str:
    patient = session.scenario_data.get("patient_profile", {})
    if isinstance(patient, dict):
        return str(patient.get("gender", ""))
    return ""


def _family_gender(session: GameSession, family_index: int) -> str:
    family_members = session.scenario_data.get("family_members", [])
    if not isinstance(family_members, list):
        return ""
    if family_index < 0 or family_index >= len(family_members):
        return ""
    member = family_members[family_index]
    if isinstance(member, dict):
        return str(member.get("gender", ""))
    return ""


async def get_npc_response(
    session: GameSession,
    nurse_message: str,
    target: str,
) -> tuple[str, str]:
    """Get an NPC response for the nurse's message.

    Returns (npc_response_text, sender) where sender is 'patient' or
    'family_0'/'family_1'/'family_2'. TTS is generated separately so text can
    be delivered without waiting for audio synthesis.
    """
    if target == "patient":
        system_prompt = session.patient_system_prompt
        sender = "patient"
    elif target.startswith("family_") and target in ("family_0", "family_1", "family_2"):
        family_index = int(target.split("_")[1])
        system_prompt = session.family_system_prompts[family_index]
        sender = target
    else:
        raise HTTPException(status_code=400, detail=f"Invalid target: {target}")

    history = _build_history(session.conversation_history)
    messages = _build_openai_messages(system_prompt, history, nurse_message)

    try:
        response = await _client.chat.completions.create(
            model=OPENAI_CONVERSATION_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=300,
            timeout=OPENAI_TIMEOUT,
        )

        content = response.choices[0].message.content
        if not content:
            raise HTTPException(status_code=502, detail="OpenAI returned empty NPC response")

        npc_text = _LABEL_RE.sub("", content.strip())
        return npc_text, sender

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"NPC response generation failed: {exc}",
        )


async def get_npc_audio(session: GameSession, npc_text: str, sender: str) -> str:
    """Generate TTS audio for an already-created NPC response."""
    if sender == "patient":
        return await get_patient_voice(npc_text, _patient_gender(session))
    if sender.startswith("family_") and sender in ("family_0", "family_1", "family_2"):
        family_index = int(sender.split("_")[1])
        return await get_family_voice(
            npc_text,
            family_index,
            _family_gender(session, family_index),
        )
    raise HTTPException(status_code=400, detail=f"Invalid sender for TTS: {sender}")


async def maybe_family_interjection(session: GameSession) -> tuple[str, bool, int]:
    """Use LLM to decide whether a family member should interject based on conversation content.

    Uses round-robin to pick one candidate family member per check to avoid
    tripling LLM costs.

    Returns (interjection_text, did_interject, family_index).
    family_index is -1 when no interjection occurred.
    """
    # Enforce minimum gap between interjections
    messages_since = _count_messages_since_last_interjection(session)
    if messages_since < _MIN_INTERJECTION_GAP:
        return "", False, -1

    if not session.family_system_prompts:
        return "", False, -1

    # Round-robin: pick the next candidate family member
    candidate_index = (session.last_interjecting_family_index + 1) % len(session.family_system_prompts)
    # Always advance the index so all family members get a turn
    session.last_interjecting_family_index = candidate_index

    # Build recent history only (last N messages for performance)
    recent_messages = session.conversation_history[-_MAX_DECISION_HISTORY:]
    history = _build_history(recent_messages)

    decision_prompt = (
        "根據目前的對話，判斷你（作為家屬）是否需要在此刻插話。\n"
        "只在以下情況插話：\n"
        "- 護理師提到讓你擔心的內容（疼痛加劇、需要手術、藥物副作用等）\n"
        "- 你覺得護理師忽略了重要資訊\n"
        "- 你等太久想催促\n"
        "- 對話觸發了你的情緒（根據你的性格）\n\n"
        "回覆格式嚴格如下：\n"
        "第一行只寫 YES 或 NO\n"
        "如果 YES，第二行寫你要說的話（一到兩句，簡短自然）"
    )

    messages: list[dict[str, str]] = [
        {"role": "system", "content": session.family_system_prompts[candidate_index]},
    ]
    messages.extend(history)
    messages.append({"role": "user", "content": decision_prompt})

    try:
        response = await _client.chat.completions.create(
            model=OPENAI_CONVERSATION_MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=100,
            timeout=OPENAI_TIMEOUT,
        )

        content = response.choices[0].message.content
        if not content:
            return "", False, -1

        lines = content.strip().split("\n", 1)
        if lines[0].strip().upper() == "YES" and len(lines) > 1:
            interjection_text = _LABEL_RE.sub("", lines[1].strip())
            if not interjection_text:
                return "", False, -1
            return interjection_text, True, candidate_index

        return "", False, -1

    except Exception:
        # Don't fail the main flow for an interjection error
        return "", False, -1


_VALID_SPEAKERS = {"patient", "family_0", "family_1", "family_2"}


async def maybe_proactive_speak(session: GameSession) -> tuple[str, str, bool]:
    """Decide whether any NPC should speak proactively after nurse idleness.

    Returns (content, sender, did_speak). Audio is generated separately by the
    WebSocket router so proactive messages follow the same text-first contract
    as normal NPC replies.
    """
    now = datetime.now(timezone.utc)

    if session.last_proactive_at is not None:
        since_last = (now - session.last_proactive_at).total_seconds()
        if since_last < PROACTIVE_COOLDOWN_SECONDS:
            return "", "", False

    if session.start_time is not None:
        elapsed = (now - session.start_time).total_seconds()
        remaining = GAME_TIME_LIMIT - elapsed
        if remaining < PROACTIVE_ENDGAME_GUARD_SECONDS:
            return "", "", False

    if not any(message.sender == "nurse" for message in session.conversation_history):
        return "", "", False

    system_prompt = build_proactive_decision_prompt(session, session.proactive_streak)

    try:
        response = await _client.chat.completions.create(
            model=OPENAI_CONVERSATION_MODEL,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "請依規則輸出嚴格 JSON。"},
            ],
            temperature=0.8,
            max_tokens=150,
            timeout=OPENAI_TIMEOUT,
            response_format={"type": "json_object"},
        )

        content = response.choices[0].message.content
        if not content:
            return "", "", False

        data = json.loads(content)
    except Exception as exc:
        logger.warning("proactive_speech decision failed: %s", exc)
        return "", "", False

    if not isinstance(data, dict) or not data.get("speak"):
        return "", "", False

    speaker = data.get("speaker")
    text = data.get("content")
    if speaker not in _VALID_SPEAKERS or not isinstance(text, str):
        return "", "", False

    if speaker.startswith("family_"):
        family_index = int(speaker.split("_")[1])
        if family_index >= len(session.family_system_prompts):
            return "", "", False

    clean_text = _LABEL_RE.sub("", text.strip())
    if not clean_text:
        return "", "", False

    session.proactive_streak += 1
    session.last_proactive_at = now
    return clean_text, speaker, True
