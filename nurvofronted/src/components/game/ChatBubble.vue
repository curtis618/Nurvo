<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage } from '@/types/game'
import { isFamilySender, familyDisplayIndex, genderAvatar } from '@/types/game'
import { decodeAndPlay } from '@/services/audioService'
import { useScenarioStore } from '@/stores/scenarioStore'

const props = defineProps<{
  message: ChatMessage
}>()

const scenarioStore = useScenarioStore()

const isNurse = computed(() => props.message.sender === 'nurse')
const hasAudio = computed(() => !!props.message.audio_base64)

const senderLabel = computed(() => {
  if (props.message.sender === 'nurse') return '你'
  if (props.message.sender === 'patient') return '病患'
  if (isFamilySender(props.message.sender)) {
    const idx = familyDisplayIndex(props.message.sender)
    return scenarioStore.scenario?.family_members[idx]?.name ?? `家屬${idx + 1}`
  }
  return ''
})

const senderClass = computed(() => {
  if (isFamilySender(props.message.sender)) return 'family'
  return props.message.sender
})

const senderAvatar = computed(() => {
  if (props.message.sender === 'nurse') return 'N'
  if (props.message.sender === 'patient') return String.fromCodePoint(0x1f9d3)
  if (isFamilySender(props.message.sender)) {
    const idx = familyDisplayIndex(props.message.sender)
    return genderAvatar(scenarioStore.scenario?.family_members[idx]?.gender)
  }
  return ''
})

const formattedTime = computed(() => {
  const totalSeconds = props.message.elapsed_seconds
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
})

function replayAudio() {
  if (props.message.audio_base64) {
    decodeAndPlay(props.message.audio_base64)
  }
}
</script>

<template>
  <div class="bubble-row" :class="{ 'bubble-row--nurse': isNurse }">
    <!-- Avatar -->
    <div
      class="bubble-avatar"
      :class="`bubble-avatar--${senderClass}`"
    >
      {{ senderAvatar }}
    </div>

    <!-- Content -->
    <div class="bubble-body" :class="{ 'bubble-body--nurse': isNurse }">
      <div class="bubble-meta">
        <span class="bubble-sender" :class="`bubble-sender--${senderClass}`">
          {{ senderLabel }}
        </span>
        <span v-if="message.is_interjection && isFamilySender(message.sender)" class="bubble-interjection">
          插話
        </span>
        <span class="bubble-time">{{ formattedTime }}</span>
      </div>
      <div class="bubble-content" :class="`bubble-content--${senderClass}`">
        {{ message.content }}
      </div>
      <button v-if="hasAudio" class="bubble-audio" @click="replayAudio">
        &#x1F50A; 播放語音
      </button>
    </div>
  </div>
</template>

<style scoped>
.bubble-row {
  display: flex;
  gap: 8px;
  align-items: flex-start;
  margin-bottom: 10px;
}

.bubble-row--nurse {
  flex-direction: row-reverse;
}

/* Avatar */
.bubble-avatar {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  font-size: 12px;
  line-height: 1;
}

.bubble-avatar--patient {
  background: linear-gradient(135deg, var(--nurvo-patient-light), var(--nurvo-patient));
}

.bubble-avatar--family {
  background: linear-gradient(135deg, var(--nurvo-family), var(--nurvo-family-dark));
}

.bubble-avatar--nurse {
  background: linear-gradient(135deg, var(--nurvo-nurse-light), var(--nurvo-nurse));
  color: white;
  font-weight: 700;
  font-size: 10px;
}

/* Body */
.bubble-body {
  max-width: 80%;
}

.bubble-body--nurse {
  text-align: right;
}

/* Meta */
.bubble-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}

.bubble-row--nurse .bubble-meta {
  flex-direction: row-reverse;
}

.bubble-sender {
  font-size: 10px;
  font-weight: 600;
}

.bubble-sender--patient {
  color: var(--nurvo-patient-darker);
}

.bubble-sender--family {
  color: var(--nurvo-warning-darker);
}

.bubble-sender--nurse {
  color: var(--nurvo-nurse-text);
}

.bubble-time {
  font-size: 10px;
  color: var(--nurvo-text-muted);
  font-variant-numeric: tabular-nums;
}

.bubble-interjection {
  background: var(--nurvo-warning-border);
  color: var(--nurvo-family-text-dark);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 9px;
  font-weight: 700;
}

/* Content bubble */
.bubble-content {
  padding: 10px 14px;
  font-size: 12px;
  color: var(--nurvo-text-primary);
  line-height: 1.4;
  word-break: break-word;
}

.bubble-content--patient {
  background: var(--nurvo-patient-bubble);
  border-radius: 2px 14px 14px 14px;
}

.bubble-content--family {
  background: var(--nurvo-family-bubble);
  border: 1px solid var(--nurvo-warning-border);
  border-radius: 2px 14px 14px 14px;
}

.bubble-content--nurse {
  background: var(--nurvo-nurse-bubble);
  border-radius: 14px 2px 14px 14px;
  text-align: left;
}

/* Audio replay */
.bubble-audio {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 9px;
  color: var(--nurvo-text-muted);
  padding: 2px 0;
  margin-top: 3px;
  transition: color 0.2s;
}

.bubble-audio:hover {
  color: var(--nurvo-text-secondary);
}
</style>
