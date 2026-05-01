"""Tests for scenario gender fields used by TTS selection."""

import unittest

from pydantic import ValidationError

from models.scenario import FamilyMember, PatientProfile
from prompts.scenario_generation import build_scenario_generation_prompt


class ScenarioGenderTest(unittest.TestCase):
    def test_family_member_requires_gender(self) -> None:
        with self.assertRaises(ValidationError):
            FamilyMember(
                name="王太太",
                relationship="配偶",
                personality="焦慮",
                emotional_state="擔心",
                interjection_triggers=["疼痛"],
            )

    def test_generation_prompt_requests_family_gender(self) -> None:
        prompt = build_scenario_generation_prompt("medium")

        self.assertIn('"gender": "女"', prompt)
        self.assertIn("必須生成 3 位家屬", prompt)

    def test_generation_prompt_requires_name_relationship_gender_consistency(self) -> None:
        prompt = build_scenario_generation_prompt("medium")

        self.assertIn("姓名稱謂", prompt)
        self.assertIn("gender 必須一致", prompt)
        self.assertIn("王先生 + 男", prompt)
        self.assertIn("王太太 + 女", prompt)
        self.assertIn("孫女 + 女", prompt)
        self.assertIn("孫子 + 男", prompt)

    def test_patient_rejects_obvious_name_gender_mismatch(self) -> None:
        with self.assertRaises(ValidationError):
            PatientProfile(
                name="王先生",
                age=72,
                gender="女",
                diagnosis="術後疼痛",
                medications=[],
                medical_history=[],
                allergies=[],
            )

    def test_family_member_rejects_obvious_name_or_relationship_gender_mismatch(self) -> None:
        with self.assertRaises(ValidationError):
            FamilyMember(
                name="王先生",
                gender="女",
                relationship="女兒",
                personality="焦慮",
                emotional_state="擔心",
                interjection_triggers=["疼痛"],
            )

        with self.assertRaises(ValidationError):
            FamilyMember(
                name="林小姐",
                gender="男",
                relationship="兒子",
                personality="急切",
                emotional_state="緊張",
                interjection_triggers=["等待過久"],
            )

        with self.assertRaises(ValidationError):
            FamilyMember(
                name="王小華",
                gender="男",
                relationship="孫女",
                personality="緊張",
                emotional_state="擔心",
                interjection_triggers=["病況變化"],
            )


if __name__ == "__main__":
    unittest.main()
