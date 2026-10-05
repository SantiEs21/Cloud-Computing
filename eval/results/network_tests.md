# Network tests (manual, encoder in Chrome)

Fill in with the values shown in the encoder's Status table and in Supabase.
"Gaps" = missing `sample_idx` values for the trip in Supabase (should be 0).

| Test | How | Pending max | Time to empty queue after reconnect | Rows lost / gaps | Duplicates in DB | Notes |
|---|---|---|---|---|---|---|
| Offline 30 s | tick "Simulate offline" for 30 s while recording | | | | | |
| Browser offline | DevTools → Network → Offline for 30 s | | | | | |
| Intermittent | toggle offline on/off every ~5 s for 1 min | | | | | |
| Server unreachable | wrong `VITE_SUPABASE_URL` in `encoder/.env`, record 20 s, fix URL, reload page | | | | | rows sent from IndexedDB after reload? |
| Duplicate sends | `SUPABASE_IT=1 npm test` (sends the same row twice) | - | - | - | | automated |
| Reload while offline | simulate offline, record, reload page, untick | | | | | queue survives in IndexedDB? |
