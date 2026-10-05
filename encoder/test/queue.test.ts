// Offline queue: rows survive while offline / on errors, and re-sending is harmless.
import 'fake-indexeddb/auto'
import { describe, expect, it } from 'vitest'
import { openStore } from '../src/db'
import { PK, Queue, type Row, type Sender, type Table } from '../src/queue'

/** Fake server that behaves like upsert(..., { ignoreDuplicates: true }): existing keys are ignored. */
function fakeServer() {
  const rows = new Map<string, Row>()
  let down = false
  const send: Sender = async (table: Table, batch: Row[]) => {
    if (down) throw new Error('Failed to fetch')
    for (const r of batch) {
      const key = [table, ...PK[table].map((c) => r[c])].join(':')
      if (!rows.has(key)) rows.set(key, r)
    }
  }
  return { rows, send, setDown: (v: boolean) => (down = v) }
}

const fp = (i: number) => ({ trip_id: 't1', sample_idx: i, t_ms: i * 500, phash: '0'.repeat(16), dhash: 'f'.repeat(16) })
let dbN = 0
const newQueue = async (send: Sender) => new Queue(await openStore(`test-${dbN++}`), send)

describe('Queue', () => {
  it('keeps items while offline and empties after reconnect', async () => {
    const server = fakeServer()
    const q = await newQueue(server.send)
    q.simulateOffline = true
    for (let i = 0; i < 5; i++) await q.add('fingerprints', fp(i))
    await q.flush()
    expect(await q.pending()).toBe(5)
    expect(server.rows.size).toBe(0)

    q.simulateOffline = false
    await q.flush()
    expect(await q.pending()).toBe(0)
    expect(server.rows.size).toBe(5)
  })

  it('keeps items when the server is unreachable', async () => {
    const server = fakeServer()
    const q = await newQueue(server.send)
    server.setDown(true)
    await q.add('fingerprints', fp(0))
    await q.flush()
    expect(await q.pending()).toBe(1)
    expect(q.lastError).toContain('Failed to fetch')

    server.setDown(false)
    await q.flush()
    expect(await q.pending()).toBe(0)
    expect(q.lastError).toBe('')
  })

  it('sending the same batch twice gives no error and no duplicates', async () => {
    const server = fakeServer()
    const q = await newQueue(server.send)
    for (let i = 0; i < 3; i++) await q.add('fingerprints', fp(i))
    await q.add('fingerprints', fp(0)) // same key twice locally -> stored once
    expect(await q.pending()).toBe(3)
    await q.flush()
    for (let i = 0; i < 3; i++) await q.add('fingerprints', fp(i)) // resend (e.g. response was lost)
    await q.flush()
    expect(q.lastError).toBe('')
    expect(await q.pending()).toBe(0)
    expect(server.rows.size).toBe(3)
  })
})
