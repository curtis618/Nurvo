"""Proactive speech decision prompt template for GPT-4o.

Used when the nurse has been idle for longer than the configured threshold.
The model decides whether any NPC (patient or a family member) should speak
unprompted, and if so, who and what they say.

Expected response format (strict JSON):
    {"speak": true,  "speaker": "patient",  "content": "好痛…護理師…"}
    {"speak": true,  "speaker": "family_1", "content": "到底要等多久！"}
    {"speak": false, "speaker": null,       "content": null}

Example decisions by streak:
    streak=0  -> mild call-out ("護理師？" or "嗯…")
    streak=1  -> moderate anxiety ("她真的很痛欸，你們怎麼辦？")
    streak=2  -> strongest tone ("到底還要等多久！")
"""

from models.chat import GameSession

_MAX_HISTORY_TURNS = 10


def _recent_history_text(session: GameSession) -> str:
    """Render the last N turns as plain labelled dialog for prompt context."""
    turns = session.conversation_history[-_MAX_HISTORY_TURNS:]
    lines: list[str] = []
    for msg in turns:
        if msg.sender == "nurse":
            label = "[護理師]"
        elif msg.sender == "patient":
            label = "[病患]"
        elif msg.sender.startswith("family_"):
            idx = int(msg.sender.split("_")[1])
            label = f"[家屬{idx + 1}]"
        else:
            label = f"[{msg.sender}]"
        lines.append(f"{label} {msg.content}")
    return "\n".join(lines) if lines else "（尚未有對話）"


def _role_summaries(session: GameSession) -> str:
    """Compose a short role digest for each candidate speaker."""
    parts: list[str] = []
    if session.patient_system_prompt:
        parts.append(f"## 病患 (speaker=\"patient\")\n{session.patient_system_prompt}")
    for idx, prompt in enumerate(session.family_system_prompts):
        parts.append(f"## 家屬{idx + 1} (speaker=\"family_{idx}\")\n{prompt}")
    return "\n\n".join(parts) if parts else "（尚未有角色設定）"


def build_proactive_decision_prompt(session: GameSession, streak: int) -> str:
    """Build the system prompt for the proactive-speech decision call.

    Args:
        session: Current game session, used to pull role prompts and history.
        streak: Current proactive_streak value (0 = first cycle, 2 = third).

    Returns:
        A string system prompt for the OpenAI chat completion call.
    """
    streak_index = max(0, min(streak, 2))
    intensity_label = ["輕度（剛開始的沉默）", "中度（等太久開始不耐）", "強烈（忍不住爆發）"][streak_index]

    return f"""你是一個多角色模擬器，負責判斷在護理師沉默時，是否有任何一位角色會主動開口。

## 背景
以下是本次對話中每一位角色的完整設定，以及最近的對話歷史。護理師（使用者）已經一段時間沒有回應。
你的任務是扮演其中一位角色（病患或某位家屬）主動開口，或是決定此刻沒有人應該開口。

## 所有可選角色
{_role_summaries(session)}

## 最近對話歷史（由舊到新）
{_recent_history_text(session)}

## 當前主動發話次數
這是連續第 {streak + 1} 次主動發話（streak={streak}）。情緒強度：**{intensity_label}**。

## 可選語氣光譜
- **病患 (patient)**：
  - 低能量呼喚（「嗯…護理師…」）
  - 再次訴苦（「好痛…真的很痛…」）
  - 透露新細節（「剛剛動了一下，更痛了」）
- **家屬 (family_N)**：
  - 輕度催促（「護理師？」「有聽到嗎？」）
  - 中度焦慮（「她真的很痛欸，你們怎麼辦？」）
  - 質疑／情緒（「到底還要等多久！」）

強度應該與 streak 遞進對齊：streak=0 偏輕度、streak=1 偏中度、streak=2 偏強烈。
同一角色的性格設定（personality / emotional_state）仍是最終決定語氣的依據。

## 典型情境提示
- 閒置時，最後一則通常就是某位 NPC 的回覆（護理師沒接話），這正是主動發話的時機
- 若對話還沒開始（使用者從未開口），則不要發話
- 避免重複最近已經說過的話（語氣可以類似，但內容要推進）

## 回覆格式（嚴格 JSON，只能是其中一種）
{{"speak": true, "speaker": "patient", "content": "短句，一到兩句"}}
{{"speak": true, "speaker": "family_0", "content": "短句，一到兩句"}}
{{"speak": false, "speaker": null, "content": null}}

## 規則
1. 只能選一位角色開口，或不開口
2. speaker 必須是以下其中之一：patient、family_0、family_1、family_2、null
3. content 使用口語化繁體中文，一到兩句就好，不要長篇大論
4. 不要在 content 中加上 [病患]/[家屬] 這類標籤
5. 如果選擇不開口，speaker 與 content 都必須是 null
"""
