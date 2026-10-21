# Average-Nigerian speech audit (held-out set B)

Messages: 40 | Passed: 36 (90.0%) | Answer language correct: 36/36 | Latency mean 13 ms, p95 16 ms (offline mode)

| Category | Passed | Total |
|---|---|---|
| holdout-b | 36 | 40 |

## Failures

### holdout-b (4)
- `dem collect my bag for bus, my passport dey inside`: expected **pp-lost**, got ['pp-fees']
- `which passport type should i get`: expected **pp-types**, got ['pp-fresh-steps']
- `can someone do my licence capture for me`: expected **dl-requirements|gen-boundary|gen-misuse**, got ['dl-reissue']
- `i am 30 and never had birth certificate`: expected **br-late**, got ['br-how-register', 'br-late']

