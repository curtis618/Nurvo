import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import LevelSelectView from '@/views/LevelSelectView.vue'
import type { Scenario } from '@/types/game'

const routerMock = vi.hoisted(() => ({
  push: vi.fn(),
}))

const apiMocks = vi.hoisted(() => ({
  generateScenario: vi.fn(),
  fetchBackgroundImage: vi.fn(),
}))

vi.mock('vue-router', () => ({
  useRouter: () => routerMock,
}))

vi.mock('@/services/apiService', () => apiMocks)

const scenario: Scenario = {
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

describe('LevelSelectView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useFakeTimers()
    routerMock.push.mockReset()
    apiMocks.generateScenario.mockReset()
    apiMocks.fetchBackgroundImage.mockReset()
    apiMocks.fetchBackgroundImage.mockResolvedValue({ pending: true, url: null })
  })

  it('reports a navigation failure after a scenario has been generated', async () => {
    apiMocks.generateScenario.mockResolvedValue({
      session_id: 'session-1',
      scenario,
    })
    routerMock.push.mockRejectedValue(new Error('navigation failed'))

    const wrapper = mount(LevelSelectView, {
      global: {
        stubs: {
          NavBar: true,
        },
      },
    })

    await wrapper.find('button.primary-btn').trigger('click')
    await flushPromises()

    expect(routerMock.push).toHaveBeenCalledWith({ name: 'briefing' })
    expect(wrapper.find('.error-alert').text()).toContain('教案已生成，但無法進入任務簡報')
  })
})
