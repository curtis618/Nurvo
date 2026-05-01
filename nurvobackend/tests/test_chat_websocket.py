"""Smoke tests for the backend WebSocket path used by digiRunner."""

import asyncio
import json
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient

from main import app
from models.chat import GameSession
from session_store import create_session, delete_session


class ChatWebSocketGatewayContractTest(unittest.TestCase):
    def test_digirunner_websocket_path_requires_session_join_first(self) -> None:
        client = TestClient(app)

        with client.websocket_connect("/api/chat/ws") as ws:
            ws.send_text(json.dumps({"type": "nurse_message", "content": "您好"}, ensure_ascii=False))
            data = ws.receive_json()

        self.assertEqual(data["type"], "error")
        self.assertEqual(data["message"], "First message must be session_join")

    def test_digirunner_websocket_path_reports_missing_session_after_join(self) -> None:
        client = TestClient(app)

        with client.websocket_connect("/api/chat/ws") as ws:
            ws.send_text(json.dumps({"type": "session_join", "session_id": "missing"}, ensure_ascii=False))
            data = ws.receive_json()

        self.assertEqual(data["type"], "error")
        self.assertEqual(data["message"], "Session not found")

    def test_npc_text_is_sent_before_async_tts_audio(self) -> None:
        client = TestClient(app)
        session_id = "session-async-audio"
        create_session(
            GameSession(
                session_id=session_id,
                scenario_data={"patient_profile": {"gender": "女"}, "family_members": []},
                start_time=datetime.now(timezone.utc),
                patient_system_prompt="patient prompt",
                family_system_prompts=[],
            ),
        )

        async def slow_audio(*_args: object) -> str:
            await asyncio.sleep(0.01)
            return "audio"

        try:
            with (
                patch("routers.chat.get_npc_response", AsyncMock(return_value=("我這裡很痛", "patient"))),
                patch("routers.chat.get_npc_audio", AsyncMock(side_effect=slow_audio), create=True),
                patch("routers.chat.maybe_family_interjection", AsyncMock(return_value=("", False, -1))),
            ):
                with client.websocket_connect(f"/api/chat/{session_id}") as ws:
                    self.assertEqual(ws.receive_json()["type"], "timer_update")

                    ws.send_text(json.dumps({"type": "nurse_message", "content": "哪裡痛？"}, ensure_ascii=False))

                    self.assertEqual(ws.receive_json(), {"type": "typing", "sender": "patient"})
                    message = ws.receive_json()
                    self.assertEqual(message["type"], "npc_message")
                    self.assertEqual(message["sender"], "patient")
                    self.assertEqual(message["content"], "我這裡很痛")
                    self.assertNotIn("audio_base64", message)

                    audio = ws.receive_json()
                    self.assertEqual(audio["type"], "npc_audio")
                    self.assertEqual(audio["message_id"], message["message_id"])
                    self.assertEqual(audio["audio_base64"], "audio")
        finally:
            delete_session(session_id)


if __name__ == "__main__":
    unittest.main()
