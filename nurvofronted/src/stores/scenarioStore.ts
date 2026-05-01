import { ref } from 'vue'
import { defineStore } from 'pinia'
import type { Scenario, ScenarioDifficulty } from '@/types/game'
import { generateScenario, fetchBackgroundImage } from '@/services/apiService'
import { useGameStore } from './gameStore'

const BACKGROUND_POLL_ATTEMPTS = 60
const BACKGROUND_POLL_INTERVAL_MS = 3000

export const useScenarioStore = defineStore('scenario', () => {
  const scenario = ref<Scenario | null>(null)
  const loading = ref(false)

  async function pollBackgroundImage(sessionId: string) {
    const gameStore = useGameStore()
    for (let i = 0; i < BACKGROUND_POLL_ATTEMPTS; i++) {
      await new Promise<void>((r) => setTimeout(r, BACKGROUND_POLL_INTERVAL_MS))
      try {
        const { pending, url } = await fetchBackgroundImage(sessionId)
        if (!pending) {
          if (
            url &&
            scenario.value &&
            gameStore.sessionId === sessionId &&
            gameStore.status === 'briefing'
          ) {
            scenario.value.background_image_url = url
          }
          return
        }
      } catch {
        continue
      }
    }
  }

  async function fetchScenario(difficulty: ScenarioDifficulty = 'medium') {
    if (loading.value) return
    const gameStore = useGameStore()
    loading.value = true
    gameStore.setStatus('generating')

    try {
      const response = await generateScenario(difficulty)
      scenario.value = response.scenario
      gameStore.setSessionId(response.session_id)
      gameStore.setStatus('briefing')
      pollBackgroundImage(response.session_id)
    } catch (error: any) {
      gameStore.setError(error.message || '情境生成失敗，請稍後再試')
      throw error
    } finally {
      loading.value = false
    }
  }

  function reset() {
    scenario.value = null
    loading.value = false
  }

  return { scenario, loading, fetchScenario, reset }
})
