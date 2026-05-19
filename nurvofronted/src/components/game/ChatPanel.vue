<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chatStore'
import { useGameStore } from '@/stores/gameStore'
import { useScenarioStore } from '@/stores/scenarioStore'
import { sendMessage } from '@/services/wsService'
import { decodeAndPlay, unlock as unlockAudio } from '@/services/audioService'
import * as speechService from '@/services/speechService'
import { isFamilySender, familyDisplayIndex, genderAvatar } from '@/types/game'
import type { FamilySender } from '@/types/game'
import ChatBubble from './ChatBubble.vue'

const router = useRouter()
const chatStore = useChatStore()
const gameStore = useGameStore()
const scenarioStore = useScenarioStore()

const familyMembers = computed(() => scenarioStore.scenario?.family_members ?? [])

const inputText = ref<string>('')
const messagesContainer = ref<HTMLElement | null>(null)
const isRecording = ref<boolean>(false)
const isTranscribing = ref<boolean>(false)
const speechSupported: boolean = speechService.isSupported()
const playedAudioMessageIds = new Set<string>()
const patientAvatar = String.fromCodePoint(0x1f9d3)

const filteredMessages = computed(() => {
  return chatStore.messages
})

const typingLabel = computed<string>(() => {
  if (!chatStore.typingIndicator) return ''
  if (chatStore.typingIndicator === 'patient') return '病患正在輸入...'
  if (isFamilySender(chatStore.typingIndicator)) {
    const idx = familyDisplayIndex(chatStore.typingIndicator)
    const name = familyMembers.value[idx]?.name ?? `家屬${idx + 1}`
    return `${name}正在輸入...`
  }
  return ''
})

const placeholder = computed<string>(() => {
  if (chatStore.currentTarget === 'patient') return '輸入訊息給病患...'
  if (isFamilySender(chatStore.currentTarget)) {
    const idx = familyDisplayIndex(chatStore.currentTarget)
    const name = familyMembers.value[idx]?.name ?? `家屬${idx + 1}`
    return `輸入訊息給${name}...`
  }
  return '輸入訊息...'
})

const typingAvatar = computed<string>(() => {
  const indicator = chatStore.typingIndicator
  if (indicator === 'patient') return patientAvatar
  if (indicator && isFamilySender(indicator)) {
    const idx = familyDisplayIndex(indicator)
    return genderAvatar(familyMembers.value[idx]?.gender)
  }
  return ''
})

const disabled = computed<boolean>(() => {
  return !chatStore.isConnected
})

const canSend = computed<boolean>(() => {
  return !!inputText.value.trim() && chatStore.isConnected
})

function handleSend(): void {
  unlockAudio()
  const content = inputText.value.trim()
  if (!content) return

  sendMessage(chatStore.currentTarget, content)

  chatStore.addMessage({
    id: `nurse-${Date.now()}`,
    sender: 'nurse',
    content,
    timestamp: new Date().toISOString(),
    elapsed_seconds: 0,
    is_interjection: false,
  })

  inputText.value = ''
}

function handleEnterKey(event: KeyboardEvent): void {
  // Avoid sending while the IME is still composing Chinese characters.
  if (event.isComposing || event.keyCode === 229) {
    return
  }
  event.preventDefault()
  handleSend()
}

function switchTarget(target: 'patient' | FamilySender): void {
  chatStore.setTarget(target)
}

function goToRecord(): void {
  gameStore.setStatus('recording')
  router.push('/record')
}

function scrollToBottom(): void {
  if (messagesContainer.value) {
    messagesContainer.value.scrollTop = messagesContainer.value.scrollHeight
  }
}

function playPendingAudio(): void {
  const currentMessageIds = new Set(chatStore.messages.map((message) => message.id))
  playedAudioMessageIds.forEach((messageId) => {
    if (!currentMessageIds.has(messageId)) {
      playedAudioMessageIds.delete(messageId)
    }
  })

  for (const message of chatStore.messages) {
    if (message.sender !== 'nurse' && message.audio_base64 && !playedAudioMessageIds.has(message.id)) {
      playedAudioMessageIds.add(message.id)
      decodeAndPlay(message.audio_base64)
    }
  }
}

async function toggleRecording(): Promise<void> {
  if (isRecording.value) {
    speechService.stop()
    isRecording.value = false
    isTranscribing.value = true
  } else {
    isTranscribing.value = false
    await speechService.start(
      (text: string) => {
        inputText.value += text
        isTranscribing.value = false
      },
      (_error: string) => {
        isTranscribing.value = false
      },
    )
    isRecording.value = true
  }
}

// Auto-play audio when new NPC audio arrives, including async TTS updates.
watch(
  () => chatStore.messages.map((message) => `${message.id}:${message.audio_base64 ? '1' : '0'}`).join('|'),
  () => {
    playPendingAudio()
    nextTick(scrollToBottom)
  },
)
</script>

<template>
  <div class="chat-panel">
    <!-- Tab bar -->
    <div class="tab-bar">
      <button
        class="tab-btn"
        :class="{ 'tab-btn--active': chatStore.currentTarget === 'patient' }"
        @click="switchTarget('patient')"
      >
        &#x1F9D3; 病患
      </button>
      <button
        v-for="(fm, idx) in familyMembers"
        :key="idx"
        class="tab-btn"
        :class="{ 'tab-btn--active': chatStore.currentTarget === `family_${idx}` }"
        @click="switchTarget(`family_${idx}` as FamilySender)"
      >
        {{ genderAvatar(fm.gender) }} {{ fm.name }}
      </button>
    </div>

    <!-- Messages area -->
    <div ref="messagesContainer" class="messages-area">
      <div v-if="filteredMessages.length === 0" class="empty-state">
        <p>開始與{{ chatStore.currentTarget === 'patient' ? '病患' : placeholder.replace('輸入訊息給', '').replace('...', '') }}對話</p>
        <p class="empty-hint">輸入訊息開始溝通評估</p>
      </div>

      <ChatBubble v-for="msg in filteredMessages" :key="msg.id" :message="msg" />

      <div v-if="chatStore.errorMessage" class="chat-error">
        {{ chatStore.errorMessage }}
      </div>

      <!-- Typing indicator -->
      <div v-if="chatStore.typingIndicator" class="typing-row">
        <div
          class="bubble-avatar"
          :class="chatStore.typingIndicator === 'patient' ? 'bubble-avatar--patient' : 'bubble-avatar--family'"
        >
          {{ typingAvatar }}
        </div>
        <span class="typing-label">{{ typingLabel }}</span>
        <div class="typing-bubble">
          <span class="typing-dots">
            <span></span><span></span><span></span>
          </span>
        </div>
      </div>
    </div>

    <!-- Input area -->
    <div class="input-area">
      <div class="input-row">
        <textarea
          v-model="inputText"
          :placeholder="placeholder"
          :disabled="disabled"
          rows="1"
          class="input-textarea"
          @keydown.enter.exact="handleEnterKey"
        ></textarea>
        <button
          v-if="speechSupported"
          class="input-btn input-btn--mic"
          :class="{ 'input-btn--recording': isRecording, 'input-btn--transcribing': isTranscribing }"
          :disabled="disabled || isTranscribing"
          :title="isTranscribing ? '辨識中...' : isRecording ? '停止錄音' : '語音輸入'"
          @click="toggleRecording"
        >
          <span v-if="isTranscribing" class="transcribing-spinner"></span>
          <span v-else>&#x1F3A4;</span>
        </button>
        <button
          class="input-btn input-btn--send"
          :disabled="!canSend"
          @click="handleSend"
        >
          &#x27A4;
        </button>
      </div>
      <button class="record-link" @click="goToRecord">
        &#x1F4DD; 完成並記錄
      </button>
    </div>
  </div>
</template>

<style scoped>
.chat-panel {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: transparent;
}

/* Tab bar */
.tab-bar {
  display: flex;
  padding: 8px 12px;
  gap: 6px;
  border-bottom: 1px solid var(--nurvo-border-light);
  background: rgba(255, 255, 255, 0.18);
  flex-shrink: 0;
}

.tab-btn {
  flex: 1;
  padding: 8px;
  border-radius: var(--nurvo-radius-sm);
  font-size: 11px;
  font-weight: 600;
  border: 1px solid var(--nurvo-border);
  background: var(--nurvo-surface);
  color: var(--nurvo-text-secondary);
  cursor: pointer;
  transition: all 0.2s;
  font-family: var(--nurvo-font-family);
  text-align: center;
}

.tab-btn--active {
  background: var(--nurvo-primary);
  color: white;
  border-color: var(--nurvo-primary);
}

/* Messages area */
.messages-area {
  flex: 1;
  overflow-y: auto;
  padding: 12px;
  background: transparent;
}

.messages-area::-webkit-scrollbar {
  width: 4px;
}

.messages-area::-webkit-scrollbar-track {
  background: transparent;
}

.messages-area::-webkit-scrollbar-thumb {
  background: var(--nurvo-border);
  border-radius: 2px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #ffffff;
  text-align: center;
  gap: 6px;
}

.empty-state p {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
  text-shadow: 0 2px 8px rgba(15, 23, 42, 0.35);
}

.empty-hint {
  font-size: 14px !important;
  opacity: 0.9;
}

.chat-error {
  margin: 8px 0 12px;
  border: 1px solid rgba(252, 165, 165, 0.8);
  border-radius: 10px;
  background: rgba(254, 242, 242, 0.95);
  color: #991b1b;
  font-size: 12px;
  font-weight: 700;
  line-height: 1.4;
  padding: 9px 12px;
}

/* Typing indicator */
.typing-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-bottom: 10px;
}

.bubble-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 12px;
}

.bubble-avatar--patient {
  background: linear-gradient(135deg, var(--nurvo-patient-light), var(--nurvo-patient));
}

.bubble-avatar--family {
  background: linear-gradient(135deg, var(--nurvo-family), var(--nurvo-family-dark));
}

.typing-bubble {
  background: var(--nurvo-patient-bubble);
  padding: 10px 16px;
  border-radius: 2px 14px 14px 14px;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--nurvo-text-muted);
  animation: typingBounce 1.4s ease-in-out infinite;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typingBounce {
  0%, 60%, 100% { transform: translateY(0); }
  30% { transform: translateY(-4px); }
}

/* Input area */
.input-area {
  border-top: 1px solid var(--nurvo-border-light);
  padding: 10px 12px;
  background: rgba(255, 255, 255, 0.2);
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.input-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
  width: 100%;
}

.input-textarea {
  flex: 1;
  background: var(--nurvo-surface);
  border: 1px solid var(--nurvo-border);
  border-radius: var(--nurvo-radius-md);
  padding: 10px 14px;
  font-size: 12px;
  color: var(--nurvo-text-primary);
  font-family: var(--nurvo-font-family);
  resize: none;
  outline: none;
  line-height: 1.4;
  min-height: 20px;
  transition: border-color 0.2s;
}

.input-textarea::placeholder {
  color: var(--nurvo-text-muted);
}

.input-textarea:focus {
  border-color: var(--nurvo-primary-border);
}

.input-textarea:disabled {
  opacity: 0.5;
}

.input-btn {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  flex-shrink: 0;
  border: none;
  font-size: 14px;
  transition: opacity 0.2s;
}

.input-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.input-btn--mic {
  background: var(--nurvo-surface);
  border: 1px solid var(--nurvo-border);
}

.input-btn--recording {
  background: var(--nurvo-danger-light);
  border-color: var(--nurvo-danger-border);
}

.input-btn--transcribing {
  background: var(--nurvo-surface);
  border-color: var(--nurvo-primary-border);
  opacity: 0.7;
}

.transcribing-spinner {
  width: 14px;
  height: 14px;
  border: 2px solid var(--nurvo-border);
  border-top-color: var(--nurvo-primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  display: inline-block;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.input-btn--send {
  background: var(--nurvo-gradient-primary);
  color: white;
  box-shadow: 0 2px 8px rgba(37, 99, 235, 0.25);
}

.record-link {
  background: none;
  border: none;
  font-size: 10px;
  color: var(--nurvo-text-muted);
  cursor: pointer;
  padding: 4px 12px;
  border-radius: 6px;
  background: var(--nurvo-surface);
  transition: color 0.2s;
  font-family: var(--nurvo-font-family);
}

.record-link:hover {
  color: var(--nurvo-text-secondary);
}
</style>
