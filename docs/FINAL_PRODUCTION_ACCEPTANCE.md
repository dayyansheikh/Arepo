# Final production acceptance test

Run after deployment (and repeat any time). Every item has a command and an expected result. Any
Fail blocks go-live.

## API

| Check | Command | Expected |
| --- | --- | --- |
| Health | `curl $API/health` | `200` `{"status":"ok"}` |
| Research status | `curl $API/api/research/status` | `200`; `edge_supported:false`, `incomplete_cohorts:0`, real `model_version` |
| Synthetic excluded | `curl -o /dev/null -w '%{http_code}' $API/api/cohorts/latest` | `404` until a real cohort exists |
| Verify script | `API_BASE=$API scripts/verify_production.sh` | `VERIFY OK` |

## Schema / migration

| Check | Command | Expected |
| --- | --- | --- |
| Schema current | (Render shell) `python -m astrolabe.storage.migrate_cli check` | `"current": true`, version 3 |
| Migration idempotent | `migrate_cli upgrade` twice | second run `columns_added: []` |

## First collection (run at a 6h boundary, e.g. just after 12:00 UTC)

| Check | Command | Expected |
| --- | --- | --- |
| 6h freeze | `research-freeze --cadence 6h` | `frozen:true`, universe > 0, `rejected` absent |
| Daily freeze | `research-freeze --cadence daily` | `frozen:true` |
| Weekly freeze (Mon) | `research-freeze --cadence weekly` | `frozen:true` |
| Idempotent | re-run 6h freeze | `already_frozen:true` |
| Forward (after ≥1h) | `research-forward` | `written > 0`, `invalid_predates_freeze:0` |
| Health check | `API_BASE=$API scripts/check_research_health.sh` | `HEALTH OK`; cohort counts > 0 |

## Frontend

| Check | Steps | Expected |
| --- | --- | --- |
| Loads | open `https://arepo.dsheikh.cc` | Opportunities/Explore/Signal Lab/Replay render |
| Research status | Replay → "Edge-research status" | amber "not enough evidence yet" banner + real counts |
| Market routing | open markets `2694364` and `2822017` | both open correctly |
| No overflow | any page, narrow width | no horizontal scrollbar |
| Popovers | click any info "i" | stays in viewport; Escape/outside-click closes |
| Title | browser tab | exactly `Arepo` |

## Automatic operation

| Check | How | Expected |
| --- | --- | --- |
| Runs with browser closed | close all browsers; wait for the next 6h boundary | a new 6h cohort appears in `/api/research/status` |
| Failure recovery | pause then resume the forward cron | backlog catches up; no duplicates |

Any locally-testable item was verified in `docs/final-production-equivalent-dry-run.md` and
`docs/FINAL_PREDEPLOYMENT_LOCAL_ACCEPTANCE.md`.
