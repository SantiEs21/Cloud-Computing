# Network tests (manual, encoder in Chrome)

Fill in with the values shown in the encoder's Status table and in Supabase.
"Gaps" = missing `sample_idx` values for the trip in Supabase (should be 0).

| Test | How | Pending max | Time to empty queue after reconnect | Rows lost / gaps | Duplicates in DB | Notes |
|---|---|---|---|---|---|---|
| Offline 30 s | tick "Simulate offline" for 30 s while recording | | | | | |
| Real network off — file mode | Wi-Fi off during the whole trip `e5488849` (tripA.mp4, 83.6 s), then reconnect | 178 rows (1 trip + 9 segments + 168 fingerprints) | all 168 fingerprints arrived within the same second (first retry, ≤ 3 s) | 0 / 0 gaps (sample_idx and seq) | 0 (primary keys) | online reference trip `a2280b49`: rows arrive spread over 83 s (~6 per 3 s) |
| Real network off — webcam | Wi-Fi off during trip `d284be5b` (19.1 s), then reconnect | 39 rows (1 + 2 + 36) | all arrived within the same second | 0 / 0 gaps | 0 | |
| Intermittent | toggle offline on/off every ~5 s for 1 min | | | | | |
| Server unreachable | wrong `VITE_SUPABASE_URL` in `encoder/.env`, record 20 s, fix URL, reload page | | | | | rows sent from IndexedDB after reload? |
| Duplicate sends | `SUPABASE_IT=1 npm test` (sends the same row twice) | - | - | - | 0 (second send ignored, first version kept) | automated, passes |
| Reload while offline | simulate offline, record, reload page, untick | | | | | queue survives in IndexedDB? |
