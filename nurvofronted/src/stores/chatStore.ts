import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { ChatMessage, FamilySender } from '@/types/game'

export const useChatStore = defineStore('chat', () => {
  const messages = ref<ChatMessage[]>([])
  const isConnected = ref(false)
  const typingIndicator = ref<'patient' | FamilySender | null>(null)
  const currentTarget = ref<'patient' | FamilySender>('patient')
  const errorMessage = ref<string>('')

  function addMessage(message: ChatMessage) {
    messages.value.push(message)
  }

  function setMessageAudio(messageId: string, audioBase64: string) {
    const message = messages.value.find((item) => item.id === messageId)
    if (message) {
      message.audio_base64 = audioBase64
    }
  }

  function setTarget(target: 'patient' | FamilySender) {
    currentTarget.value = target
  }

  function clearMessages() {
    messages.value = []
    typingIndicator.value = null
    errorMessage.value = ''
  }

  function setConnected(connected: boolean) {
    isConnected.value = connected
  }

  function setTyping(sender: 'patient' | FamilySender | null) {
    typingIndicator.value = sender
  }

  function setError(message: string) {
    errorMessage.value = message
  }

  function clearError() {
    errorMessage.value = ''
  }

  function reset() {
    messages.value = []
    isConnected.value = false
    typingIndicator.value = null
    currentTarget.value = 'patient'
    errorMessage.value = ''
  }

  return {
    messages,
    isConnected,
    typingIndicator,
    currentTarget,
    errorMessage,
    addMessage,
    setMessageAudio,
    setTarget,
    clearMessages,
    setConnected,
    setTyping,
    setError,
    clearError,
    reset,
  }
})
