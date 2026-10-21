# Average-Nigerian speech audit (held-out set A)

Messages: 56 | Passed: 53 (94.6%) | Answer language correct: 51/51 | Latency mean 12 ms, p95 18 ms (offline mode)

| Category | Passed | Total |
|---|---|---|
| holdout | 45 | 48 |
| dialogues | 8 | 8 |

## Failures

### holdout (3)
- `what do i need for my daughter passport`: expected **pp-minor**, got ['pp-documents']
- `my son is 7 and has no birth certificate`: expected **br-late**, got ['br-cost', 'br-how-register']
- `npc website for birth certificate`: expected **br-online-portals**, got ['br-cost']

