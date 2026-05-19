import { mount } from '@vue/test-utils'
import { nextTick } from 'vue'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import ChatPanel from '@/components/game/ChatPanel.vue'
import { useChatStore } from '@/stores/chatStore'
import { useScenarioStore } from '@/stores/scenarioStore'
import type { Scenario } from '@/types/game'
import { sendMessage } from '@/services/wsService'
import { decodeAndPlay } from '@/services/audioService'

vi.mock('vue-router', () => ({
  useRouter: () => ({ push: vi.fn() }),
}))

vi.mock('@/services/wsService', () => ({
  sendMessage: vi.fn(),
  sendActivity: vi.fn(),
}))

vi.mock('@/services/audioService', () => ({
  decodeAndPlay: vi.fn(),
  unlock: vi.fn(),
  onPlaybackStart: vi.fn(() => vi.fn()),
  onPlaybackEnd: vi.fn(() => vi.fn()),
}))

vi.mock('@/services/speechService', () => ({
  isSupported: () => false,
  start: vi.fn(),
  stop: vi.fn(),
}))

const scenario: Scenario = {
  id: 'scenario-1',
  patient_profile: {
    name: '林女士',
    age: 72,
    gender: '女',
    diagnosis: '術後疼痛',
    medications: [],
    medical_history: [],
    allergies: [],
  },
  pain_details: {
    location: '腹部',
    severity: 7,
    type: '刺痛',
    duration: '2 小時',
    onset: '翻身後',
    aggravating_factors: [],
    relieving_factors: [],
    associated_symptoms: [],
  },
  family_members: [
    {
      name: '林先生',
      gender: '男',
      relationship: '配偶',
      personality: '焦慮',
      emotional_state: '擔心',
      interjection_triggers: ['疼痛'],
    },
    {
      name: '林小姐',
      gender: '女',
      relationship: '女兒',
      personality: '急切',
      emotional_state: '緊張',
      interjection_triggers: ['等待過久'],
    },
    {
      name: '陳小姐',
      gender: '女',
      relationship: '媳婦',
      personality: '謹慎',
      emotional_state: '不安',
      interjection_triggers: ['資訊不清楚'],
    },
  ],
  communication_challenges: [],
  correct_answers: {
    expected_info_gathered: [],
    ideal_empathy_phrases: [],
    ideal_questioning_sequence: [],
    family_calming_strategies: [],
  },
  time_limit_seconds: 480,
  created_at: '2026-04-30T00:00:00.000Z',
}

describe('ChatPanel', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()

    const scenarioStore = useScenarioStore()
    scenarioStore.scenario = scenario

    const chatStore = useChatStore()
    chatStore.setConnected(true)
  })

  it('switches to the clicked family member and sends to that target', async () => {
    const wrapper = mount(ChatPanel)
    const chatStore = useChatStore()

    const tabButtons = wrapper.findAll('button.tab-btn')
    await tabButtons[2]!.trigger('click')

    expect(chatStore.currentTarget).toBe('family_1')
    expect(wrapper.find('textarea').attributes('placeholder')).toBe('輸入訊息給林小姐...')

    await wrapper.find('textarea').setValue('請問現在可以說明一下嗎？')
    await wrapper.find('button.input-btn--send').trigger('click')

    expect(sendMessage).toHaveBeenCalledWith('family_1', '請問現在可以說明一下嗎？')
    const lastMessage = chatStore.messages[chatStore.messages.length - 1]
    expect(lastMessage).toMatchObject({
      sender: 'nurse',
      content: '請問現在可以說明一下嗎？',
    })
  })

  it('auto-plays audio when TTS arrives after the NPC text', async () => {
    mount(ChatPanel)
    const chatStore = useChatStore()

    chatStore.addMessage({
      id: 'npc-1',
      sender: 'patient',
      content: '我這裡很痛',
      timestamp: new Date().toISOString(),
      elapsed_seconds: 3,
      is_interjection: false,
    })
    await nextTick()

    expect(decodeAndPlay).not.toHaveBeenCalled()

    chatStore.messages[0]!.audio_base64 = 'audio'
    await nextTick()

    expect(decodeAndPlay).toHaveBeenCalledWith('audio')
  })

  it('uses family gender for tab and message avatars', async () => {
    const wrapper = mount(ChatPanel)
    const chatStore = useChatStore()
    const maleAvatar = String.fromCodePoint(0x1f468)
    const femaleAvatar = String.fromCodePoint(0x1f469)

    const tabButtons = wrapper.findAll('button.tab-btn')
    expect(tabButtons[1]!.text()).toContain(maleAvatar)
    expect(tabButtons[2]!.text()).toContain(femaleAvatar)

    chatStore.addMessage({
      id: 'family-0-message',
      sender: 'family_0',
      content: '我是林先生',
      timestamp: new Date().toISOString(),
      elapsed_seconds: 5,
      is_interjection: false,
    })
    chatStore.addMessage({
      id: 'family-1-message',
      sender: 'family_1',
      content: '我是林小姐',
      timestamp: new Date().toISOString(),
      elapsed_seconds: 6,
      is_interjection: false,
    })
    await nextTick()

    const messageAvatars = wrapper.findAll('.bubble-row .bubble-avatar').map((avatar) => avatar.text())
    expect(messageAvatars).toContain(maleAvatar)
    expect(messageAvatars).toContain(femaleAvatar)
  })
})
