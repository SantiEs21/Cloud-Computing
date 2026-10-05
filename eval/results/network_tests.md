# Network tests (encoder in Chrome, values read from Supabase)

"Gaps" = missing `sample_idx` values for the trip in Supabase (should be 0).

| Test | How | Pending max | Time to empty queue after reconnect | Rows lost / gaps | Duplicates in DB | Notes |
|---|---|---|---|---|---|---|
| Real network off — file mode | Wi-Fi off during the whole trip `e5488849` (tripA.mp4, 83.6 s), then reconnect | 178 rows (1 trip + 9 segments + 168 fingerprints) | one batch: all 168 fingerprints have the same server arrival second (retry runs every 3 s) | 0 / 0 gaps (sample_idx and seq) | 0 (primary keys) | online reference trip `a2280b49`: rows arrive spread over 83 s (~6 per 3 s) |
| Real network off — webcam | Wi-Fi off during trip `d284be5b` (19.1 s), then reconnect | 39 rows (1 + 2 + 36) | one batch: all rows have the same server arrival second | 0 / 0 gaps | 0 | |
| Duplicate sends | `SUPABASE_IT=1 npm test` (sends the same row twice) | - | - | - | 0 (second send ignored, first version kept) | automated, passes |
