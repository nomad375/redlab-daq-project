# Optimization Plan

## Goals
- Reduce CPU and log overhead during steady-state streaming.
- Reduce API latency for read/write configuration endpoints.
- Improve resilience under transient MSCL/base-station faults.

## Baseline (Current)
- `app/mscl_config.py` is the main hotspot (`~2100` lines) with long critical handlers.
- Stream path uses a reader thread + writer loop with frequent polling and batching.
- Many hardware/API calls are best-effort and repeated per request (read path).

## Phase 1 (Low Risk, Immediate)
- Throttle stream batch logs with `MSCL_STREAM_LOG_INTERVAL_SEC` (done).
- Use `render_template()` instead of disk read per request for `/` (done).
- Use one thread-safe disconnect helper for shared base state (done).
- Keep strict startup env validation for all writers (done for `redlab_main`).

## Phase 2 (High Impact, Medium Risk)
- Split `api_read()` into helper functions:
  - base read,
  - channel/range/unit reads,
  - feature-option reads.
- Add per-node cache TTLs by field category:
  - static fields (model/fw/options): longer TTL (e.g. 60-120s),
  - volatile fields (state/comm): short TTL (e.g. 2-5s).
- Reduce repeated `features.*` probing per request by caching supported capabilities per node/model.
- Consolidate duplicated point decode helpers (`_point_channel`, `_point_value`) into one shared module.

## Phase 3 (Throughput and Stability)
- Introduce bounded flush cadence for stream writes:
  - cap points per write,
  - max write period,
  - drop counters exported to status endpoint.
- Add lightweight counters/metrics:
  - packets read, points written, queue depth high-water mark, reconnect count, EEPROM retry count.
- Optional: switch `mscl_main.py` writer to async write options with controlled batch/flush settings.

## Validation Plan
- Functional:
  - `python3 -m compileall app`
  - Manual API smoke: connect, read, write, sampling start/stop, reconnect.
- Performance:
  - Measure API read latency (`/api/read/<node_id>`) p50/p95 before/after.
  - Measure stream log volume and CPU usage before/after log throttling.
  - Verify no increase in dropped packets during sustained load.

## Rollout Strategy
- Enable optimizations via env flags where practical.
- Ship Phase 2 in small PR-sized slices:
  1. cache/capability helpers,
  2. `api_read` decomposition,
  3. point decoder dedup.
- Keep behavior-compatible defaults and add targeted regression checks around node read/write flows.
