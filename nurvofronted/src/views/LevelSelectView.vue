<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useScenarioStore } from '@/stores/scenarioStore'
import { useGameStore } from '@/stores/gameStore'
import type { ScenarioDifficulty } from '@/types/game'
import NavBar from '@/components/shared/NavBar.vue'

const router = useRouter()
const scenarioStore = useScenarioStore()
const gameStore = useGameStore()

const selectedDifficulty = ref<ScenarioDifficulty>('medium')
const loading = ref(false)
const errorMsg = ref('')

const difficultyOptions: Array<{
  value: ScenarioDifficulty
  title: string
  subtitle: string
  features: string[]
}> = [
  {
    value: 'easy',
    title: '入門',
    subtitle: '適合第一次練習',
    features: ['較長作答時間', '家屬互動干擾較低', '情緒張力較平穩'],
  },
  {
    value: 'medium',
    title: '標準',
    subtitle: '平衡難度與臨床真實性',
    features: ['中等時限壓力', '病患與家屬輪流互動', '需完整疼痛評估流程'],
  },
  {
    value: 'hard',
    title: '進階',
    subtitle: '高壓臨床溝通挑戰',
    features: ['時限更緊湊', '家屬高頻插話與焦慮', '需同步安撫與引導問診'],
  },
]

const selectedOption = computed(() => {
  const matched = difficultyOptions.find((option) => option.value === selectedDifficulty.value)
  return matched ?? difficultyOptions[1]!
})

async function generateAndContinue() {
  if (loading.value) return

  loading.value = true
  errorMsg.value = ''

  try {
    gameStore.reset()
    scenarioStore.reset()
    await scenarioStore.fetchScenario(selectedDifficulty.value) // 傳入選擇的難度參數(目前還沒有實際傳入後端，但前端已經準備好)
    await router.push({ name: 'briefing' })
  } catch (error: any) {
    if (scenarioStore.scenario && gameStore.sessionId) {
      errorMsg.value = '教案已生成，但無法進入任務簡報，請重新整理後再試'
    } else {
      errorMsg.value = error.message || '教案生成失敗，請稍後再試'
    }
  } finally {
    loading.value = false
  }
}

function goBack() {
  router.push('/')
}
</script>

<template>
  <div class="level-page">
    <NavBar />

    <main class="level-container">
      <header class="level-header">
        <h1 class="title">選擇關卡難度</h1>
        <p class="subtitle">系統會依據你選擇的難度，生成對應難度的教案</p>
      </header>

      <section class="difficulty-grid">
        <button
          v-for="option in difficultyOptions"
          :key="option.value"
          class="difficulty-card"
          :class="{ active: selectedDifficulty === option.value }"
          @click="selectedDifficulty = option.value"
        >
          <p class="difficulty-label">{{ option.title }}</p>
          <p class="difficulty-subtitle">{{ option.subtitle }}</p>
          <ul class="difficulty-features">
            <li v-for="feature in option.features" :key="feature">{{ feature }}</li>
          </ul>
        </button>
      </section>

      <section class="preview-card">
        <p class="preview-label">當前選擇</p>
        <h2 class="preview-title">{{ selectedOption.title }} 難度教案</h2>
        <p class="preview-text">{{ selectedOption.subtitle }}</p>
      </section>

      <div v-if="errorMsg" class="error-alert">
        <span class="error-icon">!</span>
        <span>{{ errorMsg }}</span>
      </div>

      <footer class="actions">
        <button class="secondary-btn" @click="goBack" :disabled="loading">返回首頁</button>
        <button class="primary-btn" @click="generateAndContinue" :disabled="loading">
          <span v-if="!loading">生成教案</span>
          <span v-else>生成中...</span>
        </button>
      </footer>
    </main>
  </div>
</template>

<style scoped>
.level-page {
  min-height: 100vh;
  background: radial-gradient(circle at 16% 10%, #dbeafe 0%, transparent 24%), #f8fbff;
}

.level-container {
  max-width: 1020px;
  margin: 0 auto;
  padding: 28px 20px 44px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.level-header {
  text-align: center;
}

.title {
  margin: 0;
  font-size: 36px;
  color: var(--nurvo-text-primary);
}

.subtitle {
  margin: 10px 0 0;
  color: var(--nurvo-text-secondary);
  font-size: 15px;
}

.difficulty-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
}

.difficulty-card {
  border: 1px solid #dbeafe;
  border-radius: 16px;
  padding: 16px;
  background: #ffffff;
  text-align: left;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease;
}

.difficulty-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.12);
}

.difficulty-card.active {
  border-color: #60a5fa;
  background: #eff6ff;
  box-shadow: 0 12px 28px rgba(37, 99, 235, 0.15);
}

.difficulty-label {
  margin: 0;
  font-size: 22px;
  font-weight: 800;
  color: var(--nurvo-text-primary);
}

.difficulty-subtitle {
  margin: 6px 0 10px;
  font-size: 13px;
  color: #475569;
}

.difficulty-features {
  margin: 0;
  padding-left: 18px;
  color: #334155;
  font-size: 13px;
  line-height: 1.6;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.preview-card {
  border: 1px solid #bfdbfe;
  border-radius: 14px;
  background: #f0f9ff;
  padding: 16px;
}

.preview-label {
  margin: 0;
  font-size: 12px;
  color: #0369a1;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.preview-title {
  margin: 6px 0 4px;
  font-size: 24px;
  color: var(--nurvo-text-primary);
}

.preview-text {
  margin: 0;
  color: #334155;
}

.error-alert {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  background: rgba(254, 242, 242, 0.95);
  border: 1px solid var(--nurvo-danger-border);
  border-radius: var(--nurvo-radius-sm);
  color: var(--nurvo-danger-dark);
}

.error-icon {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: var(--nurvo-danger);
  color: var(--nurvo-white);
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
}

.actions {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
}

.secondary-btn,
.primary-btn {
  border: none;
  border-radius: 10px;
  padding: 10px 18px;
  font-weight: 700;
  cursor: pointer;
}

.secondary-btn {
  background: #e2e8f0;
  color: #334155;
}

.primary-btn {
  background: var(--nurvo-gradient-primary);
  color: var(--nurvo-white);
  box-shadow: 0 8px 20px rgba(37, 99, 235, 0.28);
}

.secondary-btn:disabled,
.primary-btn:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

@media (max-width: 900px) {
  .difficulty-grid {
    grid-template-columns: 1fr;
  }

  .actions {
    flex-direction: column;
  }

  .secondary-btn,
  .primary-btn {
    width: 100%;
  }
}
</style>
