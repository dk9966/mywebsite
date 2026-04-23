const mp3Urls = import.meta.glob('../assets/**/*.mp3', {
  eager: true,
  query: '?url',
  import: 'default',
}) as Record<string, string>

type Track = {
  path: string
  src: string
  label: string
  title: string
  artist: string
  album: string
}

const TRACK_META: Record<
  string,
  { title: string; artist: string; album?: string }
> = {
  'End of Line (Remixed by Photek).mp3': {
    title: 'End of Line (Remixed by Photek)',
    artist: 'Daft Punk',
    album: 'TRON: Legacy Reconfigured',
  },
}

function buildTracks(): Track[] {
  return Object.entries(mp3Urls)
    .map(([path, src]) => {
      const file = path.slice(path.lastIndexOf('/') + 1)
      const meta = TRACK_META[file]
      const stem = file.replace(/\.mp3$/i, '')
      return {
        path,
        src,
        label: meta?.title ?? stem,
        title: meta?.title ?? stem,
        artist: meta?.artist ?? '',
        album: meta?.album ?? '',
      }
    })
    .sort((a, b) => a.label.localeCompare(b.label))
}

const TRACKS = buildTracks()

const VIZ_ROWS = 16
const DEFAULT_BARS = 64
const MIN_BARS = 16
const MAX_BARS = 512
const MAX_WAVE_COLS = 1024
const VIZ_WIDTH_STORAGE_KEY = 'bgmusic:viz-bars'
const PARTIAL = [' ', '\u2581', '\u2582', '\u2583', '\u2584', '\u2585', '\u2586', '\u2587']
const FULL = '\u2588'
const SMOOTHING_RISE = 0.6
const SMOOTHING_FALL = 0.88
const VOL_STEP = 0.05
const VIZ_MODES = ['spectrum', 'wave'] as const
let vizMode = 0

let BARS = DEFAULT_BARS
let WAVE_COLS = DEFAULT_BARS

const mmss = (s: number) => {
  const m = Math.floor(s / 60)
  const r = Math.floor(s % 60)
  return `${m}:${String(r).padStart(2, '0')}`
}

function analyserByteBuffer(length: number): Uint8Array<ArrayBuffer> {
  const buf = new ArrayBuffer(length)
  return new Uint8Array(buf) as Uint8Array<ArrayBuffer>
}

let audioCtx: AudioContext | null = null
let analyser: AnalyserNode | null = null
let audio: HTMLAudioElement | null = null
let freqData: Uint8Array<ArrayBuffer> | null = null
let smoothed = new Float32Array(BARS).fill(0)
let smoothedFloor = 0
let started = false
let muted = false
let savedVolume = 0.6
let currentTrack: Track | null = null

const SAMPLES_PER_FRAME = 3
const waveBuffer = new Float32Array(MAX_WAVE_COLS).fill(0)
let waveHead = 0

const vizEl = document.getElementById('viz')!
const vizBoxEl = document.getElementById('viz-box') as HTMLDivElement
const vizHandleEl = document.getElementById('viz-handle') as HTMLDivElement
const statusEl = document.getElementById('status')!
const hintEl = document.getElementById('hint')!
const trackSelect = document.getElementById('track') as HTMLSelectElement
const scanCanvas = document.getElementById('scanline') as HTMLCanvasElement
const scanCtx = scanCanvas.getContext('2d')!

function resetVizState() {
  smoothed = new Float32Array(BARS).fill(0)
  smoothedFloor = 0
  waveHead = 0
  waveBuffer.fill(0)
  scanX = 0
  scanAmps.length = 0
}

function resampleFloat32(
  src: Float32Array,
  dstLen: number,
): Float32Array<ArrayBuffer> {
  const dst = new Float32Array(dstLen)
  if (dstLen <= 0 || src.length === 0) return dst
  if (src.length === dstLen) {
    dst.set(src)
    return dst
  }
  if (src.length === 1) {
    dst.fill(src[0]!)
    return dst
  }
  const denom = dstLen === 1 ? 1 : dstLen - 1
  for (let i = 0; i < dstLen; i++) {
    const t = (i / denom) * (src.length - 1)
    const lo = Math.floor(t)
    const hi = Math.min(src.length - 1, lo + 1)
    const f = t - lo
    dst[i] = src[lo]! * (1 - f) + src[hi]! * f
  }
  return dst
}

function populateTrackSelect() {
  trackSelect.innerHTML = ''
  if (TRACKS.length === 0) {
    const opt = document.createElement('option')
    opt.value = ''
    opt.textContent = 'No MP3 files in assets/'
    trackSelect.append(opt)
    trackSelect.disabled = true
    return
  }
  trackSelect.disabled = false
  for (let i = 0; i < TRACKS.length; i++) {
    const opt = document.createElement('option')
    opt.value = String(i)
    opt.textContent = TRACKS[i].label
    trackSelect.append(opt)
  }
}

function getSelectedTrack(): Track | null {
  const idx = Number.parseInt(trackSelect.value, 10)
  if (Number.isNaN(idx) || idx < 0 || idx >= TRACKS.length) return TRACKS[0] ?? null
  return TRACKS[idx]
}

function initAudio() {
  if (started) return
  currentTrack = getSelectedTrack()
  if (!currentTrack) return

  started = true
  hintEl.classList.add('hint--hidden')

  audioCtx = new AudioContext()
  analyser = audioCtx.createAnalyser()
  analyser.fftSize = 2048
  analyser.smoothingTimeConstant = 0.3

  audio = new Audio(currentTrack.src)
  audio.crossOrigin = 'anonymous'
  audio.loop = true
  audio.volume = savedVolume

  const mediaSource = audioCtx.createMediaElementSource(audio)
  mediaSource.connect(analyser)
  analyser.connect(audioCtx.destination)

  freqData = analyserByteBuffer(analyser.frequencyBinCount)

  void audio.play()
  requestAnimationFrame(tick)
}

function switchTrack() {
  const next = getSelectedTrack()
  if (!next || !audio || !started) return
  if (currentTrack && next.path === currentTrack.path) return

  currentTrack = next
  audio.pause()
  audio.src = next.src
  audio.load()
  resetVizState()
  void audio.play()
}

// --- frequency bin → bar mapping (logarithmic) ---
function buildBinMap() {
  const binCount = 1024
  const minFreq = 40
  const maxFreq = 16000
  const sampleRate = 44100
  const freqPerBin = sampleRate / 2 / binCount
  const logMin = Math.log(minFreq)
  const logMax = Math.log(maxFreq)
  const map: [number, number][] = []
  for (let i = 0; i < BARS; i++) {
    const logLow = logMin + (i / BARS) * (logMax - logMin)
    const logHigh = logMin + ((i + 1) / BARS) * (logMax - logMin)
    const binLow = Math.max(0, Math.floor(Math.exp(logLow) / freqPerBin))
    const binHigh = Math.min(binCount - 1, Math.floor(Math.exp(logHigh) / freqPerBin))
    map.push([binLow, binHigh])
  }
  return map
}
let BIN_MAP: [number, number][] = buildBinMap()

function getBarHeights() {
  if (!analyser || !freqData) return new Float32Array(BARS)
  analyser.getByteFrequencyData(freqData)
  const heights = new Float32Array(BARS)
  for (let i = 0; i < BARS; i++) {
    const [lo, hi] = BIN_MAP[i]!
    let sum = 0
    let count = 0
    for (let b = lo; b <= hi; b++) {
      sum += freqData[b]!
      count++
    }
    const avg = count > 0 ? sum / count : 0
    heights[i] = avg / 255
  }

  const sorted = Float32Array.from(heights).sort()
  const rawFloor = sorted[Math.floor(BARS * 0.15)]!
  smoothedFloor += (rawFloor - smoothedFloor) * 0.15

  const range = 1 - smoothedFloor
  if (range > 0.01) {
    for (let i = 0; i < BARS; i++) {
      heights[i] = Math.max(0, (heights[i]! - smoothedFloor) / range)
    }
  }

  return heights
}

function smooth(raw: Float32Array) {
  for (let i = 0; i < BARS; i++) {
    if (raw[i]! > smoothed[i]!) {
      smoothed[i] = smoothed[i]! * SMOOTHING_RISE + raw[i]! * (1 - SMOOTHING_RISE)
    } else {
      smoothed[i] = smoothed[i]! * SMOOTHING_FALL + raw[i]! * (1 - SMOOTHING_FALL)
    }
    if (smoothed[i]! < 0.005) smoothed[i] = 0
  }
}

function renderBars() {
  const totalLevels = VIZ_ROWS * 8
  const levels = Array.from(smoothed, (h) => Math.round(h * totalLevels))
  const rows: string[] = []
  for (let r = 0; r < VIZ_ROWS; r++) {
    const fromBottom = VIZ_ROWS - 1 - r
    const rowStart = fromBottom * 8
    let row = ''
    for (let i = 0; i < BARS; i++) {
      const lvl = levels[i]!
      if (lvl >= rowStart + 8) row += FULL
      else if (lvl <= rowStart) row += ' '
      else row += PARTIAL[lvl - rowStart]!
    }
    rows.push(row)
  }
  return rows
}

// --- scrolling waveform mode ---
let timeData: Uint8Array<ArrayBuffer> | null = null

function sampleWaveform() {
  if (!analyser) return
  if (!timeData) timeData = analyserByteBuffer(analyser.fftSize)
  analyser.getByteTimeDomainData(timeData)
  const vol = audio ? audio.volume : 1
  const boost = vol > 0.01 ? 1 / vol : 1
  const len = timeData.length
  const step = Math.floor(len / SAMPLES_PER_FRAME)
  for (let s = 0; s < SAMPLES_PER_FRAME; s++) {
    const from = s * step
    const to = Math.min(from + step, len)
    let peak = 0
    for (let i = from; i < to; i++) {
      const v = Math.abs(timeData[i]! - 128) / 128
      if (v > peak) peak = v
    }
    const scaled = Math.pow(peak * boost, 0.55) * 1.6
    waveBuffer[waveHead] = Math.min(1, scaled)
    waveHead = (waveHead + 1) % MAX_WAVE_COLS
  }
}

function renderWave() {
  const totalLevels = VIZ_ROWS * 8
  const rows: string[] = []
  const readStart = (waveHead - WAVE_COLS + MAX_WAVE_COLS) % MAX_WAVE_COLS
  for (let r = 0; r < VIZ_ROWS; r++) {
    const fromBottom = VIZ_ROWS - 1 - r
    const rowStart = fromBottom * 8
    let row = ''
    for (let col = 0; col < WAVE_COLS; col++) {
      const idx = (readStart + col) % MAX_WAVE_COLS
      const lvl = Math.round(waveBuffer[idx]! * totalLevels)
      if (lvl >= rowStart + 8) row += FULL
      else if (lvl <= rowStart) row += ' '
      else row += PARTIAL[lvl - rowStart]!
    }
    rows.push(row)
  }
  let baseline = ''
  for (let col = 0; col < WAVE_COLS; col++) {
    baseline += '\u2500'
  }
  rows.push(baseline)
  return rows
}

function renderStatus() {
  if (!audio || !currentTrack) return ''
  const cur = audio.currentTime || 0
  const dur = audio.duration || 1
  const pct = cur / dur
  const barW = 38
  const pos = Math.round(pct * (barW - 1))
  let bar = ''
  for (let i = 0; i < barW; i++) {
    if (i === pos) bar += '\u25C6'
    else if (i < pos) bar += '\u2501'
    else bar += '\u2500'
  }

  const vol = Math.round(audio.volume * 100)
  const volBar = Math.round(audio.volume * 10)
  const volViz = '\u2588'.repeat(volBar) + '\u2591'.repeat(10 - volBar)
  const paused = audio.paused
  const icon = paused ? '\u23F8' : '\u25B6'
  const state = paused ? 'paused ' : 'playing'
  const muteLabel = muted ? ' [muted]' : ''

  const artistLine = currentTrack.artist
    ? `<span class="dim">${currentTrack.artist}</span>`
    : ''

  const lines = [
    `<span class="ok">${icon}</span> ${currentTrack.title}${artistLine ? ` <span class="faint">\u2014</span> ${artistLine}` : ''}`,
    `  <span class="cyan">${bar}</span> <span class="dim">${mmss(cur)} / ${mmss(dur)}</span>`,
    `  <span class="dim">${state}</span>  <span class="dim">vol</span> <span class="cyan">${volViz}</span> <span class="dim">${vol}%${muteLabel}</span>  <span class="dim">viz:</span> <span class="faint">${VIZ_MODES[vizMode]}</span>`,
  ]
  return lines.join('\n')
}

// --- scanning line ---
const SCAN_SPEED = 2
let scanX = 0
const scanAmps: number[] = []

function resizeScanCanvas() {
  const rect = scanCanvas.parentElement!.getBoundingClientRect()
  scanCanvas.width = rect.width * devicePixelRatio
  scanCanvas.height = rect.height * devicePixelRatio
  scanCtx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0)
  scanX = 0
  scanAmps.length = 0
}
resizeScanCanvas()
window.addEventListener('resize', resizeScanCanvas)

function getInstantAmplitude() {
  if (!analyser) return 0
  if (!timeData) timeData = analyserByteBuffer(analyser.fftSize)
  analyser.getByteTimeDomainData(timeData)
  let peak = 0
  for (let i = 0; i < timeData.length; i++) {
    const v = Math.abs(timeData[i]! - 128) / 128
    if (v > peak) peak = v
  }
  const vol = audio ? audio.volume : 1
  const boost = vol > 0.01 ? 1 / vol : 1
  return Math.min(1, Math.pow(peak * boost, 0.55) * 1.6)
}

function drawScanline() {
  const w = scanCanvas.width / devicePixelRatio
  const h = scanCanvas.height / devicePixelRatio
  const midY = h / 2

  const amp = getInstantAmplitude()
  scanAmps.push(amp)
  scanX += SCAN_SPEED

  if (scanX >= w) {
    scanX = 0
    scanAmps.length = 0
  }

  scanCtx.clearRect(0, 0, w, h)

  scanCtx.strokeStyle = 'rgba(196, 233, 243, 0.12)'
  scanCtx.lineWidth = 1
  scanCtx.beginPath()
  scanCtx.moveTo(0, midY)
  scanCtx.lineTo(w, midY)
  scanCtx.stroke()

  if (scanAmps.length < 2) return

  scanCtx.strokeStyle = '#fff'
  scanCtx.lineWidth = 1.5
  scanCtx.lineJoin = 'round'
  scanCtx.beginPath()
  for (let i = 0; i < scanAmps.length; i++) {
    const x = i * SCAN_SPEED
    const y = midY
    if (i === 0) scanCtx.moveTo(x, y)
    else scanCtx.lineTo(x, y)
  }
  scanCtx.stroke()
}

function tick() {
  if (!started) return

  const mode = VIZ_MODES[vizMode]
  let rows: string[]
  if (mode === 'spectrum') {
    const raw = getBarHeights()
    smooth(raw)
    rows = renderBars()
  } else {
    sampleWaveform()
    rows = renderWave()
  }

  const last = rows.length - 1
  vizEl.innerHTML = rows
    .map((r, i) => {
      if (mode === 'wave' && i === last) {
        return `<span class="faint">${r}</span>`
      }
      return `<span class="cyan">${r}</span>`
    })
    .join('\n')
  statusEl.innerHTML = renderStatus()

  drawScanline()

  requestAnimationFrame(tick)
}

function setVolume(v: number) {
  if (!audio) return
  const clamped = Math.max(0, Math.min(1, v))
  audio.volume = clamped
  savedVolume = clamped
  if (clamped > 0 && muted) muted = false
}

// --- resizable width ---
let charWidth = 8

function measureCharWidth(): number {
  const probe = document.createElement('span')
  probe.style.cssText =
    'position:absolute;visibility:hidden;white-space:pre;pointer-events:none;'
  probe.textContent = 'M'.repeat(100)
  vizBoxEl.append(probe)
  const w = probe.getBoundingClientRect().width / 100
  probe.remove()
  return w > 0 ? w : 8
}

function maxBarsForViewport(): number {
  const parent = vizBoxEl.parentElement
  if (!parent) return MAX_BARS
  const avail = parent.getBoundingClientRect().width
  return Math.max(MIN_BARS, Math.min(MAX_BARS, Math.floor(avail / charWidth)))
}

function setBars(nextBars: number) {
  const clamped = Math.max(MIN_BARS, Math.min(MAX_BARS, Math.floor(nextBars)))
  if (clamped === BARS) {
    vizBoxEl.style.width = `${clamped * charWidth}px`
    return
  }

  smoothed = resampleFloat32(smoothed, clamped)
  BARS = clamped
  WAVE_COLS = clamped
  BIN_MAP = buildBinMap()
  vizBoxEl.style.width = `${clamped * charWidth}px`
}

function loadStoredBars(): number {
  try {
    const raw = localStorage.getItem(VIZ_WIDTH_STORAGE_KEY)
    if (!raw) return DEFAULT_BARS
    const n = Number.parseInt(raw, 10)
    if (!Number.isFinite(n)) return DEFAULT_BARS
    return n
  } catch {
    return DEFAULT_BARS
  }
}

function persistBars(bars: number) {
  try {
    localStorage.setItem(VIZ_WIDTH_STORAGE_KEY, String(bars))
  } catch {
    // ignore (private mode / quota)
  }
}

function initViz() {
  charWidth = measureCharWidth()
  const stored = loadStoredBars()
  const capped = Math.min(stored, maxBarsForViewport())
  setBars(capped)
}
initViz()

let dragPointerId: number | null = null
let dragStartX = 0
let dragStartBars = 0

vizHandleEl.addEventListener('pointerdown', (e) => {
  dragPointerId = e.pointerId
  dragStartX = e.clientX
  dragStartBars = BARS
  vizHandleEl.setPointerCapture(e.pointerId)
  vizHandleEl.classList.add('viz__handle--active')
  e.preventDefault()
})

vizHandleEl.addEventListener('pointermove', (e) => {
  if (dragPointerId !== e.pointerId) return
  const deltaBars = Math.round((e.clientX - dragStartX) / charWidth)
  const cap = maxBarsForViewport()
  const next = Math.max(MIN_BARS, Math.min(cap, dragStartBars + deltaBars))
  setBars(next)
})

function endDrag(e: PointerEvent) {
  if (dragPointerId !== e.pointerId) return
  dragPointerId = null
  vizHandleEl.classList.remove('viz__handle--active')
  try {
    vizHandleEl.releasePointerCapture(e.pointerId)
  } catch {
    // pointer may already be released
  }
  persistBars(BARS)
}

vizHandleEl.addEventListener('pointerup', endDrag)
vizHandleEl.addEventListener('pointercancel', endDrag)

window.addEventListener('resize', () => {
  charWidth = measureCharWidth()
  const cap = maxBarsForViewport()
  if (BARS > cap) setBars(cap)
  else vizBoxEl.style.width = `${BARS * charWidth}px`
})

populateTrackSelect()

trackSelect.addEventListener('change', () => {
  if (!started) return
  switchTrack()
})

document.addEventListener('keydown', (e) => {
  if (!started) {
    initAudio()
    return
  }

  switch (e.key) {
    case ' ':
      e.preventDefault()
      if (audio!.paused) {
        void audio!.play()
      } else {
        audio!.pause()
      }
      break
    case 'm':
    case 'M':
      e.preventDefault()
      if (muted) {
        audio!.volume = savedVolume
        muted = false
      } else {
        savedVolume = audio!.volume || savedVolume
        audio!.volume = 0
        muted = true
      }
      break
    case 'ArrowUp':
      e.preventDefault()
      if (muted) {
        muted = false
        audio!.volume = savedVolume
      }
      setVolume(audio!.volume + VOL_STEP)
      break
    case 'ArrowDown':
      e.preventDefault()
      setVolume(audio!.volume - VOL_STEP)
      break
    case 'v':
    case 'V':
      e.preventDefault()
      vizMode = (vizMode + 1) % VIZ_MODES.length
      break
  }
})

hintEl.addEventListener('click', initAudio)
