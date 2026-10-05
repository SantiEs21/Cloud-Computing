// Local storage in IndexedDB: the upload queue and the recorded segments (so they survive a reload).
import { openDB, type IDBPDatabase } from 'idb'

export type DB = IDBPDatabase

export function openStore(name = 'dashcam'): Promise<DB> {
  return openDB(name, 1, {
    upgrade(db) {
      db.createObjectStore('queue', { keyPath: 'key' })
      db.createObjectStore('segments', { keyPath: 'id' })
    },
  })
}

export interface LocalSegment {
  id: string // `${trip_id}:${seq}`
  trip_id: string
  seq: number
  createdAt: number
  sha256: string
  mime: string
  blob: Blob
}

export const saveSegment = (db: DB, s: LocalSegment) => db.put('segments', s)
export const listSegments = (db: DB): Promise<LocalSegment[]> => db.getAll('segments')

/** Deletes local segments older than maxAgeMs; returns how many were deleted. */
export async function deleteOldSegments(db: DB, maxAgeMs: number, now = Date.now()): Promise<number> {
  const old = (await listSegments(db)).filter((s) => now - s.createdAt > maxAgeMs)
  for (const s of old) await db.delete('segments', s.id)
  return old.length
}
