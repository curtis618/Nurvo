<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useScenarioStore } from '@/stores/scenarioStore'
import { useGameStore } from '@/stores/gameStore'
import NavBar from '@/components/shared/NavBar.vue'
import PatientCard from '@/components/game/PatientCard.vue'
import { unlock as unlockAudio } from '@/services/audioService'

const router = useRouter()
const scenarioStore = useScenarioStore()
const gameStore = useGameStore()

const timeLimit = computed<number>(() => {
  if (!scenarioStore.scenario) return 0
  return Math.floor(scenarioStore.scenario.time_limit_seconds / 60)
})

const painSeverity = computed<number | undefined>(() => {
  return scenarioStore.scenario?.pain_details?.severity
})

type FamilyCardDisplay = {
  name: string
  relationship: string
  personality: string
  emotional_state: string
  interjection_triggers: string[]
}

const familyMembers = computed<FamilyCardDisplay[]>(() => {
  if (!scenarioStore.scenario) return []

  const scenarioWithList = scenarioStore.scenario as typeof scenarioStore.scenario & {
    family_members?: FamilyCardDisplay[]
    family_member_1?: FamilyCardDisplay
    family_member_2?: FamilyCardDisplay
    family_member_3?: FamilyCardDisplay
  }

  const normalizeMember = (member?: Partial<FamilyCardDisplay>): FamilyCardDisplay => ({
    name: member?.name ?? '未知家屬',
    relationship: member?.relationship ?? '家屬',
    personality: member?.personality ?? '未提供',
    emotional_state: member?.emotional_state ?? '未提供',
    interjection_triggers: Array.isArray(member?.interjection_triggers)
      ? member!.interjection_triggers
      : [],
  })

  const numberedMembers = [
    scenarioWithList.family_member_1,
    scenarioWithList.family_member_2,
    scenarioWithList.family_member_3,
  ].filter(Boolean) as FamilyCardDisplay[]

  if (numberedMembers.length > 0) {
    return numberedMembers.slice(0, 3).map(normalizeMember)
  }

  if (Array.isArray(scenarioWithList.family_members) && scenarioWithList.family_members.length > 0) {
    return scenarioWithList.family_members.slice(0, 3).map(normalizeMember)
  }

  return []
})

onMounted(() => {
  if (!scenarioStore.scenario) {
    console.warn('[BriefingView] No scenario data found, redirecting to home')
    router.replace('/')
  }
})

function enterScene(): void {
  unlockAudio()
  gameStore.setStatus('playing')
  router.push('/scene')
}
</script>

<template>
  <div class="briefing-page" v-if="scenarioStore.scenario">
    <div class="bg-glow bg-glow--left"></div>
    <div class="bg-glow bg-glow--right"></div>

    <NavBar />

    <main class="briefing-shell">
      <section class="briefing-glass">
        <header class="briefing-header">
          <p class="briefing-eyebrow">Clinical Scenario Briefing</p>
          <h1 class="briefing-title">任務簡報</h1>
        </header>

        <div class="two-col-row">
          <div class="info-card goals-card">
            <div class="goals-title">&#x1F3AF; 溝通挑戰</div>
            <ul class="goals-list">
              <!-- <li
                v-for="challenge in scenarioStore.scenario.communication_challenges"
                :key="challenge"
              >{{ challenge }}</li> -->
              <p>1. 透過與病患或病患家屬溝通獲得特定資訊</p>
              <p>2. 透過溝通技巧安撫病患或家屬的情緒</p>
            </ul>
          </div>
        </div>

        <div class="patient-card-wrap">
          <PatientCard
            :patient="scenarioStore.scenario.patient_profile"
            :pain-severity="painSeverity"
          />
        </div>

        <div class="family-row">
          <div
            v-for="(fm, idx) in familyMembers"
            :key="`${fm.name}-${idx}`"
            class="info-card family-card"
          >
            <div class="info-card-header">
              <div class="family-avatar">&#x1F464;</div>
              <div class="family-name-block">
                <span class="family-name">{{ fm.name }}</span>
                <span class="family-rel">{{ fm.relationship }}</span>
              </div>
            </div>
            <div class="family-tags">
              <span class="ftag">{{ fm.personality }}</span>
              <span class="ftag">{{ fm.emotional_state }}</span>
              <span class="ftag">易插話：{{ fm.interjection_triggers?.[0] || '無' }}</span>
            </div>
          </div>
        </div>



        <div class="action-bar">
          <div class="time-info">
            <span class="time-icon">&#x23F1;</span>
            <span class="time-text">限時 {{ timeLimit }} 分鐘</span>
          </div>
          <button class="cta-button" @click="enterScene">
            進入場景 <span class="cta-arrow">&rarr;</span>
          </button>
        </div>
      </section>
    </main>
  </div>
</template>

<style scoped>
.briefing-page {
  min-height: 100vh;
  position: relative;
  overflow: hidden;
  background:
    radial-gradient(circle at 16% 12%, #dbeafe 0%, transparent 30%),
    radial-gradient(circle at 84% 10%, #e0f2fe 0%, transparent 34%),
    #f8fbff;
}

.bg-glow {
  position: absolute;
  border-radius: 50%;
  filter: blur(56px);
  pointer-events: none;
  opacity: 0.38;
}

.bg-glow--left {
  width: 300px;
  height: 300px;
  left: -96px;
  top: 110px;
  background: #60a5fa;
}

.bg-glow--right {
  width: 340px;
  height: 340px;
  right: -130px;
  top: 86px;
  background: #7dd3fc;
}

.briefing-shell {
  position: relative;
  z-index: 1;
  max-width: 1120px;
  margin: 28px auto 0;
  padding: 0 20px 44px;
}

.briefing-glass {
  max-width: 900px;
  margin: 0 auto;
  border-radius: 26px;
  border: 1px solid rgba(219, 234, 254, 0.9);
  background: rgba(255, 255, 255, 0.62);
  backdrop-filter: blur(16px);
  box-shadow: 0 24px 54px rgba(15, 23, 42, 0.14);
  padding: 30px;
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.briefing-header {
  text-align: center;
  margin-bottom: 2px;
}

.briefing-eyebrow {
  margin: 0 0 10px;
  font-size: 12px;
  font-weight: 700;
  letter-spacing: 0.11em;
  text-transform: uppercase;
  color: var(--nurvo-primary-dark);
}

.briefing-title {
  font-size: clamp(32px, 4.6vw, 42px);
  font-weight: 800;
  letter-spacing: -0.03em;
  color: var(--nurvo-text-primary);
  margin: 0;
}

.briefing-subtitle {
  margin: 10px 0 0;
  font-size: 15px;
  color: #475569;
}

.patient-card-wrap {
  border-radius: 18px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  background: rgba(255, 255, 255, 0.7);
  padding: 10px;
}

.family-row {
  display: flex;
  gap: 14px;
}

.two-col-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 14px;
  width: 100%;
  margin: 0; /* remove extra padding so it aligns with other sections */
}

/* Make goals card span full width */
.two-col-row > .info-card.goals-card {
  grid-column: 1 / -1;
  align-items: center;
  text-align: center;
}

.info-card {
  flex: 1;
  border: 1px solid rgba(203, 213, 225, 0.9);
  border-radius: 16px;
  padding: 16px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.family-card {
  background: linear-gradient(145deg, rgba(255, 244, 231, 0.86), rgba(255, 255, 255, 0.9));
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.info-card-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.family-avatar {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: linear-gradient(135deg, var(--nurvo-family), var(--nurvo-family-dark));
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 15px;
  flex-shrink: 0;
}

.family-name-block {
  display: flex;
  flex-direction: column;
  gap: 1px;
}

.family-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--nurvo-text-primary);
  line-height: 1.3;
}

.family-rel {
  font-size: 14px;
  color: var(--nurvo-family-text);
  line-height: 1.3;
}

.family-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.ftag {
  display: inline-block;
  font-size: 13px;
  font-weight: 500;
  padding: 4px 10px;
  border-radius: 999px;
  background: var(--nurvo-warning-bg);
  color: var(--nurvo-warning-darker);
  border: 1px solid var(--nurvo-warning-border);
  line-height: 1.5;
}

.goals-card {
  background: rgba(255, 255, 255, 0.88);
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.goals-title {
  font-size: 18px;
  font-weight: 700;
  color: var(--nurvo-text-primary);
}

.goals-list {
  margin: 0;
  padding-left: 0; /* remove left padding for centered alignment */
  display: flex;
  flex-direction: column;
  gap: 6px;
  align-items: center;
}

.goals-list li {
  font-size: 14px;
  color: var(--nurvo-text-secondary);
  line-height: 1.5;
}

.action-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: rgba(241, 245, 249, 0.82);
  border: 1px solid rgba(203, 213, 225, 0.85);
  border-radius: 14px;
  padding: 14px 20px;
  margin-top: 4px;
}

.time-info {
  display: flex;
  align-items: center;
  gap: 6px;
}

.time-icon {
  font-size: 18px;
}

.time-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--nurvo-text-secondary);
}

.cta-button {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: var(--nurvo-gradient-primary);
  color: var(--nurvo-white);
  border: none;
  border-radius: 10px;
  padding: 10px 24px;
  font-size: 16px;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 10px 24px rgba(37, 99, 235, 0.28);
  transition: transform 0.2s ease, box-shadow 0.2s ease, opacity 0.2s ease;
}

.cta-button:hover {
  opacity: 0.96;
  transform: translateY(-2px);
  box-shadow: 0 14px 30px rgba(37, 99, 235, 0.34);
}

.cta-button:active {
  transform: translateY(0);
}

.cta-arrow {
  font-size: 16px;
}

@media (max-width: 860px) {
  .briefing-glass {
    padding: 24px;
  }

  .two-col-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 540px) {
  .briefing-shell {
    margin-top: 18px;
    padding: 0 14px 30px;
  }

  .briefing-glass {
    padding: 18px;
    border-radius: 20px;
  }

  .briefing-title {
    font-size: 30px;
  }

  .briefing-subtitle {
    font-size: 14px;
  }

  .family-row {
    flex-direction: column;
  }

  .action-bar {
    flex-direction: column;
    gap: 12px;
    align-items: stretch;
    text-align: center;
  }

  .time-info {
    justify-content: center;
  }
}
</style>
