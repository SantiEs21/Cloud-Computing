// Encoder page: wires the recorder (frames, segments, hashes) to the offline queue and Supabase.
import { deleteOldSegments, listSegments, openStore, saveSegment } from './db'
import { Queue } from './queue'
import { Recorder, type Sample, type Segment } from './recorder'
import { configured, purgeServer, supabaseSender } from './supabase'

const $ = <T extends HTMLElement = HTMLElement>(id: string) => document.getElementById(id) as T
const video = $<HTMLVideoElement>('video')
const canvas = $<HTMLCanvasElement>('canvas')
const offlineBox = $<HTMLInputElement>('offline')

const RETRY_MS = 3000
const CLEANUP_MS = 60_000

const db = await openStore()
const queue = new Queue(db, supabaseSender)
let recorder: Recorder | undefined
let tripId = ''
let startedAt = 0
let segmentUrls: string[] = []

if (!configured) $('config').textContent = 'Missing VITE_SUPABASE_URL / VITE_SUPABASE_ANON_KEY in encoder/.env'

async function start() {
  const driver = $<HTMLInputElement>('driver').value.trim()
  if (!driver) return alert('Enter a driver ID')
  const fileMode = (document.querySelector('input[name=source]:checked') as HTMLInputElement).value === 'file'

  if (fileMode) {
    const file = $<HTMLInputElement>('file').files?.[0]
    if (!file) return alert('Choose a video file')
    video.srcObject = null
    video.src = URL.createObjectURL(file)
    video.onended = stop // the trip ends with the file
  } else {
    video.removeAttribute('src')
    video.srcObject = await navigator.mediaDevices.getUserMedia({ video: { width: 1280, height: 720 }, audio: false })
  }
  await video.play()

  tripId = crypto.randomUUID()
  startedAt = Date.now()
  await queue.add('trips', { id: tripId, driver_id: driver, started_at: new Date(startedAt).toISOString() })

  recorder = new Recorder(video, canvas, fileMode, onSegment, onSample)
  recorder.start()
  $<HTMLButtonElement>('start').disabled = true
  $<HTMLButtonElement>('stop').disabled = false
}

function stop() {
  if (!recorder) return
  recorder.stop()
  recorder = undefined
  video.pause()
  if (video.srcObject) (video.srcObject as MediaStream).getTracks().forEach((t) => t.stop()) // camera off
  $<HTMLButtonElement>('start').disabled = false
  $<HTMLButtonElement>('stop').disabled = true
  queue.flush()
}

// Hash rows are queued (IndexedDB) first; the retry loop sends them.
async function onSample(s: Sample) {
  await queue.add('fingerprints', { trip_id: tripId, sample_idx: s.idx, t_ms: s.tMs, phash: s.phash, dhash: s.dhash })
}

async function onSegment(s: Segment) {
  const trip = tripId
  await saveSegment(db, { id: `${trip}:${s.seq}`, trip_id: trip, seq: s.seq, createdAt: Date.now(), sha256: s.sha256, mime: s.mime, blob: s.blob })
  await queue.add('segments', {
    trip_id: trip, seq: s.seq, t_start_ms: s.tStartMs, duration_ms: s.durationMs, sha256: s.sha256, size_bytes: s.blob.size,
  })
  renderSegments()
}

async function renderSegments() {
  segmentUrls.forEach(URL.revokeObjectURL)
  segmentUrls = []
  const list = (await listSegments(db)).sort((a, b) => b.createdAt - a.createdAt)
  $('segments').innerHTML = ''
  for (const s of list) {
    const url = URL.createObjectURL(s.blob)
    segmentUrls.push(url)
    const ext = s.mime.includes('mp4') ? 'mp4' : 'webm'
    const li = document.createElement('li')
    li.innerHTML = `trip ${s.trip_id.slice(0, 8)} · segment ${s.seq} · ${(s.blob.size / 1024).toFixed(0)} KB ·
      ${new Date(s.createdAt).toLocaleTimeString()} · <a href="${url}" download="trip-${s.trip_id.slice(0, 8)}-seg${s.seq}.${ext}">Download</a>`
    $('segments').append(li)
  }
}

// Deletion of expired data: local segments every minute, and server rows via purge_expired().
async function cleanup() {
  const local = await deleteOldSegments(db, Number($<HTMLInputElement>('localMin').value) * 60_000)
  let server = 'skipped (offline)'
  if (queue.isOnline() && configured) {
    try {
      const r = await purgeServer(Number($<HTMLInputElement>('serverH').value))
      server = `${r.fingerprints} fingerprints, ${r.segments} segments, ${r.trips} trips`
    } catch (e) {
      server = `error: ${e instanceof Error ? e.message : e}`
    }
  }
  $('cleanup').textContent = `${new Date().toLocaleTimeString()} — local: ${local} segments, server: ${server}`
  if (local) renderSegments()
}

async function renderStatus() {
  $('trip').textContent = tripId || '-'
  $('time').textContent = recorder ? `${Math.round((Date.now() - startedAt) / 1000)} s` : $('time').textContent
  $('frames').textContent = String(recorder?.frames ?? $('frames').textContent)
  $('hashes').textContent = String(recorder?.samples ?? $('hashes').textContent)
  $('sent').textContent = String(queue.sent)
  $('pending').textContent = String(await queue.pending())
  $('net').textContent = queue.simulateOffline ? 'offline (simulated)' : navigator.onLine ? 'online' : 'offline'
  $('latency').textContent = queue.lastLatencyMs === null ? '-' : `${queue.lastLatencyMs} ms`
  $('error').textContent = queue.lastError
}

$('start').onclick = () => start().catch((e) => alert(`Could not start: ${e.message ?? e}`))
$('stop').onclick = stop
offlineBox.onchange = () => {
  queue.simulateOffline = offlineBox.checked
  queue.flush()
}
window.addEventListener('online', () => queue.flush())
setInterval(() => queue.flush(), RETRY_MS) // retry loop: also sends rows left from a previous session
setInterval(cleanup, CLEANUP_MS)
setInterval(renderStatus, 500)
renderSegments()
queue.flush()
