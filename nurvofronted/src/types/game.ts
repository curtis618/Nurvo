export interface PatientProfile {
  name: string
  age: number
  gender: string
  diagnosis: string
  medications: string[]
  medical_history: string[]
  allergies: string[]
}

export interface PainDetails {
  location: string
  severity: number
  type: string
  duration: string
  onset: string
  aggravating_factors: string[]
  relieving_factors: string[]
  associated_symptoms: string[]
}

export interface FamilyMember {
  name: string
  gender: string
  relationship: string
  personality: string
  emotional_state: string
  interjection_triggers: string[]
}

export interface CorrectAnswers {
  expected_info_gathered: string[]
  ideal_empathy_phrases: string[]
  ideal_questioning_sequence: string[]
  family_calming_strategies: string[]
}

export interface Scenario {
  id: string
  patient_profile: PatientProfile
  pain_details: PainDetails
  family_members: FamilyMember[]
  communication_challenges: string[]
  correct_answers: CorrectAnswers
  time_limit_seconds: number
  created_at: string
  background_image_url?: string | null
}

export type FamilySender = 'family_0' | 'family_1' | 'family_2'

export function isFamilySender(s: string): s is FamilySender {
  return s === 'family_0' || s === 'family_1' || s === 'family_2'
}

export function familyDisplayIndex(s: FamilySender): number {
  const raw = s.split('_')[1]
  const parsed = Number.parseInt(raw ?? '0', 10)
  return Number.isNaN(parsed) ? 0 : parsed
}

export function genderAvatar(gender: string | null | undefined): string {
  const normalized = (gender ?? '').trim().toLowerCase()
  if (['男', '男性', 'male', 'm'].includes(normalized)) return String.fromCodePoint(0x1f468)
  if (['女', '女性', 'female', 'f'].includes(normalized)) return String.fromCodePoint(0x1f469)
  return String.fromCodePoint(0x1f9d1)
}

export interface ChatMessage {
  id: string
  sender: 'patient' | FamilySender | 'nurse'
  content: string
  timestamp: string
  elapsed_seconds: number
  is_interjection: boolean
  is_proactive?: boolean
  audio_base64?: string
}

export interface PatientRecord {
  session_id: string
  content: string
  submitted_at: string
  time_remaining_seconds: number
}

export interface DimensionScores {
  empathy: number
  guided_questioning: number
  family_calming: number
  info_gathering: number
  response_fluency: number
}

export interface KeyMoment {
  elapsed_seconds: number
  message_id: string
  quality: 'good' | 'needs_improvement'
  description: string
}

export interface ScoreResult {
  session_id: string
  overall_score: number
  level_label: string
  dimension_scores: DimensionScores
  strengths: string[]
  improvements: string[]
  key_moments: KeyMoment[]
}

export interface GameSession {
  session_id: string
  scenario: Scenario
  conversation_history: ChatMessage[]
  current_target: 'patient' | FamilySender
  start_time: string
  status: 'briefing' | 'playing' | 'recording' | 'scoring' | 'completed'
}

export type ScenarioDifficulty = 'easy' | 'medium' | 'hard'

export type GameStatus =
  | 'idle'
  | 'generating'
  | 'briefing'
  | 'playing'
  | 'recording'
  | 'scoring'
  | 'completed'
  | 'error'

export interface ScenarioGenerateResponse {
  session_id: string
  scenario: Scenario
}

export interface WsNpcMessage {
  type: 'npc_message'
  sender: 'patient' | FamilySender
  content: string
  audio_base64?: string
  message_id: string
  elapsed_seconds: number
  is_interjection?: boolean
  is_proactive?: boolean
}

export type WsActivityKind =
  | 'typing_start'
  | 'typing_end'
  | 'audio_start'
  | 'audio_end'
  | 'connection_resumed'

export interface WsActivityMessage {
  type: 'activity'
  kind: WsActivityKind
}

export interface WsNpcAudioMessage {
  type: 'npc_audio'
  message_id: string
  audio_base64: string
}

export interface WsTypingMessage {
  type: 'typing'
  sender: 'patient' | FamilySender
}

export interface WsTimerMessage {
  type: 'timer_update'
  remaining_seconds: number
}

export interface WsTimerExpired {
  type: 'timer_expired'
  message: string
}

export interface WsErrorMessage {
  type: 'error'
  message: string
  /** 後端目前固定附帶；未附帶時視為不可重試 */
  retryable?: boolean
}

export type WsServerMessage =
  | WsNpcMessage
  | WsNpcAudioMessage
  | WsTypingMessage
  | WsTimerMessage
  | WsTimerExpired
  | WsErrorMessage

export interface WsNurseMessage {
  type: 'nurse_message'
  target: 'patient' | FamilySender
  content: string
}
