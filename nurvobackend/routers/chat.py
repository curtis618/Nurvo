"""WebSocket chat router for real-time nurse-NPC conversation."""

import asyncio
import json
import logging
import uuid
from collections.abc import Callable
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from config import (
    GAME_TIME_LIMIT,
    PROACTIVE_ENABLED,
    PROACTIVE_IDLE_THRESHOLDS,
    RECONNECT_GRACE_SECONDS,
)
from models.chat import ChatMessage, GameSession, SessionStatus
from services.conversation_engine import (
    get_npc_audio,
    get_npc_response,
    maybe_family_interjection,
    maybe_proactive_speak,
)
from session_store import get_session, update_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

_session_locks: dict[str, asyncio.Lock] = {}
_VALID_ACTIVITY_KINDS = {"typing_start", "typing_end", "audio_start", "audio_end", "connection_resumed"}


def _get_session_lock(session_id: str) -> asyncio.Lock:
    """Get or create the asyncio lock for a given session."""
    lock = _session_locks.get(session_id)
    if lock is None:
        lock = asyncio.Lock()
        _session_locks[session_id] = lock
    return lock


def _elapsed_seconds(start_time: datetime) -> float:
    """Calculate elapsed seconds from session start to now."""
    now = datetime.now(timezone.utc)
    return round((now - start_time).total_seconds(), 1)


async def _send_json(ws: WebSocket, data: dict) -> None:
    """Send a JSON message over the WebSocket."""
    await ws.send_text(json.dumps(data, ensure_ascii=False))


async def _send_audio_when_ready(
    ws: WebSocket,
    session: GameSession,
    message_id: str,
    sender: str,
    content: str,
) -> None:
    """Generate TTS in the background and attach it to an existing message."""
    try:
        audio_base64 = await get_npc_audio(session, content, sender)
        if audio_base64:
            await _send_json(ws, {
                "type": "npc_audio",
                "message_id": message_id,
                "audio_base64": audio_base64,
            })
    except Exception:
        logger.exception(
            "NPC audio generation failed session_id=%s message_id=%s",
            session.session_id,
            message_id,
        )


def _ws_error(message: str) -> dict:
    return {"type": "error", "message": message, "retryable": False}


def _threshold_for_streak(streak: int) -> int:
    """Pick the idle threshold for the given streak, saturating at the last value."""
    thresholds = PROACTIVE_IDLE_THRESHOLDS or [25, 20, 15]
    idx = min(streak, len(thresholds) - 1)
    return thresholds[idx]


def _apply_activity(session: GameSession, kind: str) -> None:
    """Mutate session state based on a client-side activity signal."""
    now = datetime.now(timezone.utc)
    if kind in ("typing_start", "audio_start"):
        session.is_user_active = True
    elif kind in ("typing_end", "audio_end"):
        session.is_user_active = False
        session.last_activity_at = now
    elif kind == "connection_resumed":
        session.is_user_active = False
        session.last_activity_at = now + timedelta(seconds=RECONNECT_GRACE_SECONDS)


async def _idle_monitor_task(
    ws: WebSocket,
    session_id: str,
    lock: asyncio.Lock,
    schedule_audio: Callable[[GameSession, str, str, str], None],
) -> None:
    """Background task that triggers proactive NPC speech after nurse idleness."""
    if not PROACTIVE_ENABLED:
        return

    try:
        while True:
            await asyncio.sleep(1)

            session = get_session(session_id)
            if session is None or session.start_time is None:
                continue
            if session.is_user_active or session.last_activity_at is None:
                continue

            now = datetime.now(timezone.utc)
            idle_seconds = (now - session.last_activity_at).total_seconds()
            if idle_seconds < 0:
                continue

            threshold = _threshold_for_streak(session.proactive_streak)
            if idle_seconds < threshold:
                continue

            async with lock:
                session = get_session(session_id)
                if session is None or session.start_time is None:
                    continue
                if session.is_user_active or session.last_activity_at is None:
                    continue

                now = datetime.now(timezone.utc)
                idle_seconds = (now - session.last_activity_at).total_seconds()
                threshold = _threshold_for_streak(session.proactive_streak)
                if idle_seconds < threshold:
                    continue

                content, sender, did_speak = await maybe_proactive_speak(session)
                if not did_speak:
                    session.last_activity_at = datetime.now(timezone.utc) - timedelta(seconds=threshold - 5)
                    update_session(session)
                    continue

                elapsed = _elapsed_seconds(session.start_time)
                msg_id = str(uuid.uuid4())
                message = ChatMessage(
                    id=msg_id,
                    sender=sender,
                    content=content,
                    timestamp=datetime.now(timezone.utc),
                    elapsed_seconds=elapsed,
                    is_proactive=True,
                )
                session.conversation_history.append(message)
                session.last_activity_at = datetime.now(timezone.utc)
                update_session(session)

                await _send_json(ws, {"type": "typing", "sender": sender})
                await _send_json(ws, {
                    "type": "npc_message",
                    "sender": sender,
                    "content": content,
                    "message_id": msg_id,
                    "elapsed_seconds": elapsed,
                    "is_proactive": True,
                })
                schedule_audio(session, msg_id, sender, content)
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("idle_monitor ended unexpectedly: %s", exc)


async def _timer_task(ws: WebSocket, session_id: str, start_time: datetime) -> None:
    """Background task that sends timer updates every 30 seconds and expires the session."""
    try:
        while True:
            await asyncio.sleep(30)
            elapsed = _elapsed_seconds(start_time)
            remaining = max(0, GAME_TIME_LIMIT - int(elapsed))

            if remaining <= 0:
                await _send_json(ws, {
                    "type": "timer_expired",
                    "message": "時間已到，請前往記錄頁面提交護理記錄。",
                })
                await ws.close()
                return

            await _send_json(ws, {
                "type": "timer_update",
                "remaining_seconds": remaining,
            })
    except Exception:
        # Connection closed or other error; just stop the timer.
        pass


async def _run_chat_session(ws: WebSocket, session_id: str) -> None:
    """Shared chat loop after session_id is known, for path-based or digiRunner flows."""
    session = get_session(session_id)
    if session is None:
        await _send_json(ws, _ws_error("Session not found"))
        await ws.close()
        return

    lock = _get_session_lock(session_id)

    if session.start_time is None:
        session.start_time = datetime.now(timezone.utc)
        session.status = SessionStatus.PLAYING

    session.last_activity_at = datetime.now(timezone.utc) + timedelta(seconds=RECONNECT_GRACE_SECONDS)
    session.is_user_active = False
    update_session(session)

    initial_elapsed = _elapsed_seconds(session.start_time)
    initial_remaining = max(0, GAME_TIME_LIMIT - int(initial_elapsed))
    await _send_json(ws, {
        "type": "timer_update",
        "remaining_seconds": initial_remaining,
    })

    timer = asyncio.create_task(_timer_task(ws, session_id, session.start_time))
    audio_tasks: set[asyncio.Task[None]] = set()

    def schedule_audio(session: GameSession, message_id: str, sender: str, content: str) -> None:
        task = asyncio.create_task(_send_audio_when_ready(ws, session, message_id, sender, content))
        audio_tasks.add(task)
        task.add_done_callback(audio_tasks.discard)

    idle_monitor = asyncio.create_task(_idle_monitor_task(ws, session_id, lock, schedule_audio))

    try:
        while True:
            raw = await ws.receive_text()

            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                await _send_json(ws, _ws_error("Invalid JSON"))
                continue

            msg_type = data.get("type")

            if msg_type == "activity":
                kind = data.get("kind")
                if kind not in _VALID_ACTIVITY_KINDS:
                    await _send_json(ws, _ws_error(f"Unknown activity kind: {kind}"))
                    continue
                session = get_session(session_id)
                if session is not None:
                    _apply_activity(session, kind)
                    update_session(session)
                continue

            if msg_type != "nurse_message":
                await _send_json(ws, _ws_error(f"Unknown message type: {msg_type}"))
                continue

            content = data.get("content", "").strip()
            target = data.get("target", "patient")

            if not content:
                await _send_json(ws, _ws_error("Empty message content"))
                continue

            session = get_session(session_id)
            if session is None:
                await _send_json(ws, _ws_error("Session expired"))
                await ws.close()
                return

            elapsed = _elapsed_seconds(session.start_time)

            if elapsed >= GAME_TIME_LIMIT:
                await _send_json(ws, {
                    "type": "timer_expired",
                    "message": "時間已到，請前往記錄頁面提交護理記錄。",
                })
                await ws.close()
                return

            async with lock:
                session = get_session(session_id)
                if session is None:
                    await _send_json(ws, _ws_error("Session expired"))
                    await ws.close()
                    return

                nurse_msg_id = str(uuid.uuid4())
                nurse_chat = ChatMessage(
                    id=nurse_msg_id,
                    sender="nurse",
                    content=content,
                    timestamp=datetime.now(timezone.utc),
                    elapsed_seconds=elapsed,
                )
                session.conversation_history.append(nurse_chat)
                session.current_target = target
                session.proactive_streak = 0
                session.is_user_active = False
                session.last_activity_at = datetime.now(timezone.utc)
                update_session(session)

                await _send_json(ws, {"type": "typing", "sender": target})

                try:
                    npc_text, sender = await get_npc_response(session, content, target)
                except Exception:
                    logger.exception("NPC response failed session_id=%s", session_id)
                    await _send_json(
                        ws,
                        _ws_error("NPC 回應暫時無法產生，請稍後再試。"),
                    )
                    continue

                elapsed = _elapsed_seconds(session.start_time)
                npc_msg_id = str(uuid.uuid4())

                npc_chat = ChatMessage(
                    id=npc_msg_id,
                    sender=sender,
                    content=npc_text,
                    timestamp=datetime.now(timezone.utc),
                    elapsed_seconds=elapsed,
                )
                session.conversation_history.append(npc_chat)
                session.last_activity_at = datetime.now(timezone.utc)
                update_session(session)

                await _send_json(ws, {
                    "type": "npc_message",
                    "sender": sender,
                    "content": npc_text,
                    "message_id": npc_msg_id,
                    "elapsed_seconds": elapsed,
                })
                schedule_audio(session, npc_msg_id, sender, npc_text)

                if target == "patient":
                    interjection_text, did_interject, family_index = await maybe_family_interjection(session)

                    if did_interject:
                        family_sender = f"family_{family_index}"

                        elapsed = _elapsed_seconds(session.start_time)
                        interjection_id = str(uuid.uuid4())

                        interjection_chat = ChatMessage(
                            id=interjection_id,
                            sender=family_sender,
                            content=interjection_text,
                            timestamp=datetime.now(timezone.utc),
                            elapsed_seconds=elapsed,
                            is_interjection=True,
                        )
                        session.conversation_history.append(interjection_chat)
                        session.last_activity_at = datetime.now(timezone.utc)
                        update_session(session)

                        await _send_json(ws, {"type": "typing", "sender": family_sender})
                        await _send_json(ws, {
                            "type": "npc_message",
                            "sender": family_sender,
                            "content": interjection_text,
                            "message_id": interjection_id,
                            "elapsed_seconds": elapsed,
                            "is_interjection": True,
                        })
                        schedule_audio(session, interjection_id, family_sender, interjection_text)

    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Chat websocket error session_id=%s", session_id)
        try:
            await _send_json(
                ws,
                _ws_error("連線發生錯誤，請重新整理或稍後再試。"),
            )
        except Exception:
            pass
    finally:
        timer.cancel()
        idle_monitor.cancel()
        for task in audio_tasks:
            task.cancel()
        _session_locks.pop(session_id, None)


@router.websocket("/ws")
async def chat_websocket_digirunner(ws: WebSocket) -> None:
    """Fixed path for digiRunner WebSocket Proxy.

    digiRunner exposes clients at ws://gateway/website/{siteName} and opens one backend URI per
    client; session_id must be sent as the first frame: {"type":"session_join","session_id":"..."}.
    """
    await ws.accept()
    try:
        raw = await ws.receive_text()
    except WebSocketDisconnect:
        return
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        await _send_json(ws, _ws_error("Invalid JSON"))
        await ws.close()
        return
    if data.get("type") != "session_join":
        await _send_json(ws, _ws_error("First message must be session_join"))
        await ws.close()
        return
    session_id = str(data.get("session_id", "")).strip()
    if not session_id:
        await _send_json(ws, _ws_error("session_id required"))
        await ws.close()
        return
    await _run_chat_session(ws, session_id)


@router.websocket("/{session_id}")
async def chat_websocket(ws: WebSocket, session_id: str) -> None:
    """WebSocket: /api/chat/{session_id} direct to FastAPI."""
    await ws.accept()
    await _run_chat_session(ws, session_id)
