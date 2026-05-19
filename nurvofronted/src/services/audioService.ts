/**
 * Audio playback service for TTS audio (base64-encoded).
 * Uses AudioContext for playback. The context is unlocked on the first user
 * gesture via {@link unlock} so that subsequent WebSocket-driven playback
 * is not blocked by Chrome's autoplay policy.
 */

let audioContext: AudioContext | null = null
let currentSource: AudioBufferSourceNode | null = null
let isPlaying = false
let unlocked = false
const queue: string[] = []

type PlaybackListener = () => void
const startListeners = new Set<PlaybackListener>()
const endListeners = new Set<PlaybackListener>()

export function onPlaybackStart(cb: PlaybackListener): () => void {
  startListeners.add(cb)
  return () => startListeners.delete(cb)
}

export function onPlaybackEnd(cb: PlaybackListener): () => void {
  endListeners.add(cb)
  return () => endListeners.delete(cb)
}

function emitStart(): void {
  for (const cb of startListeners) {
    try {
      cb()
    } catch (err) {
      console.error('[audioService] start listener error:', err)
    }
  }
}

function emitEnd(): void {
  for (const cb of endListeners) {
    try {
      cb()
    } catch (err) {
      console.error('[audioService] end listener error:', err)
    }
  }
}

function getAudioContext(): AudioContext {
  if (!audioContext) {
    audioContext = new AudioContext()
  }
  return audioContext
}

/**
 * Call once during a user gesture (click / keydown) to unlock the AudioContext.
 * After this, audio can be played freely from any async callback.
 */
export function unlock(): void {
  if (unlocked) return
  const ctx = getAudioContext()
  if (ctx.state === 'suspended') {
    ctx.resume()
  }
  // Play a silent buffer to fully unlock on iOS / Chrome
  const buf = ctx.createBuffer(1, 1, ctx.sampleRate)
  const src = ctx.createBufferSource()
  src.buffer = buf
  src.connect(ctx.destination)
  src.start(0)
  unlocked = true
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binaryString = atob(base64)
  const bytes = new Uint8Array(binaryString.length)
  for (let i = 0; i < binaryString.length; i++) {
    bytes[i] = binaryString.charCodeAt(i)
  }
  return bytes.buffer
}

async function playBuffer(base64Audio: string): Promise<void> {
  const ctx = getAudioContext()

  if (ctx.state === 'suspended') {
    await ctx.resume()
  }

  const arrayBuffer = base64ToArrayBuffer(base64Audio)
  const audioBuffer = await ctx.decodeAudioData(arrayBuffer)

  return new Promise<void>((resolve) => {
    const source = ctx.createBufferSource()
    source.buffer = audioBuffer
    source.connect(ctx.destination)
    currentSource = source

    source.onended = () => {
      currentSource = null
      resolve()
    }

    source.start(0)
  })
}

async function processQueue(): Promise<void> {
  if (isPlaying) return

  isPlaying = true
  emitStart()
  try {
    while (queue.length > 0) {
      const next = queue.shift()!
      try {
        await playBuffer(next)
      } catch (err) {
        console.error('[audioService] 播放音訊失敗:', err)
      }
    }
  } finally {
    isPlaying = false
    emitEnd()
  }
}

/**
 * Decode base64 audio and play it. If audio is already playing, queue it.
 */
export function decodeAndPlay(base64Audio: string): void {
  if (!base64Audio) return
  queue.push(base64Audio)
  processQueue().catch((err) => {
    console.error('[audioService] processQueue error:', err)
  })
}

/**
 * Stop current playback and clear the queue.
 */
export function stop(): void {
  queue.length = 0
  if (currentSource) {
    try {
      currentSource.stop()
    } catch {
      // already stopped
    }
    currentSource = null
  }
  if (isPlaying) {
    isPlaying = false
    emitEnd()
  }
}
