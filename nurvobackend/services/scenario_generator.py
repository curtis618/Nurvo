"""Scenario generation service using OpenAI GPT-4o and DALL-E 3."""

import asyncio
import json
import logging
import uuid

from fastapi import HTTPException
from openai import AsyncOpenAI
from pydantic import ValidationError

from config import (
    DALLE_MODEL,
    DALLE_QUALITY,
    DALLE_SIZE,
    DALLE_TIMEOUT,
    OPENAI_API_KEY,
    OPENAI_MODEL,
    OPENAI_TIMEOUT,
)
from models.scenario import Scenario
from prompts.scenario_generation import TIME_LIMIT_BY_DIFFICULTY, build_scenario_generation_prompt

_MAX_SCENARIO_ATTEMPTS = 2


_client = AsyncOpenAI(api_key=OPENAI_API_KEY)
_logger = logging.getLogger(__name__)

# Tracks in-flight DALL-E tasks and their resolved URLs, keyed by session_id.
# Entries are never evicted (MVP memory is negligible: ~100 bytes per session).
_pending: set[str] = set()
_image_results: dict[str, str | None] = {}

_BACKGROUND_PROMPT = (
    "A realistic, warm hospital ward interior scene. "
    "An elderly patient is resting peacefully in a hospital bed, "
    "wearing a light hospital gown, with medical equipment visible nearby. "
    "Three family members are gathered around the bedside showing care and concern, "
    "some standing and some seated. "
    "Soft natural lighting comes through a large window, creating a calm supportive atmosphere. "
    "Pale blue walls, clean tiled floor, curtains partially drawn. "
    "Taiwanese hospital setting. Photorealistic cinematic wide-angle shot. "
    "No text, no labels, no watermarks, no on-screen captions."
)


def _norm_difficulty(difficulty: str) -> str:
    if difficulty in TIME_LIMIT_BY_DIFFICULTY:
        return difficulty
    return "medium"


async def _call_openai_for_scenario(difficulty: str) -> Scenario:
    """Issue a single GPT-4o call and parse it into a Scenario model."""
    d = _norm_difficulty(difficulty)
    response = await _client.chat.completions.create(
        model=OPENAI_MODEL,
        messages=[
            {"role": "system", "content": "You are a nursing education scenario generator. Respond only with valid JSON."},
            {"role": "user", "content": build_scenario_generation_prompt(d)},
        ],
        temperature=0.9,
        timeout=OPENAI_TIMEOUT,
    )

    content = response.choices[0].message.content
    if not content:
        raise HTTPException(status_code=502, detail="OpenAI returned empty response")

    cleaned = content.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        cleaned = cleaned.strip()

    try:
        scenario_data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse scenario JSON from OpenAI: {exc}",
        )

    scenario = Scenario(**scenario_data)
    return scenario.model_copy(
        update={"time_limit_seconds": TIME_LIMIT_BY_DIFFICULTY[d]},
    )


async def _generate_scenario_text(difficulty: str) -> Scenario:
    """Generate scenario text with one retry on Pydantic validation failure."""
    last_validation_error: ValidationError | None = None

    for attempt in range(1, _MAX_SCENARIO_ATTEMPTS + 1):
        try:
            return await _call_openai_for_scenario(difficulty)
        except ValidationError as exc:
            last_validation_error = exc
            _logger.warning(
                "Scenario validation failed on attempt %d/%d: %s",
                attempt,
                _MAX_SCENARIO_ATTEMPTS,
                exc.errors(),
            )

    raise HTTPException(
        status_code=502,
        detail=f"Scenario validation failed after retry: {last_validation_error}",
    )


async def _generate_background_image() -> str | None:
    """Call DALL-E 3 to generate a hospital ward background image.

    Returns the image URL on success, or None on failure. Never raises —
    image generation is best-effort, frontend falls back to the static
    hospital_bg.jpg when this returns None.
    """
    try:
        response = await _client.images.generate(
            model=DALLE_MODEL,
            prompt=_BACKGROUND_PROMPT,
            size=DALLE_SIZE,
            quality=DALLE_QUALITY,
            n=1,
            timeout=DALLE_TIMEOUT,
        )
        return response.data[0].url
    except Exception as exc:
        _logger.warning("DALL-E 3 image generation failed: %s", exc)
        return None


async def _store_background_image(session_id: str) -> None:
    """Background task: generate image and store result in _image_results."""
    url = await _generate_background_image()
    _image_results[session_id] = url
    _pending.discard(session_id)


def start_background_image(session_id: str) -> None:
    """Fire DALL-E generation as a non-blocking asyncio task."""
    _pending.add(session_id)
    asyncio.create_task(_store_background_image(session_id))


def get_background_image_status(session_id: str) -> tuple[bool, str | None]:
    """Return (is_pending, url). is_pending=True means DALL-E is still running."""
    if session_id in _pending:
        return True, None
    return False, _image_results.get(session_id)


async def generate_scenario(difficulty: str = "medium") -> tuple[str, Scenario]:
    """Generate scenario text via GPT-4o and kick off DALL-E in the background."""
    try:
        scenario = await _generate_scenario_text(difficulty)
        session_id = str(uuid.uuid4())
        start_background_image(session_id)
        return session_id, scenario

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI scenario generation failed: {exc}",
        )
