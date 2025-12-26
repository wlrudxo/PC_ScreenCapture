# API Review (Frontend ↔ Backend)

Scope: `webui/src/lib/api/client.js`, `webui/src/pages/*.svelte`, `backend/api_server.py`.

## Findings (highest severity first)

### ~~High~~ - **해결됨**
- ~~Duplicate route definitions shadow each other.~~ **완료**: 중복 핸들러 삭제됨 (backend_code_review 참조).

### ~~Medium~~ - **해결됨**
- ~~WebSocket URL ignores file:// mode.~~ **완료**: `client.js`의 미사용 `createWebSocket` 삭제됨. `websocket.js`가 file:// 모드 올바르게 처리.
- ~~Focus page expects to detect a 403 by checking `err.message.includes('403')`.~~ **완료**: `client.js`의 `request()`가 `error.status` 포함하도록 수정. `Focus.svelte`에서 `err.status === 403` 체크로 변경.

### ~~Low~~ - **해결됨**
- ~~Inconsistent response shapes.~~ **완료**: 중복 핸들러 삭제로 해결.

## Notes
- No missing endpoints were found for the current UI usage. Most REST calls align with the backend signatures.
- **모든 이슈 해결됨** (2025-12-27)
