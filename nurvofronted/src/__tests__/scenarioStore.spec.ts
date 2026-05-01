import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useScenarioStore } from '@/stores/scenarioStore'
import { useGameStore } from '@/stores/gameStore'

const apiMocks = vi.hoisted(() => ({
  generateScenario: vi.fn(),
  fetchBackgroundImage: vi.fn(),
}))

vi.mock('@/services/apiService', () => apiMocks)

const scenario = {
  id: 'scenario-1',
  patient_profile: {
    name: '李大華',
    age: 70,
    gender: '男',
    diagnosis: '腰椎間盤突出',
    medications: [],
    medical_history: [],
    allergies: [],
  },
  pain_details: {
    location: '腰部',
    severity: 7,
    type: '刺痛',
    duration: '一天',
    onset: '搬重物後',
    aggravating_factors: [],
    relieving_factors: [],
    associated_symptoms: [],
  },
  family_members: [],
  communication_challenges: [],
  correct_answers: {
    expected_info_gathered: [],
    ideal_empathy_phrases: [],
    ideal_questioning_sequence: [],
    family_calming_strategies: [],
  },
  time_limit_seconds: 480,
  created_at: '2026-05-01T00:00:00Z',
}

describe('scenarioStore', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    apiMocks.generateScenario.mockReset()
    apiMocks.fetchBackgroundImage.mockReset()
  })

  it('keeps polling for a background image after a transient polling error', async () => {
    apiMocks.generateScenario.mockResolvedValue({
      session_id: 'session-1',
      scenario: { ...scenario },
    })
    apiMocks.fetchBackgroundImage
      .mockRejectedValueOnce(new Error('temporary gateway error'))
      .mockResolvedValueOnce({ pending: false, url: 'https://example.test/background.png' })

    const store = useScenarioStore()
    await store.fetchScenario('medium')

    await vi.advanceTimersByTimeAsync(3000)
    await vi.advanceTimersByTimeAsync(3000)

    expect(apiMocks.fetchBackgroundImage).toHaveBeenCalledTimes(2)
    expect(store.scenario?.background_image_url).toBe('https://example.test/background.png')
  })

  it('does not swap in a generated background after the game has started', async () => {
    apiMocks.generateScenario.mockResolvedValue({
      session_id: 'session-1',
      scenario: { ...scenario },
    })
    apiMocks.fetchBackgroundImage.mockResolvedValue({
      pending: false,
      url: 'https://example.test/generated-after-start.png',
    })

    const store = useScenarioStore()
    const gameStore = useGameStore()
    await store.fetchScenario('medium')
    gameStore.setStatus('playing')

    await vi.advanceTimersByTimeAsync(3000)

    expect(store.scenario?.background_image_url).toBeUndefined()
  })

  it('ignores a generated background from a stale session', async () => {
    apiMocks.generateScenario.mockResolvedValue({
      session_id: 'session-1',
      scenario: { ...scenario },
    })
    apiMocks.fetchBackgroundImage.mockResolvedValue({
      pending: false,
      url: 'https://example.test/stale-session.png',
    })

    const store = useScenarioStore()
    const gameStore = useGameStore()
    await store.fetchScenario('medium')
    gameStore.setSessionId('session-2')

    await vi.advanceTimersByTimeAsync(3000)

    expect(store.scenario?.background_image_url).toBeUndefined()
  })
})
