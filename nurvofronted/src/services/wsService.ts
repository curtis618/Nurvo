import { useChatStore } from '@/stores/chatStore'
import type {
  WsServerMessage,
  WsNurseMessage,
  WsActivityMessage,
  WsActivityKind,
  ChatMessage,
  FamilySender,
} from '@/types/game'
import { isFamilySender } from '@/types/game'

let ws: WebSocket | null = null
let reconnectTimer: ReturnType<typeof setTimeout> | null = null
let currentSessionId: string | null = null
const RECONNECT_DELAY = 3000
const USE_MOCK_API = import.meta.env.DEV && import.meta.env.VITE_USE_MOCK_API === 'true'
/** digiRunner WebSocket Proxy 站點名稱（對應 /website/{siteName}）；見 digiRunner WebSocketServer.java */
const DIGIRUNNER_WS_SITE = import.meta.env.VITE_DIGIRUNNER_WS_SITE ?? 'nurvo-chat'

// Timer event callbacks
let _onTimerUpdate: ((seconds: number) => void) | null = null
let _onTimerExpired: (() => void) | null = null

function randomId(prefix: string): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`
}

function createMockReply(target: 'patient' | FamilySender, nurseContent: string): string {
  if (target === 'patient') {
    return `我了解，關於「${nurseContent.slice(0, 12)}」我想補充：現在主要是傷口附近刺痛，翻身時更明顯。`
  }
  return `護理師您好，我有點擔心，剛剛提到「${nurseContent.slice(0, 12)}」的部分可以再說明一下嗎？`
}

/**
 * Register a callback for timer_update events.
 */
export function onTimerUpdate(cb: (seconds: number) => void): void {
  _onTimerUpdate = cb
}

/**
 * Register a callback for timer_expired events.
 */
export function onTimerExpired(cb: () => void): void {
  _onTimerExpired = cb
}

function getWsUrl(_sessionId: string): string {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  // digiRunner 固定入口 /website/{siteName}；session 以第一則 session_join 傳（後端 /api/chat/ws）
  return `${protocol}//${window.location.host}/website/${DIGIRUNNER_WS_SITE}`
}

function handleMessage(event: MessageEvent) {
  const chatStore = useChatStore()

  let data: WsServerMessage
  try {
    data = JSON.parse(event.data)
  } catch {
    console.error('[wsService] 無法解析伺服器訊息:', event.data)
    return
  }

  switch (data.type) {
    case 'npc_message': {
      const message: ChatMessage = {
        id: data.message_id,
        sender: data.sender,
        content: data.content,
        timestamp: new Date().toISOString(),
        elapsed_seconds: data.elapsed_seconds,
        is_interjection: data.is_interjection ?? false,
        is_proactive: data.is_proactive ?? false,
        audio_base64: data.audio_base64,
      }
      chatStore.setTyping(null)
      chatStore.clearError()
      chatStore.addMessage(message)
      break
    }
    case 'npc_audio': {
      chatStore.setMessageAudio(data.message_id, data.audio_base64)
      break
    }
    case 'typing': {
      chatStore.setTyping(data.sender)
      break
    }
    case 'timer_update': {
      if (_onTimerUpdate) {
        _onTimerUpdate(data.remaining_seconds)
      }
      break
    }
    case 'timer_expired': {
      console.warn('[wsService] 時間已到:', data.message)
      if (_onTimerExpired) {
        _onTimerExpired()
      }
      break
    }
    case 'error': {
      console.error('[wsService] 伺服器錯誤:', data.message)
      chatStore.setTyping(null)
      chatStore.setError(data.message)
      break
    }
  }
}

export function connect(sessionId: string) {
  disconnect()
  currentSessionId = sessionId

  const chatStore = useChatStore()

  if (USE_MOCK_API) {
    chatStore.setConnected(true)
    return
  }

  const url = getWsUrl(sessionId)

  ws = new WebSocket(url)

  ws.onopen = () => {
    ws!.send(JSON.stringify({ type: 'session_join', session_id: sessionId }))
    chatStore.setConnected(true)
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
      reconnectTimer = null
    }
    sendActivity('connection_resumed')
  }

  ws.onmessage = handleMessage

  ws.onclose = () => {
    chatStore.setConnected(false)
    if (currentSessionId) {
      reconnectTimer = setTimeout(() => {
        if (currentSessionId) {
          connect(currentSessionId)
        }
      }, RECONNECT_DELAY)
    }
  }

  ws.onerror = (error) => {
    console.error('[wsService] WebSocket 錯誤:', error)
  }
}

export function sendActivity(kind: WsActivityKind): void {
  if (USE_MOCK_API) return
  if (!ws || ws.readyState !== WebSocket.OPEN) return

  const payload: WsActivityMessage = { type: 'activity', kind }
  ws.send(JSON.stringify(payload))
}

export function sendMessage(target: 'patient' | FamilySender, content: string) {
  const chatStore = useChatStore()
  chatStore.clearError()

  if (USE_MOCK_API) {
    chatStore.setTyping(target)

    const delayMs = 500 + Math.floor(Math.random() * 500)
    setTimeout(() => {
      const message: ChatMessage = {
        id: randomId('mock-reply'),
        sender: target,
        content: createMockReply(target, content),
        timestamp: new Date().toISOString(),
        elapsed_seconds: 0,
        is_interjection: isFamilySender(target) && Math.random() > 0.6,
      }
      chatStore.setTyping(null)
      chatStore.addMessage(message)
    }, delayMs)

    return
  }
  if (!ws || ws.readyState !== WebSocket.OPEN) {
    console.error('[wsService] WebSocket 尚未連線')
    chatStore.setError('WebSocket 尚未連線，請稍後再試。')
    return
  }

  const payload: WsNurseMessage = {
    type: 'nurse_message',
    target,
    content,
  }

  ws.send(JSON.stringify(payload))
}

export function disconnect() {
  currentSessionId = null
  _onTimerUpdate = null
  _onTimerExpired = null

  if (reconnectTimer) {
    clearTimeout(reconnectTimer)
    reconnectTimer = null
  }

  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }

  const chatStore = useChatStore()
  chatStore.setConnected(false)
}
