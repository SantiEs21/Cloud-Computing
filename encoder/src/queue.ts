// Offline-first upload queue. Every row is written to IndexedDB first and removed only after the
// server confirmed it. The server ignores duplicates (primary key + upsert ignoreDuplicates), so
// re-sending after a crash or a lost response is harmless and the order does not matter.
import type { DB } from './db'

export type Table = 'trips' | 'segments' | 'fingerprints'
export type Row = Record<string, unknown>
export type Sender = (table: Table, rows: Row[]) => Promise<void>

/** Primary key columns per table (same as supabase/schema.sql). */
export const PK: Record<Table, string[]> = {
  trips: ['id'],
  segments: ['trip_id', 'seq'],
  fingerprints: ['trip_id', 'sample_idx'],
}

interface Item {
  key: string
  table: Table
  row: Row
}

const BATCH = 500

export class Queue {
  sent = 0
  lastLatencyMs: number | null = null
  lastError = ''
  simulateOffline = false
  private flushing = false

  constructor(private db: DB, private send: Sender) {}

  async add(table: Table, row: Row) {
    // Same table + primary key => same queue key, so the local queue never holds a row twice.
    const key = [table, ...PK[table].map((c) => row[c])].join(':')
    await this.db.put('queue', { key, table, row } satisfies Item)
  }

  pending(): Promise<number> {
    return this.db.count('queue')
  }

  isOnline(): boolean {
    return !this.simulateOffline && !(typeof navigator !== 'undefined' && navigator.onLine === false)
  }

  /** Sends pending rows in batches. Safe to call often: does nothing if offline or already running. */
  async flush() {
    if (this.flushing || !this.isOnline()) return
    this.flushing = true
    try {
      const items: Item[] = await this.db.getAll('queue', undefined, BATCH)
      for (const table of ['trips', 'segments', 'fingerprints'] as Table[]) {
        const batch = items.filter((i) => i.table === table)
        if (!batch.length) continue
        const t0 = performance.now()
        await this.send(table, batch.map((i) => i.row)) // throws on network/server error -> rows stay
        this.lastLatencyMs = Math.round(performance.now() - t0)
        const tx = this.db.transaction('queue', 'readwrite')
        await Promise.all([...batch.map((i) => tx.store.delete(i.key)), tx.done])
        this.sent += batch.length
      }
      this.lastError = ''
    } catch (e) {
      this.lastError = e instanceof Error ? e.message : String(e)
    } finally {
      this.flushing = false
    }
  }
}
