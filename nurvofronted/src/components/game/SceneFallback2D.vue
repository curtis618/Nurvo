<script setup lang="ts">
import { computed } from 'vue'
import type { ChatMessage, FamilyMember, FamilySender } from '@/types/game'

interface TopBubbleItem {
  id: string
  label: string
  target: 'patient' | FamilySender
  variant?: 'patient' | 'family'
}

const props = defineProps<{
  patientName?: string
  familyMembers?: FamilyMember[]
  topBubbles?: TopBubbleItem[]
  latestMessage?: ChatMessage | null
  backgroundUrl?: string | null
}>()

const backgroundStyle = computed<Record<string, string> | undefined>(() => {
  const url = props.backgroundUrl
  if (!url) return undefined
  return {
    backgroundImage: `linear-gradient(180deg, rgba(8, 47, 73, 0.08) 0%, rgba(2, 6, 23, 0.18) 100%), url("${url}")`,
  }
})

const emit = defineEmits<{
  (e: 'select-target', target: 'patient' | FamilySender): void
}>()

const showPatientBubble = computed<boolean>(() => props.latestMessage?.sender === 'patient')

const showBottomDialog = computed<boolean>(() => {
  const sender = props.latestMessage?.sender
  return sender === 'patient' || (typeof sender === 'string' && sender.startsWith('family_'))
})

const dialogSpeakerName = computed<string>(() => {
  const sender = props.latestMessage?.sender
  if (sender === 'patient') return props.patientName || '病患'
  if (typeof sender === 'string' && sender.startsWith('family_')) {
    const idx = parseInt(sender.split('_')[1]!)
    return props.familyMembers?.[idx]?.name || '家屬'
  }
  return ''
})

const isFamilySpeaker = computed<boolean>(() => {
  const sender = props.latestMessage?.sender
  return typeof sender === 'string' && sender.startsWith('family_')
})

const resolvedTopBubbles = computed<TopBubbleItem[]>(() => {
  if (props.topBubbles && props.topBubbles.length > 0) {
    return props.topBubbles
  }

  const bubbles: TopBubbleItem[] = [
    {
      id: 'patient-default',
      label: props.patientName || '病患',
      target: 'patient',
      variant: 'patient',
    },
  ]

  if (props.familyMembers && props.familyMembers.length > 0) {
    props.familyMembers.forEach((fm, idx) => {
      bubbles.push({
        id: `family-default-${idx}`,
        label: fm.name || '家屬',
        target: `family_${idx}` as FamilySender,
        variant: 'family',
      })
    })
  }

  return bubbles
})

const dialogContent = computed<string>(() => props.latestMessage?.content ?? '')

const familyPositions = ['8%', '20%', '32%']
</script>

<template>
  <div class="scene-fallback-2d" :style="backgroundStyle">
    <div class="room">
      <div class="top-bubbles">
        <button
          v-for="bubble in resolvedTopBubbles"
          :key="bubble.id"
          class="top-bubble"
          :class="{ 'top-bubble--family': bubble.variant === 'family' }"
          type="button"
          @click="emit('select-target', bubble.target)"
        >
          {{ bubble.label }}
        </button>
      </div>

      <!-- Wall -->
      <div class="wall">
        <div class="window">
          <div class="window-frame">
            <div class="window-pane"></div>
            <div class="window-pane"></div>
          </div>
        </div>
      </div>

      <!-- Floor -->
      <div class="floor"></div>

      <!-- Bed -->
      <div class="bed">
        <div class="bed-headboard"></div>
        <div class="bed-mattress"></div>
        <div class="bed-footboard"></div>
      </div>

      <!-- Patient -->
      <div
        class="character patient"
        role="button"
        :title="'點擊與' + (patientName || '病患') + '對話'"
        @click="emit('select-target', 'patient')"
      >
        <div class="person-head person-head--patient"></div>
        <div class="person-body person-body--patient"></div>
      </div>

      <!-- Family Members -->
      <div
        v-for="(fm, idx) in (familyMembers ?? [])"
        :key="`family-${idx}`"
        class="character family"
        :style="{ right: familyPositions[idx] }"
        role="button"
        :title="'點擊與' + fm.name + '對話'"
        @click="emit('select-target', `family_${idx}` as FamilySender)"
      >
        <div class="person-head person-head--family"></div>
        <div class="person-body person-body--family"></div>
      </div>

      <!-- Nurse -->
      <div class="character nurse">
        <div class="person-head person-head--nurse"></div>
        <div class="person-body person-body--nurse"></div>
        <div class="person-legs"></div>
        <span class="character-label">護理師（你）</span>
      </div>

      <div
        v-if="showBottomDialog"
        class="bottom-dialog"
        :class="{ 'bottom-dialog--family': isFamilySpeaker }"
      >
        <span class="bottom-dialog__speaker">{{ dialogSpeakerName }}</span>
        <p class="bottom-dialog__content">{{ dialogContent }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.scene-fallback-2d {
  width: 100%;
  height: 100%;
  min-height: 500px;
  background-image:
    linear-gradient(180deg, rgba(8, 47, 73, 0.08) 0%, rgba(2, 6, 23, 0.18) 100%),
    url('/hospital_bg.jpg');
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
  overflow: hidden;
  position: relative;
}

.room {
  width: 100%;
  height: 100%;
  position: relative;
}

.top-bubbles {
  position: absolute;
  top: 14px;
  left: 16px;
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  z-index: 8;
  max-width: calc(100% - 32px);
}

.top-bubble {
  border: 1px solid rgba(186, 230, 253, 0.95);
  background: rgba(255, 255, 255, 0.95);
  color: #0f172a;
  border-radius: 999px;
  padding: 7px 14px;
  font-size: 14px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.16);
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.top-bubble:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 20px rgba(15, 23, 42, 0.2);
}

.top-bubble--family {
  border-color: rgba(251, 191, 36, 0.75);
  background: rgba(254, 243, 199, 0.94);
}

.wall,
.floor,
.bed,
.person-head,
.person-body,
.person-legs,
.character.nurse {
  display: none;
}

/* Wall */
.wall {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  height: 55%;
  background: linear-gradient(180deg, var(--nurvo-patient-bg-alt) 0%, var(--nurvo-patient-light) 100%);
  border-bottom: 3px solid var(--nurvo-border);
}

.window {
  position: absolute;
  top: 15%;
  left: 10%;
  width: 120px;
  height: 100px;
  background: var(--nurvo-patient-bg);
  border: 4px solid var(--nurvo-text-muted);
  border-radius: var(--nurvo-radius-sm);
}

.window-frame {
  display: flex;
  width: 100%;
  height: 100%;
}

.window-pane {
  flex: 1;
  background: linear-gradient(135deg, var(--nurvo-patient-light), var(--nurvo-patient));
  border: 2px solid var(--nurvo-text-muted);
  opacity: 0.6;
}

/* Floor */
.floor {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  height: 45%;
  background: linear-gradient(180deg, var(--nurvo-border) 0%, #cbd5e1 100%);
}

/* Bed */
.bed {
  position: absolute;
  top: 38%;
  left: 20%;
  width: 45%;
  height: 25%;
}

.bed-headboard {
  position: absolute;
  left: 0;
  top: 0;
  width: 8%;
  height: 100%;
  background: #a8a29e;
  border-radius: 4px 0 0 4px;
  border: 1px solid #78716c;
}

.bed-mattress {
  position: absolute;
  left: 8%;
  top: 15%;
  width: 84%;
  height: 70%;
  background: var(--nurvo-white);
  border: 2px solid #d1d5db;
  border-radius: 2px;
}

.bed-footboard {
  position: absolute;
  right: 0;
  top: 10%;
  width: 8%;
  height: 80%;
  background: #a8a29e;
  border-radius: 0 4px 4px 0;
  border: 1px solid #78716c;
}

/* Characters */
.character {
  position: absolute;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: flex-end;
  width: 110px;
  height: 130px;
  transition: transform 0.2s ease;
}

.character.patient,
.character.family {
  cursor: pointer;
}

.character.patient:hover,
.character.family:hover {
  transform: scale(1.05);
}

.character.patient { top: 36%; left: 28%; }
.character.family { top: 32%; }
.character.nurse { bottom: 8%; left: 50%; transform: translateX(-50%); cursor: default; }

/* Heads */
.person-head {
  border-radius: 50%;
  border: 2px solid;
}

.person-head--patient {
  width: 30px;
  height: 30px;
  background: var(--nurvo-patient);
  border-color: var(--nurvo-patient-dark);
}

.person-head--family {
  width: 28px;
  height: 28px;
  background: var(--nurvo-family);
  border-color: var(--nurvo-family-dark);
}


.person-head--nurse {
  width: 32px;
  height: 32px;
  background: var(--nurvo-nurse-light);
  border-color: var(--nurvo-primary);
}

/* Bodies */
.person-body--patient {
  width: 60px;
  height: 20px;
  background: var(--nurvo-patient-light);
  border-radius: 4px;
  margin-top: -2px;
  border: 1px solid var(--nurvo-patient);
}

.person-body--family {
  width: 36px;
  height: 40px;
  background: var(--nurvo-family);
  border-radius: 8px 8px 4px 4px;
  margin-top: 2px;
  border: 1px solid var(--nurvo-family-dark);
}

.person-body--nurse {
  width: 38px;
  height: 42px;
  background: var(--nurvo-white);
  border-radius: 8px 8px 4px 4px;
  margin-top: 2px;
  border: 1px solid var(--nurvo-border);
}

.person-legs {
  display: flex;
  gap: 6px;
  margin-top: 2px;
}

.person-legs::before,
.person-legs::after {
  content: '';
  width: 10px;
  height: 24px;
  background: var(--nurvo-text-muted);
  border-radius: 0 0 4px 4px;
}

.bottom-dialog {
  position: absolute;
  left: 50%;
  bottom: 16px;
  transform: translateX(-50%);
  width: min(760px, calc(100% - 32px));
  max-height: min(34%, 220px);
  overflow-y: auto;
  border-radius: 14px;
  border: 1px solid rgba(147, 197, 253, 0.8);
  background: rgba(239, 246, 255, 0.95);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.24);
  padding: 12px 16px;
  z-index: 9;
}

.bottom-dialog--family {
  border-color: rgba(251, 191, 36, 0.75);
  background: rgba(254, 243, 199, 0.95);
}

.bottom-dialog__speaker {
  display: inline-block;
  margin-bottom: 6px;
  padding: 2px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  color: #1e3a8a;
  background: rgba(255, 255, 255, 0.85);
}

.bottom-dialog--family .bottom-dialog__speaker {
  color: #92400e;
}

.bottom-dialog__content {
  margin: 0;
  color: #0f172a;
  font-size: 14px;
  font-weight: 600;
  line-height: 1.5;
  white-space: pre-wrap;
  overflow-wrap: anywhere;
}

.character-label {
  margin-top: 0;
  font-size: 14px;
  color: #0f172a;
  font-weight: 700;
  white-space: nowrap;
  background: rgba(255, 255, 255, 0.92);
  padding: 6px 10px;
  border-radius: 999px;
  border: 1px solid rgba(186, 230, 253, 0.95);
  box-shadow: 0 8px 18px rgba(15, 23, 42, 0.16);
}

.character.patient:hover .character-label {
  color: var(--nurvo-text-primary);
  background: rgba(255, 255, 255, 0.95);
}

/* Speech bubbles */
.speech-bubble {
  position: absolute;
  bottom: 110%;
  left: 50%;
  transform: translateX(-50%);
  padding: 8px 12px;
  border-radius: var(--nurvo-radius-sm);
  font-size: 13px;
  max-width: 200px;
  min-width: 100px;
  text-align: center;
  animation: fadeInUp 0.3s ease;
  z-index: 5;
  box-shadow: var(--nurvo-shadow-sm);
}

.speech-bubble::after {
  content: '';
  position: absolute;
  bottom: -6px;
  left: 50%;
  transform: translateX(-50%);
  width: 0;
  height: 0;
  border-left: 6px solid transparent;
  border-right: 6px solid transparent;
}

.speech-bubble--patient {
  background: var(--nurvo-white);
  color: var(--nurvo-text-primary);
  border: 1px solid var(--nurvo-border);
}

.speech-bubble--patient::after {
  border-top: 6px solid var(--nurvo-white);
}


.speech-bubble p {
  margin: 0;
  line-height: 1.4;
}

@keyframes fadeInUp {
  from { opacity: 0; transform: translateX(-50%) translateY(8px); }
  to { opacity: 1; transform: translateX(-50%) translateY(0); }
}
</style>
