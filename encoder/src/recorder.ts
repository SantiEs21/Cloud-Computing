// Frame acquisition + video composition. Source frames (webcam or video file) are drawn on a canvas;
// the canvas is both recorded (captureStream -> MediaRecorder) and hashed, so the stored hashes
// describe exactly the frames that are in the recorded video.
import { hashFrame } from './hash'

export const FPS = 15
export const SEGMENT_MS = 10_000
export const SAMPLE_MS = 500
const MAX_WIDTH = 640

export interface Segment {
  seq: number
  tStartMs: number
  durationMs: number
  blob: Blob
  sha256: string
  mime: string
}

export interface Sample {
  idx: number
  tMs: number
  phash: string
  dhash: string
}

export function pickMime(): string {
  for (const m of ['video/webm;codecs=vp8', 'video/webm', 'video/mp4']) {
    if (MediaRecorder.isTypeSupported(m)) return m
  }
  return ''
}

export async function sha256Hex(blob: Blob): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', await blob.arrayBuffer())
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

export class Recorder {
  frames = 0
  samples = 0
  private ctx: CanvasRenderingContext2D
  private stream: MediaStream
  private current?: MediaRecorder
  private timers: number[] = []
  private seq = 0
  private t0 = performance.now()

  constructor(
    private video: HTMLVideoElement,
    private canvas: HTMLCanvasElement,
    private fileMode: boolean,
    private onSegment: (s: Segment) => void,
    private onSample: (s: Sample) => void,
  ) {
    const scale = Math.min(1, MAX_WIDTH / video.videoWidth)
    canvas.width = Math.round(video.videoWidth * scale)
    canvas.height = Math.round(video.videoHeight * scale)
    this.ctx = canvas.getContext('2d', { willReadFrequently: true })!
    this.stream = canvas.captureStream(FPS)
  }

  /** Position in the trip: video time for a file, elapsed time for the webcam. */
  now(): number {
    return Math.round(this.fileMode ? this.video.currentTime * 1000 : performance.now() - this.t0)
  }

  start() {
    this.draw()
    this.sample() // a sample at t≈0 so the first frame of every video has a stored hash
    this.startSegment()
    this.timers.push(
      window.setInterval(() => this.draw(), 1000 / FPS),
      window.setInterval(() => this.sample(), SAMPLE_MS),
      // A new MediaRecorder every 10 s => every segment is a standalone playable file with its own SHA-256.
      window.setInterval(() => {
        this.current?.stop()
        this.startSegment()
      }, SEGMENT_MS),
    )
  }

  stop() {
    this.timers.forEach(clearInterval)
    this.timers = []
    this.current?.stop() // flushes the last (shorter) segment
    this.current = undefined
    this.stream.getTracks().forEach((t) => t.stop())
  }

  private draw() {
    this.ctx.drawImage(this.video, 0, 0, this.canvas.width, this.canvas.height)
    this.frames++
  }

  private sample() {
    const { width, height } = this.canvas
    const { phash, dhash } = hashFrame(this.ctx.getImageData(0, 0, width, height).data, width, height)
    this.onSample({ idx: this.samples++, tMs: this.now(), phash, dhash })
  }

  private startSegment() {
    const mime = pickMime()
    const rec = new MediaRecorder(this.stream, mime ? { mimeType: mime } : undefined)
    const chunks: Blob[] = []
    const seq = this.seq++
    const tStartMs = this.now()
    const wallStart = performance.now()
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data)
    rec.onstop = async () => {
      const durationMs = Math.round(performance.now() - wallStart)
      const blob = new Blob(chunks, { type: rec.mimeType })
      this.onSegment({ seq, tStartMs, durationMs, blob, sha256: await sha256Hex(blob), mime: rec.mimeType })
    }
    rec.start()
    this.current = rec
  }
}
