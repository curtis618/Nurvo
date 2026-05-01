import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'

import SceneFallback2D from '@/components/game/SceneFallback2D.vue'
import type { FamilyMember } from '@/types/game'

const familyMembers: FamilyMember[] = [
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
]

describe('SceneFallback2D', () => {
  it('emits the correct target when patient and family characters are clicked', async () => {
    const wrapper = mount(SceneFallback2D, {
      props: {
        patientName: '林女士',
        familyMembers,
      },
    })

    await wrapper.find('.character.patient').trigger('click')
    await wrapper.findAll('.character.family')[1]!.trigger('click')

    expect(wrapper.emitted('select-target')).toEqual([['patient'], ['family_1']])
  })

  it('emits the correct target from top bubble buttons', async () => {
    const wrapper = mount(SceneFallback2D, {
      props: {
        patientName: '林女士',
        familyMembers,
      },
    })

    await wrapper.findAll('button.top-bubble')[3]!.trigger('click')

    expect(wrapper.emitted('select-target')).toEqual([['family_2']])
  })

  it('shows the full latest NPC message in the scene dialog', () => {
    const content =
      '我是王雅君，林志明的妻子。我很擔心他現在的狀況，他一直在說疼痛，真的讓我很不安。你能告訴我們，他的情況有改善嗎？藥物有在起作用嗎？'

    const wrapper = mount(SceneFallback2D, {
      props: {
        patientName: '林志明',
        familyMembers: [
          ...familyMembers.slice(0, 2),
          {
            ...familyMembers[2]!,
            name: '王雅君',
            relationship: '妻子',
          },
        ],
        latestMessage: {
          id: 'message-1',
          sender: 'family_2',
          content,
          timestamp: '2026-05-01T00:00:00Z',
          elapsed_seconds: 0,
          is_interjection: false,
        },
      },
    })

    expect(wrapper.find('.bottom-dialog__content').text()).toBe(content)
  })
})
