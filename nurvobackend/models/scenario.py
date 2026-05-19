"""Scenario-related Pydantic models."""

from typing import Optional

from pydantic import BaseModel, field_validator, model_validator


_MALE_MARKERS = (
    "先生",
    "男性",
    "爸爸",
    "父親",
    "丈夫",
    "兒子",
    "哥哥",
    "弟弟",
    "爺爺",
    "祖父",
    "外公",
    "公公",
    "女婿",
    "孫子",
)
_FEMALE_MARKERS = (
    "女士",
    "小姐",
    "太太",
    "女性",
    "媽媽",
    "母親",
    "妻子",
    "女兒",
    "姐姐",
    "姊姊",
    "妹妹",
    "奶奶",
    "祖母",
    "外婆",
    "婆婆",
    "媳婦",
    "孫女",
)

_FORBIDDEN_RELATIONSHIP_KEYWORDS: tuple[str, ...] = (
    "主治醫師",
    "醫師",
    "醫生",
    "護理",
    "護士",
    "藥師",
    "社工",
    "看護",
    "照護員",
    "照服員",
    "朋友",
    "同事",
    "鄰居",
    "老闆",
    "老師",
    "同學",
    "學生",
)


def _normalize_gender(gender: str) -> str | None:
    normalized = gender.strip().lower()
    if normalized in {"男", "男性", "male", "m"}:
        return "male"
    if normalized in {"女", "女性", "female", "f"}:
        return "female"
    return None


def _has_marker(text: str, markers: tuple[str, ...]) -> bool:
    return any(marker in text for marker in markers)


def _validate_name_gender_consistency(name: str, gender: str, relationship: str = "") -> None:
    normalized = _normalize_gender(gender)
    combined = f"{name} {relationship}"
    if normalized == "male" and _has_marker(combined, _FEMALE_MARKERS):
        raise ValueError("姓名稱謂/關係與 gender 不一致：男性角色不可使用女性稱謂或關係")
    if normalized == "female" and _has_marker(combined, _MALE_MARKERS):
        raise ValueError("姓名稱謂/關係與 gender 不一致：女性角色不可使用男性稱謂或關係")


class PatientProfile(BaseModel):
    name: str
    age: int
    gender: str
    diagnosis: str
    medications: list[str]
    medical_history: list[str]
    allergies: list[str]

    @model_validator(mode="after")
    def name_matches_gender(self) -> "PatientProfile":
        _validate_name_gender_consistency(self.name, self.gender)
        return self


class PainDetails(BaseModel):
    location: str
    severity: int
    type: str
    duration: str
    onset: str
    aggravating_factors: list[str]
    relieving_factors: list[str]
    associated_symptoms: list[str]


class FamilyMember(BaseModel):
    name: str
    gender: str
    relationship: str
    personality: str
    emotional_state: str
    interjection_triggers: list[str]

    @field_validator("relationship")
    @classmethod
    def relationship_must_be_family_role(cls, v: str) -> str:
        for keyword in _FORBIDDEN_RELATIONSHIP_KEYWORDS:
            if keyword in v:
                raise ValueError(
                    f"家屬 relationship 不可包含非家庭角色關鍵字「{keyword}」，實際值為「{v}」"
                )
        return v

    @model_validator(mode="after")
    def name_and_relationship_match_gender(self) -> "FamilyMember":
        _validate_name_gender_consistency(self.name, self.gender, self.relationship)
        return self


class CorrectAnswers(BaseModel):
    expected_info_gathered: list[str]
    ideal_empathy_phrases: list[str]
    ideal_questioning_sequence: list[str]
    family_calming_strategies: list[str]


class Scenario(BaseModel):
    patient_profile: PatientProfile
    pain_details: PainDetails
    family_members: list[FamilyMember]
    communication_challenges: list[str]
    correct_answers: CorrectAnswers
    time_limit_seconds: int = 480
    background_image_url: Optional[str] = None

    @field_validator("family_members")
    @classmethod
    def exactly_three_family_members(cls, v: list[FamilyMember]) -> list[FamilyMember]:
        if len(v) != 3:
            raise ValueError(f"必須恰好有 3 位家屬，目前有 {len(v)} 位")
        return v

    @model_validator(mode="after")
    def at_least_one_family_shares_patient_surname(self) -> "Scenario":
        patient_name = self.patient_profile.name.strip()
        if not patient_name:
            raise ValueError("病患姓名不可為空")

        patient_surname = patient_name[0]
        family_surnames = [fm.name.strip()[0] for fm in self.family_members if fm.name.strip()]

        if not any(surname == patient_surname for surname in family_surnames):
            raise ValueError(
                f"三位家屬姓氏皆與病患「{patient_surname}」不同（家屬姓氏：{family_surnames}）"
            )
        return self
