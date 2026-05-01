"""Scenario generation router."""

from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from models.chat import GameSession, SessionStatus
from models.scenario import Scenario
from prompts.patient_conversation import build_patient_prompt
from prompts.family_conversation import build_family_prompt
from services.scenario_generator import generate_scenario, get_background_image_status
from session_store import create_session

router = APIRouter(prefix="/scenario", tags=["scenario"])


class GenerateScenarioRequest(BaseModel):
    difficulty: Literal["easy", "medium", "hard"] = "medium"


@router.get("/{session_id}/background")
async def get_scenario_background(session_id: str) -> dict:
    """Poll for the DALL-E background image. Returns status=pending until ready."""
    is_pending, url = get_background_image_status(session_id)
    if is_pending:
        return {"status": "pending", "url": None}
    return {"status": "ready", "url": url}


class _ScenarioResponse(Scenario):
    """Scenario response that excludes correct_answers from serialization."""

    class Config:
        # We override serialization at the endpoint level instead
        pass


@router.post("/generate")
async def generate_scenario_endpoint(body: GenerateScenarioRequest) -> dict:
    """Generate a new scenario and create a game session."""
    session_id, scenario = await generate_scenario(body.difficulty)

    # Build system prompts for patient and family NPCs
    patient = scenario.patient_profile
    pain = scenario.pain_details

    patient_system_prompt = build_patient_prompt(
        name=patient.name,
        age=patient.age,
        gender=patient.gender,
        diagnosis=patient.diagnosis,
        pain_location=pain.location,
        pain_severity=pain.severity,
        pain_type=pain.type,
        pain_duration=pain.duration,
        onset=pain.onset,
        aggravating_factors=pain.aggravating_factors,
        relieving_factors=pain.relieving_factors,
        associated_symptoms=pain.associated_symptoms,
    )

    family_system_prompts = [
        build_family_prompt(
            family_name=fm.name,
            gender=fm.gender,
            relationship=fm.relationship,
            personality=fm.personality,
            emotional_state=fm.emotional_state,
            patient_name=patient.name,
            interjection_triggers=fm.interjection_triggers,
        )
        for fm in scenario.family_members
    ]

    # Create and store game session
    game_session = GameSession(
        session_id=session_id,
        scenario_data=scenario.model_dump(),
        status=SessionStatus.BRIEFING,
        patient_system_prompt=patient_system_prompt,
        family_system_prompts=family_system_prompts,
    )
    create_session(game_session)

    # Return scenario without correct_answers
    scenario_dict = scenario.model_dump()
    scenario_dict.pop("correct_answers", None)

    return {
        "session_id": session_id,
        "scenario": scenario_dict,
    }
