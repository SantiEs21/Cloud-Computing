import { createClient } from '@supabase/supabase-js'
import { PK, type Sender } from './queue'

const url = import.meta.env.VITE_SUPABASE_URL as string | undefined
const key = import.meta.env.VITE_SUPABASE_ANON_KEY as string | undefined
export const configured = Boolean(url && key)

export const supabase = createClient(url || 'http://missing', key || 'missing', {
  auth: { persistSession: false },
})

/** Upsert that ignores rows whose primary key already exists (ON CONFLICT DO NOTHING). */
export const supabaseSender: Sender = async (table, rows) => {
  const { error } = await supabase
    .from(table)
    .upsert(rows, { onConflict: PK[table].join(','), ignoreDuplicates: true })
  if (error) throw new Error(error.message)
}

/** Server-side deletion of rows older than `hours` (see purge_expired in supabase/schema.sql). */
export async function purgeServer(hours: number) {
  const { data, error } = await supabase.rpc('purge_expired', { hours })
  if (error) throw new Error(error.message)
  return data as { fingerprints: number; segments: number; trips: number }
}
