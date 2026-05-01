import type { ScenarioDifficulty, ScenarioGenerateResponse, ScoreResult } from '@/types/game'

const API_BASE = '/api'
const MAX_RETRIES = 2
const RETRY_DELAY_MS = 2000
const USE_MOCK_API = import.meta.env.DEV && import.meta.env.VITE_USE_MOCK_API === 'true'

function randomId(prefix: string): string {
  if (typeof crypto !== 'undefined' && 'randomUUID' in crypto) {
    return `${prefix}-${crypto.randomUUID()}`
  }
  return `${prefix}-${Date.now()}-${Math.floor(Math.random() * 100000)}`
}

function createMockScenarioResponse(difficulty: ScenarioDifficulty = 'medium'): ScenarioGenerateResponse {
  const now = new Date().toISOString()
  const severityMap: Record<ScenarioDifficulty, number> = {
    easy: 4,
    medium: 7,
    hard: 9,
  }
  const timeLimitMap: Record<ScenarioDifficulty, number> = {
    easy: 600,
    medium: 480,
    hard: 360,
  }
  const challengeMap: Record<ScenarioDifficulty, string[]> = {
    easy: ['病患疼痛敘述不完整', '需以同理開場並逐步提問'],
    medium: ['病患疼痛敘述不完整', '家屬容易打斷', '需同理並引導重點'],
    hard: ['病患情緒波動明顯', '家屬高焦慮且頻繁打斷', '需同時完成安撫、評估與衛教'],
  }

  return {
    session_id: randomId('mock-session'),
    scenario: {
      id: randomId('mock-scenario'),
      patient_profile: {
        name: '王阿明',
        age: 67,
        gender: '男',
        diagnosis: '術後傷口疼痛',
        medications: ['止痛藥 PRN', '抗生素'],
        medical_history: ['高血壓', '第二型糖尿病'],
        allergies: ['無已知藥物過敏'],
      },
      pain_details: {
        location: '右下腹手術傷口',
        severity: severityMap[difficulty],
        type: '刺痛',
        duration: '約 2 小時',
        onset: '翻身後加劇',
        aggravating_factors: ['翻身', '咳嗽'],
        relieving_factors: ['平躺休息'],
        associated_symptoms: ['焦慮', '冒冷汗'],
      },
      family_members: [
        {
          name: '王太太',
          gender: '女',
          relationship: '配偶',
          personality: '焦慮、保護性高',
          emotional_state: '擔心手術後恢復狀況',
          interjection_triggers: ['疼痛惡化', '等待過久', '資訊不清楚'],
        },
        {
          name: '王先生',
          gender: '男',
          relationship: '兒子',
          personality: '理性但急切',
          emotional_state: '擔心疼痛是否代表併發症',
          interjection_triggers: ['手術風險', '藥物副作用', '病況變化'],
        },
        {
          name: '林小姐',
          gender: '女',
          relationship: '女兒',
          personality: '細心、容易追問細節',
          emotional_state: '不安且想確認後續照護',
          interjection_triggers: ['照護計畫不清楚', '出院安排', '疼痛控制'],
        },
      ],
      communication_challenges: challengeMap[difficulty],
      correct_answers: {
        expected_info_gathered: ['疼痛位置', '疼痛程度', '疼痛誘發因子', '緩解方式'],
        ideal_empathy_phrases: ['我理解您現在很不舒服', '謝謝您願意告訴我感受'],
        ideal_questioning_sequence: ['先同理', '再問疼痛細節', '確認變化與影響'],
        family_calming_strategies: ['先回應家屬擔憂', '提供清楚下一步處置'],
      },
      time_limit_seconds: timeLimitMap[difficulty],
      created_at: now,
    },
  }
}

function createMockScoreResult(sessionId: string): ScoreResult {
  return {
    session_id: sessionId,
    overall_score: 82,
    level_label: '良好',
    dimension_scores: {
      empathy: 84,
      guided_questioning: 80,
      family_calming: 78,
      info_gathering: 85,
      response_fluency: 81,
    },
    strengths: ['能先同理病患不適', '有主動釐清疼痛位置與程度', '語句清楚、節奏穩定'],
    improvements: ['可更早安撫家屬情緒', '可補問疼痛持續時間與緩解因子'],
    key_moments: [
      {
        elapsed_seconds: 34,
        message_id: 'mock-msg-1',
        quality: 'good',
        description: '第一時間先同理病患情緒，建立信任。',
      },
      {
        elapsed_seconds: 96,
        message_id: 'mock-msg-2',
        quality: 'needs_improvement',
        description: '家屬焦慮升高時，可先短句安撫再繼續提問。',
      },
    ],
  }
}

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

function getErrorMessage(status: number): string {
  switch (status) {
    case 400:
      return '請求格式錯誤，請檢查輸入內容'
    case 401:
    case 403:
      return '認證失敗，請重新登入'
    case 404:
      return '找不到請求的資源'
    case 408:
      return '請求逾時，請稍後再試'
    case 429:
      return '請求過於頻繁，請稍後再試'
    case 500:
      return '伺服器內部錯誤，請稍後再試'
    case 502:
      return '服務暫時無法使用，請稍後再試'
    case 503:
      return '伺服器維護中，請稍後再試'
    case 504:
      return '伺服器回應逾時，請稍後再試'
    default:
      return `請求失敗（${status}），請稍後再試`
  }
}

function isRetryable(status: number): boolean {
  return status === 503 || status === 502 || status === 504 || status === 408 || status === 429
}

async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  let lastError: Error | null = null

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 30000)

      const response = await fetch(`${API_BASE}${url}`, {
        headers: { 'Content-Type': 'application/json', ...options.headers },
        ...options,
        signal: controller.signal,
      })

      clearTimeout(timeoutId)

      if (!response.ok) {
        const shouldRetry = isRetryable(response.status) && attempt < MAX_RETRIES

        if (shouldRetry) {
          lastError = new Error(getErrorMessage(response.status))
          await delay(RETRY_DELAY_MS)
          continue
        }

        // Try to get server error message, fall back to localized message
        const errorBody = await response.json().catch(() => null)
        const message = errorBody?.detail || errorBody?.message || getErrorMessage(response.status)
        throw new Error(message)
      }

      return response.json()
    } catch (err: any) {
      if (err.name === 'AbortError') {
        lastError = new Error('請求逾時，請檢查網路連線後再試')
      } else if (err instanceof TypeError && err.message.includes('fetch')) {
        lastError = new Error('無法連線至伺服器，請檢查網路連線')
      } else if (err instanceof Error) {
        lastError = err
      } else {
        lastError = new Error('發生未知錯誤，請稍後再試')
      }

      // Only retry on network-level errors, not on thrown HTTP errors
      if (attempt < MAX_RETRIES && (err.name === 'AbortError' || (err instanceof TypeError && err.message.includes('fetch')))) {
        await delay(RETRY_DELAY_MS)
        continue
      }

      throw lastError
    }
  }

  throw lastError || new Error('請求失敗，請稍後再試')
}

export async function generateScenario(
  difficulty: ScenarioDifficulty = 'medium',
): Promise<ScenarioGenerateResponse> {
  if (USE_MOCK_API) {
    return createMockScenarioResponse(difficulty)
  }
  return request<ScenarioGenerateResponse>('/scenario/generate', {
    method: 'POST',
    body: JSON.stringify({ difficulty }),
  })
}

export async function submitRecord(
  sessionId: string,
  content: string,
): Promise<{ status: string; session_id: string }> {
  if (USE_MOCK_API) {
    return { status: 'ok', session_id: sessionId }
  }
  return request('/record/submit', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId, content }),
  })
}

export async function transcribeAudio(audioBlob: Blob): Promise<string> {
  const formData = new FormData()
  formData.append('file', audioBlob, 'audio.webm')

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 30000)

  const response = await fetch(`${API_BASE}/stt/transcribe`, {
    method: 'POST',
    body: formData,
    signal: controller.signal,
  })

  clearTimeout(timeoutId)

  if (!response.ok) {
    const errorBody = await response.json().catch(() => null)
    throw new Error(errorBody?.detail || '語音辨識失敗')
  }

  const data = await response.json()
  return data.text || ''
}

export async function fetchBackgroundImage(
  sessionId: string,
): Promise<{ pending: boolean; url: string | null }> {
  const data = await request<{ status: string; url: string | null }>(
    `/scenario/${sessionId}/background`,
  )
  return { pending: data.status === 'pending', url: data.url }
}

export async function evaluateScore(sessionId: string): Promise<ScoreResult> {
  if (USE_MOCK_API) {
    return createMockScoreResult(sessionId)
  }
  return request<ScoreResult>('/score/evaluate', {
    method: 'POST',
    body: JSON.stringify({ session_id: sessionId }),
  })
}
