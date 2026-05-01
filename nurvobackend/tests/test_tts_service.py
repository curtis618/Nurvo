"""Tests for gender-aware, per-person TTS voice selection."""

import unittest
from unittest.mock import AsyncMock, patch

from services import tts_service


class TTSVoiceSelectionTest(unittest.IsolatedAsyncioTestCase):
    async def test_patient_voice_uses_gender_specific_slot(self) -> None:
        synthesize = AsyncMock(return_value="audio")

        with (
            patch.object(tts_service, "synthesize_speech", synthesize),
            patch.object(tts_service, "ELEVENLABS_PATIENT_MALE_VOICE_ID", "patient-male", create=True),
            patch.object(tts_service, "ELEVENLABS_PATIENT_FEMALE_VOICE_ID", "patient-female", create=True),
        ):
            await tts_service.get_patient_voice("我很痛", gender="男")
            await tts_service.get_patient_voice("我很痛", gender="女性")

        self.assertEqual(
            [call.args[1] for call in synthesize.await_args_list],
            ["patient-male", "patient-female"],
        )

    async def test_same_gender_family_members_use_different_person_slots(self) -> None:
        synthesize = AsyncMock(return_value="audio")

        with (
            patch.object(tts_service, "synthesize_speech", synthesize),
            patch.object(tts_service, "ELEVENLABS_FAMILY_0_FEMALE_VOICE_ID", "family-0-female", create=True),
            patch.object(tts_service, "ELEVENLABS_FAMILY_1_FEMALE_VOICE_ID", "family-1-female", create=True),
        ):
            await tts_service.get_family_voice("她現在很不舒服嗎？", family_index=0, gender="女")
            await tts_service.get_family_voice("那接下來要怎麼辦？", family_index=1, gender="女")

        self.assertEqual(
            [call.args[1] for call in synthesize.await_args_list],
            ["family-0-female", "family-1-female"],
        )

    async def test_family_voice_falls_back_to_legacy_person_slot_for_unknown_gender(self) -> None:
        synthesize = AsyncMock(return_value="audio")

        with (
            patch.object(tts_service, "synthesize_speech", synthesize),
            patch.object(tts_service, "ELEVENLABS_FAMILY_VOICE_ID_2", "family-2-legacy"),
        ):
            await tts_service.get_family_voice("我想了解狀況。", family_index=2, gender="未提供")

        synthesize.assert_awaited_once_with("我想了解狀況。", "family-2-legacy")

    async def test_patient_voice_retries_default_voice_when_gender_voice_fails(self) -> None:
        synthesize = AsyncMock(side_effect=["", "fallback-audio"])

        with (
            patch.object(tts_service, "synthesize_speech", synthesize),
            patch.object(tts_service, "ELEVENLABS_PATIENT_FEMALE_VOICE_ID", "patient-female", create=True),
            patch.object(tts_service, "ELEVENLABS_PATIENT_VOICE_ID", "patient-default", create=True),
        ):
            audio = await tts_service.get_patient_voice("我很痛", gender="女")

        self.assertEqual(audio, "fallback-audio")
        self.assertEqual(
            [call.args[1] for call in synthesize.await_args_list],
            ["patient-female", "patient-default"],
        )

    async def test_unknown_gender_family_voice_retries_person_and_shared_legacy_fallbacks(self) -> None:
        synthesize = AsyncMock(side_effect=["", "fallback-audio"])

        with (
            patch.object(tts_service, "synthesize_speech", synthesize),
            patch.object(tts_service, "ELEVENLABS_FAMILY_VOICE_ID_1", "family-1-legacy", create=True),
            patch.object(tts_service, "ELEVENLABS_FAMILY_VOICE_ID_0", "family-0-legacy", create=True),
        ):
            audio = await tts_service.get_family_voice("我很擔心她", family_index=1, gender="未提供")

        self.assertEqual(audio, "fallback-audio")
        self.assertEqual(
            [call.args[1] for call in synthesize.await_args_list],
            ["family-1-legacy", "family-0-legacy"],
        )

    async def test_female_family_voice_does_not_fall_back_to_male_legacy_slot(self) -> None:
        synthesize = AsyncMock(side_effect=["", "fallback-audio"])

        with (
            patch.object(tts_service, "synthesize_speech", synthesize),
            patch.object(tts_service, "ELEVENLABS_FAMILY_2_FEMALE_VOICE_ID", "family-2-female", create=True),
            patch.object(tts_service, "ELEVENLABS_FAMILY_VOICE_ID_2", "family-2-legacy-male"),
            patch.object(tts_service, "ELEVENLABS_FAMILY_0_FEMALE_VOICE_ID", "family-0-female", create=True),
        ):
            audio = await tts_service.get_family_voice("我是劉小姐", family_index=2, gender="女")

        self.assertEqual(audio, "fallback-audio")
        self.assertEqual(
            [call.args[1] for call in synthesize.await_args_list],
            ["family-2-female", "family-0-female"],
        )


if __name__ == "__main__":
    unittest.main()
