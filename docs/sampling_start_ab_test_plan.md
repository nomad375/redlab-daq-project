# Sampling Start A/B Test Plan (MSCL Configurator vs SensorConnect)

## Scope
- Node: same physical node.
- Data path: same `mscl-stream` + same Influx bucket.
- Variable under test: who starts sampling:
  - A: official SensorConnect
  - B: our configurator (`/api/sampling/start`)

Goal: confirm whether our start flow changes node config/state and causes stop around ~60s.

## Safety / Pre-checks
1. Save current git state.
   - `git status -sb`
   - `git rev-parse --short HEAD`
2. Confirm containers are healthy.
   - `docker ps --format 'table {{.Names}}\t{{.Status}}'`
3. Confirm node ID and current sampling profile documented.
   - Node ID:
   - Sample rate:
   - Mode (log/transmit):
   - Any timeout settings:

Rollback point R0:
- No code changes. Baseline only.

## Baseline (A): Start from SensorConnect
1. Start sampling from SensorConnect with target profile.
2. Observe for 10 minutes:
   - `mscl_sensors/ch1` rate each minute.
   - node state from configurator status.
3. Capture logs:
   - `docker compose logs --since=15m mscl-app > /tmp/mscl_A.log`
4. Record result:
   - Sampling stable? `yes/no`
   - Stop timestamp (if any):
   - Avg Hz:

Expected baseline:
- no forced idle, continuous logging.

## Candidate Cause Test (B1): Our start flow as-is
1. Stop node if running, return to Idle.
2. Start sampling from our UI/API with same profile.
3. Observe 10 minutes with same method as baseline.
4. Capture logs:
   - `docker compose logs --since=15m mscl-app > /tmp/mscl_B1.log`
5. Record:
   - stop around ~60s? `yes/no`
   - any config/apply warnings

Decision:
- If B1 reproduces stop and A is stable, continue to B2/B3 isolations.

## Isolation B2: Start-only mode (disable applyConfig in runtime start path)
Change:
- In `_start_sampling_run`, skip `node.applyConfig(cfg)` and only send start command.
- Keep this behind env flag:
  - `MSCL_SAMPLING_START_ONLY=true`

Steps:
1. Implement flag-gated behavior.
2. Rebuild/restart only `mscl-app`.
3. Start sampling from our configurator.
4. Observe 10 minutes and capture logs:
   - `docker compose logs --since=15m mscl-app > /tmp/mscl_B2.log`

Pass criteria:
- If stop disappears, root cause likely in partial `applyConfig`.

Rollback point R1:
- Disable flag (`MSCL_SAMPLING_START_ONLY=false`) and restart `mscl-app`.
- Or revert code patch and redeploy previous image.

## Isolation B3: Config diff before/after start
Purpose:
- Verify if runtime start modifies persistent node settings unexpectedly.

Steps:
1. Read and store node config snapshot before start.
2. Start sampling from our configurator.
3. Read and store config snapshot after 15-30s.
4. Compare fields:
   - `inactivityTimeout`
   - `defaultMode`
   - `checkRadioInterval`
   - `samplingMode`
   - `dataMode`
   - lost beacon / diagnostic intervals

Artifacts:
- `/tmp/node_cfg_before.json`
- `/tmp/node_cfg_after.json`
- `/tmp/node_cfg_diff.txt`

Rollback point R2:
- Re-apply known-good settings via SensorConnect.
- Confirm node returns to stable behavior under SensorConnect start.

## Optional Isolation B4: Force sync-only start
Change:
- In `_start_sampling_best_effort`, disable non-sync fallback for test.

Steps:
1. Start sampling with sync-only path.
2. Observe 10 minutes.
3. Compare to B1.

Rollback point R3:
- Re-enable fallback path and restart `mscl-app`.

## Exit Criteria
- Root cause accepted if one isolated change reliably flips behavior:
  - B1 fails, B2 passes (most likely `applyConfig` side effect), or
  - B1 fails, B4 passes (start-method mismatch), or
  - config diff proves unwanted field changes.

## Recovery / Full Rollback
If test state becomes unstable:
1. Stop sampling.
2. Restore known-good settings in SensorConnect.
3. Restart `mscl-app` container:
   - `docker compose restart mscl-app`
4. Verify:
   - node in expected mode
   - `mscl_sensors/ch1` stable for 5 minutes

## Tracking
Last updated: 2026-02-11

- [ ] T0: Pre-checks complete (R0 available)
- [ ] T1: Baseline A (SensorConnect) recorded
- [ ] T2: B1 (our as-is) recorded
- [ ] T3: B2 (start-only) recorded
- [ ] T4: B3 (config diff) recorded
- [ ] T5: B4 (sync-only, optional) recorded
- [ ] T6: Root cause conclusion documented
- [ ] T7: Final rollback/production-safe state confirmed

## Notes
- Keep one variable changed at a time.
- Keep hardware wiring and node power conditions unchanged across A/B runs.
- Use same observation window (10 min) for comparability.
