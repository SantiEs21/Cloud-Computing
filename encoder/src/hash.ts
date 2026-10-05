// Perceptual hashes of a frame. Same algorithm as decoder/fingerprint.py so browser hashes can be
// compared with hashes computed in Python from a video file. Pure functions on RGBA pixels, so the
// exact code that runs in the browser is also what the Vitest parity test runs in Node.

/** RGBA bytes (canvas ImageData layout) -> float grayscale. */
export function toGray(rgba: Uint8ClampedArray | Uint8Array, w: number, h: number): Float64Array {
  const g = new Float64Array(w * h)
  for (let i = 0; i < w * h; i++) {
    g[i] = 0.299 * rgba[i * 4] + 0.587 * rgba[i * 4 + 1] + 0.114 * rgba[i * 4 + 2]
  }
  return g
}

/** For each output index, the source pixels it covers and how much (area weights, like cv2 INTER_AREA). */
function areaWeights(src: number, dst: number): { idx: number; w: number }[][] {
  const scale = src / dst
  const out: { idx: number; w: number }[][] = []
  for (let o = 0; o < dst; o++) {
    const start = o * scale
    const end = start + scale
    const list: { idx: number; w: number }[] = []
    for (let s = Math.floor(start); s < Math.ceil(end - 1e-9); s++) {
      const overlap = Math.min(end, s + 1) - Math.max(start, s)
      if (overlap > 1e-9) list.push({ idx: s, w: overlap / scale })
    }
    out.push(list)
  }
  return out
}

/** Downscale a grayscale image by area averaging (each output pixel = mean of the area it covers). */
export function resizeArea(g: Float64Array, w: number, h: number, nw: number, nh: number): Float64Array {
  const wx = areaWeights(w, nw)
  const wy = areaWeights(h, nh)
  const out = new Float64Array(nw * nh)
  for (let oy = 0; oy < nh; oy++) {
    for (let ox = 0; ox < nw; ox++) {
      let sum = 0
      for (const y of wy[oy]) for (const x of wx[ox]) sum += g[y.idx * w + x.idx] * y.w * x.w
      out[oy * nw + ox] = sum
    }
  }
  return out
}

export function gray32(rgba: Uint8ClampedArray | Uint8Array, w: number, h: number): Float64Array {
  return resizeArea(toGray(rgba, w, h), w, h, 32, 32)
}

/** 64 booleans (row-major, MSB first) -> 16 hex chars. */
function bitsToHex(bits: boolean[]): string {
  let hex = ''
  for (let i = 0; i < bits.length; i += 4) {
    let nibble = 0
    for (let j = 0; j < 4; j++) nibble = (nibble << 1) | (bits[i + j] ? 1 : 0)
    hex += nibble.toString(16)
  }
  return hex
}

// Orthonormal DCT-II matrix (same scaling as cv2.dct, which matters for the median split).
const N = 32
const C: number[][] = Array.from({ length: N }, (_, k) =>
  Array.from({ length: N }, (_, n) =>
    (k === 0 ? Math.sqrt(1 / N) : Math.sqrt(2 / N)) * Math.cos((Math.PI * (2 * n + 1) * k) / (2 * N)),
  ),
)

/** pHash: 2-D DCT of the 32x32 image, keep the low-frequency 8x8 corner, bit = value > median. */
export function phashFromGray32(g: Float64Array): string {
  const low: number[] = []
  // Only the 8x8 corner is needed: D[u][v] = sum_y sum_x C[u][y] * g[y][x] * C[v][x]
  for (let u = 0; u < 8; u++) {
    for (let v = 0; v < 8; v++) {
      let s = 0
      for (let y = 0; y < N; y++) {
        let row = 0
        for (let x = 0; x < N; x++) row += g[y * N + x] * C[v][x]
        s += C[u][y] * row
      }
      low.push(s)
    }
  }
  const sorted = [...low].sort((a, b) => a - b)
  const median = (sorted[31] + sorted[32]) / 2
  return bitsToHex(low.map((v) => v > median))
}

const EPS = 1e-3

/** dHash: shrink to 9x8, bit = right pixel brighter than left pixel (encodes gradients). */
export function dhashFromGray32(g: Float64Array): string {
  const s = resizeArea(g, 32, 32, 9, 8)
  const bits: boolean[] = []
  // EPS: flat areas (e.g. white sky) give exact ties; float rounding differences between JS and
  // Python would flip those bits randomly, so a tie always counts as 0.
  for (let y = 0; y < 8; y++) for (let x = 0; x < 8; x++) bits.push(s[y * 9 + x + 1] - s[y * 9 + x] > EPS)
  return bitsToHex(bits)
}

/** Both hashes of an RGBA frame (e.g. canvas getImageData). */
export function hashFrame(rgba: Uint8ClampedArray | Uint8Array, w: number, h: number) {
  const g = gray32(rgba, w, h)
  return { phash: phashFromGray32(g), dhash: dhashFromGray32(g) }
}

/** Number of different bits between two hex hashes. */
export function hamming(a: string, b: string): number {
  let d = 0
  for (let i = 0; i < a.length; i++) {
    let x = parseInt(a[i], 16) ^ parseInt(b[i], 16)
    while (x) {
      d += x & 1
      x >>= 1
    }
  }
  return d
}
