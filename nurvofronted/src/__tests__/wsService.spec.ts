import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { connect, disconnect } from '@/services/wsService'
import { useChatStore } from '@/stores/chatStore'

class FakeWebSocket {
  static OPEN = 1
  static instances: FakeWebSocket[] = []

  readonly url: string
  readyState = FakeWebSocket.OPEN
  sent: string[] = []
  onopen: (() => void) | null = null
  onmessage: ((event: MessageEvent) => void) | null = null
  onclose: (() => void) | null = null
  onerror: ((event: Event) => void) | null = null

  constructor(url: string) {
    this.url = url
    FakeWebSocket.instances.push(this)
  }

  send(data: string): void {
    this.sent.push(data)
  }

  close(): void {
    this.onclose?.()
  }
}

describe('wsService', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    FakeWebSocket.instances = []
    vi.stubGlobal('WebSocket', FakeWebSocket)
    Object.defineProperty(window, 'location', {
      value: {
        protocol: 'http:',
        host: 'localhost:5173',
      },
      writable: true,
    })
  })

  it('connects through the digiRunner website path and sends session_join on open', () => {
    connect('session-123')

    const socket = FakeWebSocket.instances[0]!
    expect(socket.url).toBe('ws://localhost:5173/website/nurvo-chat')

    socket.onopen?.()

    expect(socket.sent).toEqual([
      JSON.stringify({ type: 'session_join', session_id: 'session-123' }),
      JSON.stringify({ type: 'activity', kind: 'connection_resumed' }),
    ])

    disconnect()
  })

  it('clears typing and exposes server errors when an NPC response fails', () => {
    connect('session-123')

    const socket = FakeWebSocket.instances[0]!
    const chatStore = useChatStore()
    chatStore.setTyping('family_0')

    socket.onmessage?.({
      data: JSON.stringify({ type: 'error', message: 'NPC 回應暫時無法產生，請稍後再試。' }),
    } as MessageEvent)

    expect(chatStore.typingIndicator).toBeNull()
    expect(chatStore.errorMessage).toBe('NPC 回應暫時無法產生，請稍後再試。')

    disconnect()
  })

  it('attaches async TTS audio to the matching NPC message', () => {
    connect('session-123')

    const socket = FakeWebSocket.instances[0]!
    const chatStore = useChatStore()

    socket.onmessage?.({
      data: JSON.stringify({
        type: 'npc_message',
        message_id: 'npc-1',
        sender: 'patient',
        content: '我這裡很痛',
        elapsed_seconds: 3,
      }),
    } as MessageEvent)

    socket.onmessage?.({
      data: JSON.stringify({
        type: 'npc_audio',
        message_id: 'npc-1',
        audio_base64: 'audio',
      }),
    } as MessageEvent)

    expect(chatStore.messages[0]?.audio_base64).toBe('audio')

    disconnect()
  })
})
