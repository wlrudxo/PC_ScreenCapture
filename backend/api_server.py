"""
FastAPI 서버 - 웹 UI용 REST + WebSocket API
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.database import DatabaseManager


# === Pydantic Models ===

class TagCreate(BaseModel):
    name: str
    color: str

class TagUpdate(BaseModel):
    name: Optional[str] = None
    color: Optional[str] = None
    alert_enabled: Optional[bool] = None
    alert_message: Optional[str] = None
    alert_cooldown: Optional[int] = None
    block_enabled: Optional[bool] = None
    block_start_time: Optional[str] = None
    block_end_time: Optional[str] = None

class RuleCreate(BaseModel):
    name: str
    tag_id: int
    priority: int = 0
    enabled: bool = True
    process_pattern: Optional[str] = None
    url_pattern: Optional[str] = None
    window_title_pattern: Optional[str] = None
    chrome_profile: Optional[str] = None
    process_path_pattern: Optional[str] = None

class RuleUpdate(BaseModel):
    name: Optional[str] = None
    tag_id: Optional[int] = None
    priority: Optional[int] = None
    enabled: Optional[bool] = None
    process_pattern: Optional[str] = None
    url_pattern: Optional[str] = None
    window_title_pattern: Optional[str] = None
    chrome_profile: Optional[str] = None
    process_path_pattern: Optional[str] = None

class SettingsUpdate(BaseModel):
    settings: dict


# === WebSocket Manager ===

class ConnectionManager:
    """WebSocket 연결 관리"""

    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        """모든 연결에 메시지 전송"""
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass


# === Global instances ===
ws_manager = ConnectionManager()
db: Optional[DatabaseManager] = None


def get_db() -> DatabaseManager:
    """DB 인스턴스 반환"""
    global db
    if db is None:
        db = DatabaseManager()
    return db


# === Lifespan ===
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global db
    db = DatabaseManager()
    yield
    # Shutdown
    if db:
        db.close()


# === FastAPI App ===

app = FastAPI(
    title="Activity Tracker API",
    version="2.0.0",
    lifespan=lifespan
)

# CORS 설정 (개발용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# === Dashboard Endpoints ===

@app.get("/api/dashboard/daily")
async def get_dashboard_daily(date: str = Query(..., description="YYYY-MM-DD format")):
    """일간 대시보드 통계"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    start = datetime.combine(target_date.date(), datetime.min.time())
    end = start + timedelta(days=1)

    db = get_db()

    # 태그별 통계
    tag_stats = db.get_stats_by_tag(start, end)

    # 프로세스별 통계
    process_stats = db.get_stats_by_process(start, end, limit=10)

    # 활동 목록 (요약용)
    activities = db.get_activities(start, end)

    # 총 활동 시간 계산
    total_seconds = sum(s.get('total_seconds', 0) or 0 for s in tag_stats)

    # 첫/마지막 활동 시간
    first_activity = None
    last_activity = None
    if activities:
        sorted_activities = sorted(activities, key=lambda x: x['start_time'])
        first_activity = sorted_activities[0]['start_time']
        last_activity = sorted_activities[-1]['start_time']

    # 태그 전환 횟수 계산
    tag_switches = 0
    prev_tag = None
    for act in sorted(activities, key=lambda x: x['start_time']):
        if prev_tag is not None and act.get('tag_id') != prev_tag:
            tag_switches += 1
        prev_tag = act.get('tag_id')

    return {
        "date": date,
        "tagStats": tag_stats,
        "processStats": process_stats,
        "summary": {
            "totalSeconds": total_seconds,
            "activityCount": len(activities),
            "firstActivity": first_activity,
            "lastActivity": last_activity,
            "tagSwitches": tag_switches
        }
    }


@app.get("/api/dashboard/period")
async def get_dashboard_period(
    start: str = Query(..., description="Start date YYYY-MM-DD"),
    end: str = Query(..., description="End date YYYY-MM-DD")
):
    """기간별 대시보드 통계"""
    try:
        start_date = datetime.strptime(start, "%Y-%m-%d")
        end_date = datetime.strptime(end, "%Y-%m-%d") + timedelta(days=1)
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    db = get_db()

    tag_stats = db.get_stats_by_tag(start_date, end_date)
    process_stats = db.get_stats_by_process(start_date, end_date, limit=10)

    return {
        "start": start,
        "end": end,
        "tagStats": tag_stats,
        "processStats": process_stats
    }


@app.get("/api/dashboard/hourly")
async def get_dashboard_hourly(date: str = Query(..., description="YYYY-MM-DD format")):
    """시간대별 태그 통계 (7시~21시)"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    db = get_db()

    # 7시~21시 (15개 시간대)
    hours = list(range(7, 22))
    hourly_data = {h: {} for h in hours}

    # 해당 날짜의 모든 활동 가져오기
    start = datetime.combine(target_date.date(), datetime.min.time())
    end = start + timedelta(days=1)
    activities = db.get_activities(start, end)

    # 모든 태그 정보 가져오기
    tags = {t['id']: t for t in db.get_all_tags()}

    # 활동별로 시간대 분배
    for act in activities:
        start_time = act.get('start_time')
        end_time = act.get('end_time')
        tag_id = act.get('tag_id')

        if not start_time or not tag_id:
            continue

        # datetime 파싱
        if isinstance(start_time, str):
            start_time = datetime.fromisoformat(start_time)
        if isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time) if end_time else datetime.now()
        elif end_time is None:
            end_time = datetime.now()

        # 각 시간대에 걸친 시간 계산
        for hour in hours:
            hour_start = target_date.replace(hour=hour, minute=0, second=0, microsecond=0)
            hour_end = hour_start + timedelta(hours=1)

            # 겹치는 시간 계산
            overlap_start = max(start_time, hour_start)
            overlap_end = min(end_time, hour_end)

            if overlap_start < overlap_end:
                seconds = (overlap_end - overlap_start).total_seconds()
                if tag_id not in hourly_data[hour]:
                    hourly_data[hour][tag_id] = 0
                hourly_data[hour][tag_id] += seconds

    # 결과 포맷팅
    result = []
    for hour in hours:
        hour_stats = {
            "hour": hour,
            "tags": []
        }
        for tag_id, seconds in hourly_data[hour].items():
            tag = tags.get(tag_id, {})
            hour_stats["tags"].append({
                "tag_id": tag_id,
                "tag_name": tag.get('name', 'Unknown'),
                "tag_color": tag.get('color', '#888888'),
                "seconds": int(seconds),
                "minutes": round(seconds / 60, 1)
            })
        result.append(hour_stats)

    return {
        "date": date,
        "hourlyStats": result
    }


# === Timeline Endpoints ===

@app.get("/api/timeline")
async def get_timeline(
    date: str = Query(..., description="YYYY-MM-DD format"),
    tag_id: Optional[int] = Query(None, description="Filter by tag ID")
):
    """타임라인 조회"""
    try:
        target_date = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise HTTPException(400, "Invalid date format. Use YYYY-MM-DD")

    start = datetime.combine(target_date.date(), datetime.min.time())
    end = start + timedelta(days=1)

    db = get_db()
    activities = db.get_activities(start, end, tag_id=tag_id)

    return {
        "date": date,
        "activities": activities
    }


# === Tags Endpoints ===

@app.get("/api/tags")
async def get_tags():
    """모든 태그 조회"""
    db = get_db()
    tags = db.get_all_tags()

    # 각 태그별 룰 개수 추가
    rules = db.get_all_rules()
    rule_counts = {}
    for rule in rules:
        tag_id = rule.get('tag_id')
        rule_counts[tag_id] = rule_counts.get(tag_id, 0) + 1

    for tag in tags:
        tag['rule_count'] = rule_counts.get(tag['id'], 0)

    return {"tags": tags}


@app.post("/api/tags")
async def create_tag(tag: TagCreate):
    """태그 생성"""
    db = get_db()
    tag_id = db.create_tag(tag.name, tag.color)
    return {"id": tag_id, "message": "Tag created"}


@app.put("/api/tags/{tag_id}")
async def update_tag(tag_id: int, tag: TagUpdate):
    """태그 수정"""
    db = get_db()

    existing = db.get_tag_by_id(tag_id)
    if not existing:
        raise HTTPException(404, "Tag not found")

    update_data = tag.model_dump(exclude_unset=True)
    if update_data:
        db.update_tag(tag_id, **update_data)

    return {"message": "Tag updated"}


@app.delete("/api/tags/{tag_id}")
async def delete_tag(tag_id: int):
    """태그 삭제"""
    db = get_db()

    existing = db.get_tag_by_id(tag_id)
    if not existing:
        raise HTTPException(404, "Tag not found")

    db.delete_tag(tag_id)
    return {"message": "Tag deleted"}


# === Rules Endpoints ===

@app.get("/api/rules")
async def get_rules():
    """모든 룰 조회"""
    db = get_db()
    rules = db.get_all_rules()
    return {"rules": rules}


@app.post("/api/rules")
async def create_rule(rule: RuleCreate):
    """룰 생성"""
    db = get_db()
    rule_id = db.create_rule(**rule.model_dump())
    return {"id": rule_id, "message": "Rule created"}


@app.put("/api/rules/{rule_id}")
async def update_rule(rule_id: int, rule: RuleUpdate):
    """룰 수정"""
    db = get_db()

    existing = db.get_rule_by_id(rule_id)
    if not existing:
        raise HTTPException(404, "Rule not found")

    update_data = rule.model_dump(exclude_unset=True)
    if update_data:
        db.update_rule(rule_id, **update_data)

    return {"message": "Rule updated"}


@app.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: int):
    """룰 삭제"""
    db = get_db()

    existing = db.get_rule_by_id(rule_id)
    if not existing:
        raise HTTPException(404, "Rule not found")

    db.delete_rule(rule_id)
    return {"message": "Rule deleted"}


# === Settings Endpoints ===

@app.get("/api/settings")
async def get_settings():
    """모든 설정 조회"""
    db = get_db()

    settings_keys = [
        'alert_toast_enabled',
        'alert_sound_enabled',
        'alert_sound_mode',
        'alert_image_enabled',
        'alert_image_mode',
        'log_retention_days',
        'polling_interval',
        'idle_threshold'
    ]

    settings = {}
    for key in settings_keys:
        value = db.get_setting(key)
        settings[key] = value

    return {"settings": settings}


@app.put("/api/settings")
async def update_settings(data: SettingsUpdate):
    """설정 업데이트"""
    db = get_db()

    for key, value in data.settings.items():
        db.set_setting(key, str(value) if value is not None else None)

    return {"message": "Settings updated"}


# === Alert Endpoints ===

@app.get("/api/alerts/sounds")
async def get_alert_sounds():
    """알림음 목록 조회"""
    db = get_db()
    sounds = db.get_all_alert_sounds()
    return {"sounds": sounds}


@app.get("/api/alerts/images")
async def get_alert_images():
    """알림 이미지 목록 조회"""
    db = get_db()
    images = db.get_all_alert_images()
    return {"images": images}


# === Focus Endpoints ===

@app.get("/api/focus")
async def get_focus_settings():
    """집중 모드 설정 조회 (태그별)"""
    db = get_db()
    tags = db.get_all_tags()

    focus_settings = []
    for tag in tags:
        focus_settings.append({
            "id": tag['id'],
            "name": tag['name'],
            "color": tag['color'],
            "block_enabled": bool(tag.get('block_enabled', 0)),
            "block_start_time": tag.get('block_start_time', '09:00'),
            "block_end_time": tag.get('block_end_time', '18:00')
        })

    return {"focusSettings": focus_settings}


@app.put("/api/focus/{tag_id}")
async def update_focus_settings(tag_id: int, data: TagUpdate):
    """집중 모드 설정 수정"""
    db = get_db()

    existing = db.get_tag_by_id(tag_id)
    if not existing:
        raise HTTPException(404, "Tag not found")

    # 차단 활성 시간대에는 수정 불가 체크
    if existing.get('block_enabled'):
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute

        start_time = existing.get('block_start_time', '00:00')
        end_time = existing.get('block_end_time', '00:00')

        if start_time and end_time:
            start_h, start_m = map(int, start_time.split(':'))
            end_h, end_m = map(int, end_time.split(':'))
            start_minutes = start_h * 60 + start_m
            end_minutes = end_h * 60 + end_m

            if start_minutes <= current_minutes <= end_minutes:
                raise HTTPException(403, "Cannot modify during active block period")

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        db.update_tag(tag_id, **update_data)

    return {"message": "Focus settings updated"}


# === WebSocket Endpoint ===

@app.websocket("/ws/activity")
async def websocket_activity(websocket: WebSocket):
    """실시간 활동 업데이트 WebSocket"""
    await ws_manager.connect(websocket)
    try:
        while True:
            # 클라이언트 메시지 대기 (ping/pong)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# === Broadcast function (for external use) ===

async def broadcast_activity_update(activity: dict):
    """활동 업데이트를 모든 WebSocket 클라이언트에 전송"""
    await ws_manager.broadcast({
        "type": "activity_update",
        "data": activity
    })


# === Health Check ===

@app.get("/api/health")
async def health_check():
    """헬스 체크"""
    return {"status": "ok", "timestamp": datetime.now().isoformat()}


# === Run Server (for development) ===

def run_server(host: str = "127.0.0.1", port: int = 8000):
    """개발용 서버 실행"""
    import uvicorn
    uvicorn.run(app, host=host, port=port)


if __name__ == "__main__":
    run_server()
