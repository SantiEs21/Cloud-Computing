// Integration test against the real Supabase project (needs encoder/.env and the schema).
// Run with: SUPABASE_IT=1 npm test
import { describe, expect, it } from 'vitest'
import { supabase, supabaseSender } from '../src/supabase'

describe.skipIf(!process.env.SUPABASE_IT)('Supabase (integration)', () => {
  const trip = crypto.randomUUID()
  const row = { trip_id: trip, sample_idx: 0, t_ms: 0, phash: '0123456789abcdef', dhash: 'fedcba9876543210' }

  it('upsert of the same row twice is accepted and stored once', async () => {
    await supabaseSender('fingerprints', [row])
    await supabaseSender('fingerprints', [{ ...row, phash: 'ffffffffffffffff' }]) // duplicate key: ignored
    const { data, error } = await supabase.from('fingerprints').select('*').eq('trip_id', trip)
    expect(error).toBeNull()
    expect(data).toHaveLength(1)
    expect(data![0].phash).toBe(row.phash) // the first version is kept, not overwritten
  })

  it('the public key cannot update or delete (append-only)', async () => {
    await supabase.from('fingerprints').update({ phash: '0000000000000000' }).eq('trip_id', trip)
    await supabase.from('fingerprints').delete().eq('trip_id', trip)
    const { data } = await supabase.from('fingerprints').select('phash').eq('trip_id', trip)
    expect(data).toEqual([{ phash: row.phash }])
  })
})
