# Backend Code Review (Efficiency + Implementation Fit)

Scope: `backend/*.py` in `/mnt/c/Users/kyoungtj/GitProject/PC_ScreenCapture`.

## Findings (highest severity first)

### ~~High~~ - **해결됨**
- ~~Duplicate route definitions shadow each other, causing dead code and inconsistent response shapes.~~ **완료**: 중복 정의된 `GET /api/alerts/sounds` (775줄)와 `GET /api/alerts/images` (783줄) 핸들러 삭제. 완전한 버전(selected_id 포함)만 유지.

### Medium
- `process_path_pattern` rules cannot be re-applied during reclassification because `activities` do not store `process_path`. Live classification uses `process_path`, but DB-only reclassify routes build `activity_info` without it, so `process_path_pattern` rules silently stop working after the fact. Either persist `process_path` in `activities` or remove/disable `process_path_pattern` to avoid false expectations. `backend/database.py`, `backend/monitor_engine_thread.py`, `backend/api_server.py`, `backend/rule_engine.py`.
- Database restore swaps the SQLite file while other threads may still hold connections, and the API path does not pause monitoring before the swap. This risks "database is locked" errors or partial state until restart, and it makes recovery brittle. Prefer SQLite's backup API to restore into the live DB, or enforce a stop/pause callback and close all connections before replacing the file. `backend/import_export.py`, `backend/api_server.py`, `backend/monitor_engine_thread.py`.
- Async FastAPI endpoints call synchronous SQLite queries directly, which blocks the event loop under load. For a single-user desktop app this may be acceptable now, but if datasets grow or UI relies on concurrent requests, it will cause stalls. Either make endpoints sync (`def` not `async`) or move DB calls to a threadpool/aiosqlite. `backend/api_server.py`, `backend/database.py`.

### Low
- "Always block" semantics are inconsistent in focus mode. `_load_blocked_tags` says `None` means always block, but `is_blocked` treats `None` as "do not block" to avoid lockout. This mismatch makes it hard to reason about the UI state and can surprise users. Choose one behavior and encode it explicitly (e.g., a separate `block_always` flag). `backend/focus_blocker.py`.
- Crash recovery truncates long sessions: `cleanup_unfinished_activities` sets `end_time` to `start_time + 1 minute` for all open sessions, which can severely undercount legitimate time if the app crashed after hours. Consider ending at "app startup time" or keeping a `last_seen` heartbeat so you can estimate more accurately. `backend/database.py`.
- Focus time logic is duplicated in `FocusBlocker` and `_is_in_block_time` with slightly different semantics, which risks divergence over time. A small shared helper (or reusing the same logic) would reduce maintenance overhead. `backend/focus_blocker.py`, `backend/api_server.py`.

## Implementation Fit (efficiency vs. purpose)
- The design is generally practical for a single-developer desktop app: SQLite + polling + simple rules are quick to iterate. The main efficiency risks are the duplicated routes and the restore workflow, which can surprise users or break the UI unexpectedly.
- The rule engine favors simple OR-matching. That is good for ease of use, but it makes it hard to express "process + URL" constraints. If misclassification becomes noisy, consider a minimal AND mode (e.g., "match all populated fields") without adding a full rules DSL. `backend/rule_engine.py`.

## Suggested Next Steps (small wins)
1) ~~Remove the duplicate `GET /api/alerts/sounds` and `GET /api/alerts/images` endpoints and pick one response format.~~ **완료**
2) Decide on a single source of truth for focus-time checks and encode the always-block behavior explicitly. `backend/focus_blocker.py`, `backend/api_server.py`.
3) If reclassification is important, persist `process_path` (schema + writes + read). `backend/database.py`, `backend/monitor_engine_thread.py`, `backend/api_server.py`.
