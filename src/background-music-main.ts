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
const SCAN_HEIGHTS_STORAGE_KEY = 'bgmusic:scan-heights'
// Default and bounds for the HI/LO scanline trace heights, in CSS pixels of
// vertical deflection from the scanline's midline.
const SCAN_DEFAULT_HEIGHT_PX = 24
const SCAN_MIN_HEIGHT_PX = 6
const SCAN_EDGE_MARGIN_PX = 6  // keep a handle this far from the canvas edge
const PARTIAL = [' ', '\u2581', '\u2582', '\u2583', '\u2584', '\u2585', '\u2586', '\u2587']
const FULL = '\u2588'
const SMOOTHING_RISE = 0.6
const SMOOTHING_FALL = 0.88
// Per-bar spectral normalization. Each bar tracks its own long-term average
// and is divided by it, so all bars settle near a common target height. This
// flattens the natural pink-noise tilt of music while leaving instantaneous
// dynamics (kicks, drops, transients) intact.
const SPECTRAL_NORM_SMOOTHING = 0.995  // ~3 sec adaptation at 60 fps
const SPECTRAL_NORM_TARGET = 0.35      // long-term average bar height
const SPECTRAL_NORM_FLOOR = 0.06       // divisor floor; prevents amplifying silence
const SPECTRAL_NORM_MAX_GAIN = 4       // hard cap on amplification of quiet bars
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
let spectralAvg = new Float32Array(BARS).fill(SPECTRAL_NORM_TARGET)
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
const bandsEl = document.getElementById('bands') as HTMLDivElement
const scanHiHandleEl = document.getElementById('scanline-handle-hi') as HTMLDivElement
const scanLoHandleEl = document.getElementById('scanline-handle-lo') as HTMLDivElement
const scanRowsHandleEl = document.getElementById('scanline-handle-rows') as HTMLDivElement
const statusLine1El = document.getElementById('status-line1')!
const statusProgressEl = document.getElementById('status-progress') as HTMLSpanElement
const statusProgressTextEl = document.getElementById('status-progress-text')!
const statusTimesEl = document.getElementById('status-times')!
const statusLine3El = document.getElementById('status-line3')!
const hintEl = document.getElementById('hint')!
const trackSelect = document.getElementById('track') as HTMLSelectElement
const scanCanvas = document.getElementById('scanline') as HTMLCanvasElement
const scanCtx = scanCanvas.getContext('2d')!

const STATUS_BAR_WIDTH = 38

let scrubPointerId: number | null = null

const SCRUB_KEY_STEP_SEC = 5

function buildProgressBarText(ratio: number): string {
  const r = Math.min(1, Math.max(0, ratio))
  const pos = Math.round(r * (STATUS_BAR_WIDTH - 1))
  let bar = ''
  for (let i = 0; i < STATUS_BAR_WIDTH; i++) {
    if (i === pos) bar += '\u25C6'
    else if (i < pos) bar += '\u2501'
    else bar += '\u2500'
  }
  return bar
}

function scrubDuration(): number | null {
  if (!audio) return null
  const d = audio.duration
  return Number.isFinite(d) && d > 0 ? d : null
}

function scrubRatioFromClientX(clientX: number): number {
  const rect = statusProgressEl.getBoundingClientRect()
  if (rect.width <= 0) return 0
  return Math.min(1, Math.max(0, (clientX - rect.left) / rect.width))
}

function seekToRatio(ratio: number) {
  const d = scrubDuration()
  if (d == null || !audio) return
  audio.currentTime = ratio * d
}

function updateProgressAria(ratio: number) {
  const d = scrubDuration()
  const cur = d != null ? ratio * d : 0
  statusProgressEl.setAttribute('aria-valuenow', String(Math.round(ratio * 100)))
  statusProgressEl.setAttribute(
    'aria-valuetext',
    d != null ? `${mmss(cur)} / ${mmss(d)}` : 'loading',
  )
}

function resetVizState() {
  smoothed = new Float32Array(BARS).fill(0)
  spectralAvg = new Float32Array(BARS).fill(SPECTRAL_NORM_TARGET)
  smoothedFloor = 0
  waveHead = 0
  waveBuffer.fill(0)
  scanX = 0
  scanFrameCounter = 0
  scanHiAmps.length = 0
  scanLoAmps.length = 0
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
  statusProgressEl.tabIndex = 0
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

  for (let i = 0; i < BARS; i++) {
    const h = heights[i]!
    spectralAvg[i] =
      spectralAvg[i]! * SPECTRAL_NORM_SMOOTHING + h * (1 - SPECTRAL_NORM_SMOOTHING)
    const divisor = Math.max(SPECTRAL_NORM_FLOOR, spectralAvg[i]!)
    const gain = Math.min(SPECTRAL_NORM_MAX_GAIN, SPECTRAL_NORM_TARGET / divisor)
    heights[i] = Math.min(1, h * gain)
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

// Fraction of bars (from the bottom) counted as the LO band; the rest is HI.
// 0.75 → LO covers ~40 Hz – 3.5 kHz, HI covers ~3.5 kHz – 16 kHz (the split
// is logarithmic because BIN_MAP is). Used by both the LO/HI bands meter
// and the scanline traces so they stay in sync.
const LO_BAND_FRACTION = 0.75

function getBandAverages(): { lo: number; hi: number } {
  const split = Math.max(1, Math.min(BARS - 1, Math.round(BARS * LO_BAND_FRACTION)))
  let loSum = 0
  let hiSum = 0
  for (let i = 0; i < split; i++) loSum += smoothed[i]!
  for (let i = split; i < BARS; i++) hiSum += smoothed[i]!
  return { lo: loSum / split, hi: hiSum / (BARS - split) }
}

const BAND_LABEL_W = 3   // visual width of "LO " / "HI "
const BAND_GAP_W = 2     // gap between the two meters
const BAND_EMPTY = '\u2591'

function renderBands() {
  if (BARS < 2) return ''
  const { lo, hi } = getBandAverages()
  const bandW = Math.max(1, Math.floor((BARS - 2 * BAND_LABEL_W - BAND_GAP_W) / 2))
  const fill = (v: number) => {
    const filled = Math.round(Math.min(1, Math.max(0, v)) * bandW)
    return FULL.repeat(filled) + BAND_EMPTY.repeat(bandW - filled)
  }

  return (
    `<span class="dim">LO </span><span class="cyan">${fill(lo)}</span>` +
    '  ' +
    `<span class="dim">HI </span><span class="cyan">${fill(hi)}</span>`
  )
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

function updateStatus() {
  if (!audio || !currentTrack) return

  const cur = audio.currentTime || 0
  const durRaw = audio.duration
  const durOk = Number.isFinite(durRaw) && durRaw > 0
  const pct = durOk ? cur / durRaw : 0

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

  statusLine1El.innerHTML = `<span class="ok">${icon}</span> ${currentTrack.title}${artistLine ? ` <span class="faint">\u2014</span> ${artistLine}` : ''}`

  if (scrubPointerId === null) {
    statusProgressTextEl.textContent = buildProgressBarText(pct)
    updateProgressAria(pct)
  }

  statusTimesEl.textContent = ` ${mmss(cur)} / ${mmss(durOk ? durRaw : 0)}`

  statusLine3El.innerHTML = `  <span class="dim">${state}</span>  <span class="dim">vol</span> <span class="cyan">${volViz}</span> <span class="dim">${vol}%${muteLabel}</span>  <span class="dim">viz:</span> <span class="faint">${VIZ_MODES[vizMode]}</span>`
}

// --- scanning line ---
// Two stacked traces sharing a horizontal midline: HI band deflects upward,
// LO band deflects downward. Each trace's max deflection (in pixels) is set
// by a draggable handle on the right edge of the canvas. Bars are stepped
// into discrete row segments to match the blocky look of the spectrum viz,
// and each bar is exactly one viz column (charWidth) wide so they align.
const SCAN_BAR_COLOR = '#78dce8'  // matches --cyan
// One new bar every N animation frames. With charWidth ≈ 8 px and 60 fps,
// N = 4 gives ~2 px / frame perceived scroll speed (same feel as before
// the bar width was matched to the viz columns).
const SCAN_FRAMES_PER_SAMPLE = 4
// Visual gaps. The column footprint (colW) still matches one viz character so
// scanline bars line up with the spectrum bars below.
const SCAN_BAR_GAP_RATIO = 0.25         // 25% of colW becomes empty space
const SCAN_MIDLINE_GAP_PX = 4           // total gutter between HI (above) and LO (below)
const scanColW = () => Math.max(1, Math.round(charWidth))
const scanBarW = () => Math.max(1, Math.round(scanColW() * (1 - SCAN_BAR_GAP_RATIO)))
let scanFrameCounter = 0
const SCAN_ROW_GAP = 1            // px gap between row segments
const SCAN_ROW_HEIGHT_DEFAULT = 6
const SCAN_ROW_HEIGHT_MIN = 2
const SCAN_ROW_HEIGHT_MAX = 14
let scanRowHeightPx = SCAN_ROW_HEIGHT_DEFAULT
let scanX = 0
const scanHiAmps: number[] = []
const scanLoAmps: number[] = []
let scanHiHeightPx = SCAN_DEFAULT_HEIGHT_PX
let scanLoHeightPx = SCAN_DEFAULT_HEIGHT_PX

function scanMaxHeight(): number {
  const h = scanCanvas.parentElement!.getBoundingClientRect().height
  return Math.max(
    SCAN_MIN_HEIGHT_PX,
    h / 2 - SCAN_EDGE_MARGIN_PX - SCAN_MIDLINE_GAP_PX / 2,
  )
}

function positionScanHandles() {
  const h = scanCanvas.parentElement!.getBoundingClientRect().height
  const midY = h / 2
  const halfGap = SCAN_MIDLINE_GAP_PX / 2
  scanHiHandleEl.style.top = `${midY - halfGap - scanHiHeightPx}px`
  scanLoHandleEl.style.top = `${midY + halfGap + scanLoHeightPx}px`
  scanRowsHandleEl.style.top = `${midY}px`
}

function setScanHi(px: number) {
  scanHiHeightPx = Math.max(SCAN_MIN_HEIGHT_PX, Math.min(scanMaxHeight(), px))
  positionScanHandles()
}

function setScanLo(px: number) {
  scanLoHeightPx = Math.max(SCAN_MIN_HEIGHT_PX, Math.min(scanMaxHeight(), px))
  positionScanHandles()
}

function setScanRowHeight(px: number) {
  scanRowHeightPx = Math.max(
    SCAN_ROW_HEIGHT_MIN,
    Math.min(SCAN_ROW_HEIGHT_MAX, Math.round(px)),
  )
}

function loadScanHeights() {
  try {
    const raw = localStorage.getItem(SCAN_HEIGHTS_STORAGE_KEY)
    if (!raw) return
    const obj = JSON.parse(raw) as { hi?: number; lo?: number; rows?: number }
    if (typeof obj.hi === 'number') scanHiHeightPx = obj.hi
    if (typeof obj.lo === 'number') scanLoHeightPx = obj.lo
    if (typeof obj.rows === 'number') scanRowHeightPx = obj.rows
  } catch {
    // ignore (private mode / quota / corrupt value)
  }
}

function persistScanHeights() {
  try {
    localStorage.setItem(
      SCAN_HEIGHTS_STORAGE_KEY,
      JSON.stringify({
        hi: scanHiHeightPx,
        lo: scanLoHeightPx,
        rows: scanRowHeightPx,
      }),
    )
  } catch {
    // ignore
  }
}

function resizeScanCanvas() {
  const rect = scanCanvas.parentElement!.getBoundingClientRect()
  scanCanvas.width = rect.width * devicePixelRatio
  scanCanvas.height = rect.height * devicePixelRatio
  scanCtx.setTransform(devicePixelRatio, 0, 0, devicePixelRatio, 0, 0)
  scanX = 0
  scanHiAmps.length = 0
  scanLoAmps.length = 0
  // re-clamp to the new available height before repositioning the handles
  setScanHi(scanHiHeightPx)
  setScanLo(scanLoHeightPx)
}
loadScanHeights()
resizeScanCanvas()
window.addEventListener('resize', resizeScanCanvas)

function drawScanline() {
  const w = scanCanvas.width / devicePixelRatio
  const h = scanCanvas.height / devicePixelRatio
  const midY = h / 2
  const colW = scanColW()
  const barW = scanBarW()
  const halfGap = SCAN_MIDLINE_GAP_PX / 2
  const hiBaseY = midY - halfGap   // bottom edge of HI bars
  const loBaseY = midY + halfGap   // top edge of LO bars

  scanFrameCounter++
  if (scanFrameCounter >= SCAN_FRAMES_PER_SAMPLE) {
    scanFrameCounter = 0
    const { lo, hi } = getBandAverages()
    scanHiAmps.push(hi)
    scanLoAmps.push(lo)
    scanX += colW

    if (scanX >= w) {
      scanX = 0
      scanHiAmps.length = 0
      scanLoAmps.length = 0
    }
  }

  scanCtx.clearRect(0, 0, w, h)

  scanCtx.strokeStyle = 'rgba(196, 233, 243, 0.12)'
  scanCtx.lineWidth = 1
  scanCtx.beginPath()
  scanCtx.moveTo(0, midY)
  scanCtx.lineTo(w, midY)
  scanCtx.stroke()

  if (scanHiAmps.length < 1) return

  // Bars made of discrete row segments to match the spectrum viz look. Each
  // column is colW (one viz character) wide; height is quantized into row
  // segments of scanRowHeightPx separated by SCAN_ROW_GAP. HI grows up from
  // the midline, LO grows down. The rightmost segment stack is the current
  // value (the "tip" of the trace).
  const rowH = scanRowHeightPx
  const STEP = rowH + SCAN_ROW_GAP

  scanCtx.fillStyle = SCAN_BAR_COLOR
  for (let i = 0; i < scanHiAmps.length; i++) {
    const x = i * colW
    const target = Math.min(1, scanHiAmps[i]!) * scanHiHeightPx
    const rows = Math.floor(target / STEP)
    for (let r = 0; r < rows; r++) {
      scanCtx.fillRect(x, hiBaseY - (r + 1) * STEP + SCAN_ROW_GAP, barW, rowH)
    }
    const rem = target - rows * STEP
    if (rem > SCAN_ROW_GAP) {
      const partial = rem - SCAN_ROW_GAP
      scanCtx.fillRect(x, hiBaseY - rows * STEP - partial, barW, partial)
    }
  }
  for (let i = 0; i < scanLoAmps.length; i++) {
    const x = i * colW
    const target = Math.min(1, scanLoAmps[i]!) * scanLoHeightPx
    const rows = Math.floor(target / STEP)
    for (let r = 0; r < rows; r++) {
      scanCtx.fillRect(x, loBaseY + r * STEP, barW, rowH)
    }
    const rem = target - rows * STEP
    if (rem > SCAN_ROW_GAP) {
      const partial = rem - SCAN_ROW_GAP
      scanCtx.fillRect(x, loBaseY + rows * STEP, barW, partial)
    }
  }
}

type ScanHandleAxis = 'y-up' | 'y-down' | 'x-right'

function attachScanHandle(
  el: HTMLElement,
  read: () => number,
  write: (px: number) => void,
  axis: ScanHandleAxis,
) {
  let dragId: number | null = null
  let startX = 0
  let startY = 0
  let startVal = 0
  el.addEventListener('pointerdown', (e) => {
    dragId = e.pointerId
    startX = e.clientX
    startY = e.clientY
    startVal = read()
    el.setPointerCapture(e.pointerId)
    el.classList.add('scanline__handle--active')
    e.preventDefault()
  })
  el.addEventListener('pointermove', (e) => {
    if (dragId !== e.pointerId) return
    let delta: number
    switch (axis) {
      case 'y-up':    delta = startY - e.clientY; break
      case 'y-down':  delta = e.clientY - startY; break
      case 'x-right': delta = e.clientX - startX; break
    }
    write(startVal + delta)
  })
  const end = (e: PointerEvent) => {
    if (dragId !== e.pointerId) return
    dragId = null
    el.classList.remove('scanline__handle--active')
    try {
      el.releasePointerCapture(e.pointerId)
    } catch {
      // pointer may already be released
    }
    persistScanHeights()
  }
  el.addEventListener('pointerup', end)
  el.addEventListener('pointercancel', end)
}

attachScanHandle(scanHiHandleEl, () => scanHiHeightPx, setScanHi, 'y-up')
attachScanHandle(scanLoHandleEl, () => scanLoHeightPx, setScanLo, 'y-down')
attachScanHandle(scanRowsHandleEl, () => scanRowHeightPx, setScanRowHeight, 'x-right')

function tick() {
  if (!started) return

  // Spectrum data feeds both the main viz (in spectrum mode) and the lo/hi
  // band meters (in any mode), so always compute it.
  const raw = getBarHeights()
  smooth(raw)

  const mode = VIZ_MODES[vizMode]
  let rows: string[]
  if (mode === 'spectrum') {
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
  bandsEl.innerHTML = renderBands()
  updateStatus()

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

function applyVizWidth(bars: number) {
  const w = `${bars * charWidth}px`
  vizBoxEl.style.width = w
  bandsEl.style.width = w
}

function setBars(nextBars: number) {
  const clamped = Math.max(MIN_BARS, Math.min(MAX_BARS, Math.floor(nextBars)))
  if (clamped === BARS) {
    applyVizWidth(clamped)
    return
  }

  smoothed = resampleFloat32(smoothed, clamped)
  spectralAvg = resampleFloat32(spectralAvg, clamped)
  BARS = clamped
  WAVE_COLS = clamped
  BIN_MAP = buildBinMap()
  applyVizWidth(clamped)
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

statusProgressEl.addEventListener('pointerdown', (e) => {
  if (!started || !audio || e.button !== 0) return
  if (scrubDuration() == null) return
  e.preventDefault()
  scrubPointerId = e.pointerId
  statusProgressEl.setPointerCapture(e.pointerId)
  statusProgressEl.classList.add('status__progress--dragging')
  const ratio = scrubRatioFromClientX(e.clientX)
  seekToRatio(ratio)
  statusProgressTextEl.textContent = buildProgressBarText(ratio)
  updateProgressAria(ratio)
})

statusProgressEl.addEventListener('pointermove', (e) => {
  if (scrubPointerId !== e.pointerId) return
  const ratio = scrubRatioFromClientX(e.clientX)
  seekToRatio(ratio)
  statusProgressTextEl.textContent = buildProgressBarText(ratio)
  updateProgressAria(ratio)
})

function endScrubPointer(e: PointerEvent) {
  if (scrubPointerId !== e.pointerId) return
  scrubPointerId = null
  statusProgressEl.classList.remove('status__progress--dragging')
  try {
    statusProgressEl.releasePointerCapture(e.pointerId)
  } catch {
    // pointer may already be released
  }
}

statusProgressEl.addEventListener('pointerup', endScrubPointer)
statusProgressEl.addEventListener('pointercancel', endScrubPointer)

statusProgressEl.addEventListener('keydown', (e) => {
  if (!started || !audio) return
  const d = scrubDuration()
  if (d == null) return

  let handled = false
  if (e.key === 'ArrowLeft' || e.key === 'ArrowDown') {
    audio.currentTime = Math.max(0, audio.currentTime - SCRUB_KEY_STEP_SEC)
    handled = true
  } else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') {
    audio.currentTime = Math.min(d, audio.currentTime + SCRUB_KEY_STEP_SEC)
    handled = true
  } else if (e.key === 'Home') {
    audio.currentTime = 0
    handled = true
  } else if (e.key === 'End') {
    audio.currentTime = d
    handled = true
  }

  if (!handled) return
  e.preventDefault()
  e.stopPropagation()
  const ratio = audio.currentTime / d
  statusProgressTextEl.textContent = buildProgressBarText(ratio)
  updateProgressAria(ratio)
})

window.addEventListener('resize', () => {
  charWidth = measureCharWidth()
  const cap = maxBarsForViewport()
  if (BARS > cap) setBars(cap)
  else applyVizWidth(BARS)
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
