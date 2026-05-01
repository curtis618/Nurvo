"""Tests that conversation responses pass scenario gender to TTS."""

from datetime import datetime, timezone
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, patch

from config import OPENAI_TIMEOUT
from models.chat import GameSession
from services import conversation_engine


class _FakeCompletions:
    def __init__(self, content: str) -> None:
        self._content = content
        self.calls: list[dict[str, object]] = []

    async def create(self, **kwargs: object) -> object:
        self.calls.append(kwargs)
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=self._content),
                ),
            ],
        )


class ConversationVoiceGenderTest(unittest.IsolatedAsyncioTestCase):
    def _session(self) -> GameSession:
        return GameSession(
            session_id="session-1",
            scenario_data={
                "patient_profile": {"name": "林女士", "gender": "女"},
                "family_members": [
                    {"name": "林先生", "gender": "男"},
                    {"name": "林小姐", "gender": "女"},
                    {"name": "陳小姐", "gender": "女"},
                ],
            },
            start_time=datetime.now(timezone.utc),
            patient_system_prompt="patient prompt",
            family_system_prompts=["family 0", "family 1", "family 2"],
        )

    async def test_patient_audio_passes_patient_gender_to_tts(self) -> None:
        get_patient_voice = AsyncMock(return_value="audio")

        with patch.object(conversation_engine, "get_patient_voice", get_patient_voice):
            audio = await conversation_engine.get_npc_audio(self._session(), "我這裡很痛", "patient")

        self.assertEqual(audio, "audio")
        get_patient_voice.assert_awaited_once_with("我這裡很痛", "女")

    async def test_family_audio_passes_matching_family_gender_to_tts(self) -> None:
        get_family_voice = AsyncMock(return_value="audio")

        with patch.object(conversation_engine, "get_family_voice", get_family_voice):
            audio = await conversation_engine.get_npc_audio(self._session(), "我很擔心她", "family_1")

        self.assertEqual(audio, "audio")
        get_family_voice.assert_awaited_once_with("我很擔心她", 1, "女")

    async def test_npc_response_uses_conversation_model_without_waiting_for_tts(self) -> None:
        completions = _FakeCompletions("[病患] 我了解")
        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))
        get_patient_voice = AsyncMock(return_value="audio")

        with (
            patch.object(conversation_engine, "_client", fake_client),
            patch.object(conversation_engine, "get_patient_voice", get_patient_voice),
        ):
            text, sender = await conversation_engine.get_npc_response(self._session(), "您好", "patient")

        self.assertEqual((text, sender), ("我了解", "patient"))
        self.assertEqual(completions.calls[0]["model"], conversation_engine.OPENAI_CONVERSATION_MODEL)
        get_patient_voice.assert_not_awaited()

    async def test_npc_response_uses_configured_openai_timeout(self) -> None:
        completions = _FakeCompletions("我了解")
        fake_client = SimpleNamespace(chat=SimpleNamespace(completions=completions))

        with patch.object(conversation_engine, "_client", fake_client):
            await conversation_engine.get_npc_response(self._session(), "您好", "patient")

        self.assertEqual(completions.calls[0]["timeout"], OPENAI_TIMEOUT)


if __name__ == "__main__":
    unittest.main()
