"""Scenario generation prompt template for GPT-4o."""

import json
from typing import Literal

# Server 以難度覆寫，此表供 router／測試對齊前端 mock
TIME_LIMIT_BY_DIFFICULTY: dict[str, int] = {
    "easy": 600,
    "medium": 480,
    "hard": 360,
}

_Difficulty = Literal["easy", "medium", "hard"]


def _json_skeleton_for_prompt() -> str:
    return json.dumps(
        {
            "patient_profile": {
                "name": "病患全名（繁體中文）",
                "age": 0,
                "gender": "男",
                "diagnosis": "主要診斷",
                "medications": ["目前用藥列表"],
                "medical_history": ["過去病史列表"],
                "allergies": ["過敏史列表"],
            },
            "pain_details": {
                "location": "疼痛位置",
                "severity": 0,
                "type": "疼痛類型（如刺痛、鈍痛、絞痛）",
                "duration": "持續時間",
                "onset": "發作情況",
                "aggravating_factors": ["加重因素"],
                "relieving_factors": ["緩解因素"],
                "associated_symptoms": ["伴隨症狀"],
            },
            "family_members": [
                {
                    "name": "王太太",
                    "gender": "女",
                    "relationship": "配偶",
                    "personality": "性格類型",
                    "emotional_state": "當前情緒狀態描述",
                    "interjection_triggers": ["會觸發插話的話題或情況"],
                },
                {
                    "name": "王先生",
                    "gender": "男",
                    "relationship": "兒子",
                    "personality": "性格類型（不同於家屬1）",
                    "emotional_state": "當前情緒狀態描述",
                    "interjection_triggers": ["會觸發插話的話題或情況"],
                },
                {
                    "name": "王小姐",
                    "gender": "女",
                    "relationship": "女兒",
                    "personality": "性格類型（不同於家屬1和2）",
                    "emotional_state": "當前情緒狀態描述",
                    "interjection_triggers": ["會觸發插話的話題或情況"],
                },
            ],
            "communication_challenges": ["這個情境中護理師可能遇到的溝通挑戰"],
            "correct_answers": {
                "expected_info_gathered": ["護理師應該收集到的資訊"],
                "ideal_empathy_phrases": ["理想的同理心回應範例"],
                "ideal_questioning_sequence": ["建議的提問順序"],
                "family_calming_strategies": ["有效的安撫家屬策略"],
            },
            "time_limit_seconds": 480,
        },
        ensure_ascii=False,
        indent=2,
    )


def build_scenario_generation_prompt(difficulty: str) -> str:
    """依難度組裝系統外送給 LLM 的 user prompt（內文含難度與 JSON 結構說明）。"""
    d: _Difficulty = difficulty if difficulty in TIME_LIMIT_BY_DIFFICULTY else "medium"
    difficulty_text = {
        "easy": (
            "【難度：簡單】疼痛嚴重度（severity）建議約 1–5/10；家屬相對願意配合、情緒較穩，"
            "敘述不全為主。communication_challenges 著重在敘述不完整、需溫和引導，避免多線家屬衝突。"
        ),
        "medium": (
            "【難度：中等】疼痛約 4–7/10，敘述偏模糊需引導；家屬易焦慮或偶爾打斷。"
            "communication_challenges 可含：敘述不完整、家屬打斷、需同理並釐清重點。"
        ),
        "hard": (
            "【難度：困難】疼痛約 6–9/10，病患敘述混亂或情緒波動；家屬高度焦慮、易頻繁打斷或質疑，"
            "需同時處理安撫、釐清與衛教，壓力明顯高於前兩者。"
        ),
    }[d]
    return f"""你是一個護理教育情境生成器。請生成一個獨特的疼痛評估護理情境。

{difficulty_text}

請以 JSON 格式回傳以下結構的情境資料（欄位名稱與層級必須一致，數值可替換為合理內容）：

{_json_skeleton_for_prompt()}

要求：
1. 每次生成的情境必須獨特，包括不同的疼痛原因、位置和程度
2. 病患的疼痛描述要模糊且不具體，需要護理師透過引導來釐清
3. 必須生成 3 位家屬，每位都必須有 gender（男或女），且姓名、與病患關係、性格類型各不相同，並會影響溝通過程
4. 病患與家屬的姓名稱謂、relationship 與 gender 必須一致：例如「王先生 + 男」、「王太太 + 女」、「林小姐 + 女」、「兒子 + 男」、「女兒 + 女」、「孫子 + 男」、「孫女 + 女」。禁止產生「王先生 + 女」、「王太太 + 男」、「兒子 + 女」、「女兒 + 男」、「孫女 + 男」、「孫子 + 女」這類不一致組合
5. 家屬的 relationship 欄位只能是家庭成員關係（配偶、父/母、子/女、兄/姊/弟/妹、祖父母、外祖父母、孫子女、外孫子女、媳婦、女婿、伯叔姑舅姨、堂/表兄弟姊妹）。禁止出現醫師、主治醫師、護理師、住院醫師、藥師、社工、看護、照護員、朋友、同事、鄰居、同學、老闆、老師、學生等任何非家屬角色
6. 家屬的姓氏規則：三位家屬的姓氏原則上與 patient_profile.name 的姓氏相同。僅當該家屬是配偶、媳婦或女婿時，可以使用不同姓氏；至少要有一位家屬與病患同姓
7. 三位家屬必須是真實同家族的合理組合，例如「配偶＋子女」「子女＋父母」「子女＋手足」「配偶＋子女＋父母」，不要隨機湊三個不相關的人
8. 所有文字使用繁體中文
9. 情境要符合真實臨床場景
10. 依難度調整家屬與溝通挑戰的強度
11. time_limit_seconds 可填列示值；伺服器端可能依難度再校正
12. 只回傳 JSON，不要有其他文字"""
