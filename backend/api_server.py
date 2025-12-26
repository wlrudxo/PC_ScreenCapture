"""
FastAPI 서버 - 웹 UI용 REST + WebSocket API
"""
import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Any
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uuid
from pathlib import Path

from backend.database import DatabaseManager


# === Runtime Engine References ===
# main_webview.py에서 설정, 룰/집중 설정 변경 시 reload 호출용
_rule_engine = None
_focus_blocker = None


def set_runtime_engines(rule_engine, focus_blocker):
    """런타임 엔진 인스턴스 설정 (main_webview.py에서 호출)"""
    global _rule_engine, _focus_blocker
    _rule_engine = rule_engine
    _focus_blocker = focus_blocker


def _reload_rule_engine():
    """룰 엔진 새로고침"""
    if _rule_engine:
        _rule_engine.reload_rules()
        print("[API] RuleEngine 새로고침 완료")


def _reload_focus_blocker():
    """집중 모드 새로고침"""
    if _focus_blocker:
        _focus_blocker.reload()
        print("[API] FocusBlocker 새로고침 완료")


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

    # 총 활동 시간 계산 (자리비움 제외)
    total_seconds = sum(
        s.get('total_seconds', 0) or 0
        for s in tag_stats
        if s.get('tag_name') != '자리비움'
    )

    # 태그 통계에서 자리비움 제외
    tag_stats = [s for s in tag_stats if s.get('tag_name') != '자리비움']

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
    # 자리비움 제외
    tag_stats = [s for s in tag_stats if s.get('tag_name') != '자리비움']
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
            tag_name = tag.get('name', 'Unknown')
            # 자리비움 제외
            if tag_name == '자리비움':
                continue
            hour_stats["tags"].append({
                "tag_id": tag_id,
                "tag_name": tag_name,
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
    _reload_rule_engine()
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
        _reload_rule_engine()

    return {"message": "Tag updated"}


@app.delete("/api/tags/{tag_id}")
async def delete_tag(tag_id: int):
    """태그 삭제"""
    db = get_db()

    existing = db.get_tag_by_id(tag_id)
    if not existing:
        raise HTTPException(404, "Tag not found")

    db.delete_tag(tag_id)
    _reload_rule_engine()
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
    _reload_rule_engine()
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
        _reload_rule_engine()

    return {"message": "Rule updated"}


@app.delete("/api/rules/{rule_id}")
async def delete_rule(rule_id: int):
    """룰 삭제"""
    db = get_db()

    existing = db.get_rule_by_id(rule_id)
    if not existing:
        raise HTTPException(404, "Rule not found")

    db.delete_rule(rule_id)
    _reload_rule_engine()
    return {"message": "Rule deleted"}


# === Reclassify Endpoints ===

@app.post("/api/reclassify/untagged")
async def reclassify_untagged():
    """미분류 항목 재분류"""
    from backend.rule_engine import RuleEngine

    db = get_db()
    rule_engine = RuleEngine(db)

    # 미분류 활동 가져오기
    unclassified = db.get_unclassified_activities()
    if not unclassified:
        return {"reclassified": 0, "remaining": 0, "message": "No unclassified activities"}

    # 미분류 태그 ID
    unclassified_tag = db.get_tag_by_name('미분류')
    unclassified_tag_id = unclassified_tag['id'] if unclassified_tag else None

    reclassified_count = 0
    for activity in unclassified:
        activity_info = {
            'process_name': activity.get('process_name'),
            'window_title': activity.get('window_title'),
            'chrome_url': activity.get('chrome_url'),
            'chrome_profile': activity.get('chrome_profile')
        }

        tag_id, rule_id = rule_engine.match(activity_info)

        # 미분류가 아닌 경우만 업데이트
        if tag_id != unclassified_tag_id:
            db.update_activity_classification(activity['id'], tag_id, rule_id)
            reclassified_count += 1

    return {
        "reclassified": reclassified_count,
        "remaining": len(unclassified) - reclassified_count,
        "message": f"Reclassified {reclassified_count} activities"
    }


@app.post("/api/reclassify/all")
async def reclassify_all():
    """모든 활동 재분류"""
    from backend.rule_engine import RuleEngine

    db = get_db()
    rule_engine = RuleEngine(db)

    # 모든 활동 가져오기
    all_activities = db.get_all_activities_for_reclassify()
    if not all_activities:
        return {"reclassified": 0, "message": "No activities to reclassify"}

    reclassified_count = 0
    for activity in all_activities:
        activity_info = {
            'process_name': activity.get('process_name'),
            'window_title': activity.get('window_title'),
            'chrome_url': activity.get('chrome_url'),
            'chrome_profile': activity.get('chrome_profile')
        }

        tag_id, rule_id = rule_engine.match(activity_info)
        db.update_activity_classification(activity['id'], tag_id, rule_id)
        reclassified_count += 1

    return {
        "reclassified": reclassified_count,
        "message": f"Reclassified {reclassified_count} activities"
    }


@app.get("/api/activities/unclassified")
async def get_unclassified_activities():
    """미분류 활동 목록 (그룹화)"""
    db = get_db()
    activities = db.get_unclassified_activities()

    # 프로세스+제목+URL로 그룹화
    grouped = {}
    for act in activities:
        key = (
            act.get('process_name') or '',
            act.get('window_title') or '',
            act.get('chrome_url') or ''
        )
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(act['id'])

    # 정렬 (개수 내림차순)
    result = [
        {
            "process_name": k[0],
            "window_title": k[1],
            "chrome_url": k[2],
            "ids": v,
            "count": len(v)
        }
        for k, v in sorted(grouped.items(), key=lambda x: len(x[1]), reverse=True)
    ]

    return {"groups": result, "total": len(activities)}


class ActivityDeleteRequest(BaseModel):
    ids: List[int]


@app.post("/api/activities/delete")
async def delete_activities(data: ActivityDeleteRequest):
    """활동 삭제"""
    db = get_db()
    db.delete_activities(data.ids)
    return {"deleted": len(data.ids), "message": f"Deleted {len(data.ids)} activities"}


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
        # 자리비움, 미분류 태그는 차단 대상에서 제외
        if tag['name'] in ('자리비움', '미분류'):
            continue

        focus_settings.append({
            "id": tag['id'],
            "name": tag['name'],
            "color": tag['color'],
            "block_enabled": bool(tag.get('block_enabled', 0)),
            "block_start_time": tag.get('block_start_time') or None,
            "block_end_time": tag.get('block_end_time') or None
        })

    return {"focusSettings": focus_settings}


def _is_in_block_time(start_time: str, end_time: str) -> bool:
    """현재 시간이 차단 시간대 내인지 확인 (자정 넘김 지원)"""
    if not start_time or not end_time:
        return True  # 시간 미설정 = 항상 차단 중

    try:
        now = datetime.now()
        current_minutes = now.hour * 60 + now.minute

        start_h, start_m = map(int, start_time.split(':'))
        end_h, end_m = map(int, end_time.split(':'))
        start_minutes = start_h * 60 + start_m
        end_minutes = end_h * 60 + end_m

        if start_minutes <= end_minutes:
            # 일반 케이스: 09:00 ~ 18:00
            return start_minutes <= current_minutes <= end_minutes
        else:
            # 자정 넘는 케이스: 22:00 ~ 02:00
            return current_minutes >= start_minutes or current_minutes <= end_minutes
    except:
        return True  # 파싱 실패 시 차단 중으로 간주


@app.put("/api/focus/{tag_id}")
async def update_focus_settings(tag_id: int, data: TagUpdate):
    """집중 모드 설정 수정"""
    db = get_db()

    existing = db.get_tag_by_id(tag_id)
    if not existing:
        raise HTTPException(404, "Tag not found")

    # 차단 활성 시간대에는 수정 불가 체크
    if existing.get('block_enabled'):
        start_time = existing.get('block_start_time')
        end_time = existing.get('block_end_time')

        if _is_in_block_time(start_time, end_time):
            raise HTTPException(403, "Cannot modify during active block period")

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        db.update_tag(tag_id, **update_data)
        _reload_focus_blocker()

    return {"message": "Focus settings updated"}


# === Alert/Notification Endpoints ===

class AlertSettingsUpdate(BaseModel):
    toast_enabled: Optional[bool] = None
    sound_enabled: Optional[bool] = None
    sound_mode: Optional[str] = None  # 'single' | 'random'
    sound_selected: Optional[int] = None
    image_enabled: Optional[bool] = None
    image_mode: Optional[str] = None
    image_selected: Optional[int] = None


class TagAlertUpdate(BaseModel):
    alert_enabled: Optional[bool] = None
    alert_message: Optional[str] = None
    alert_cooldown: Optional[int] = None


@app.get("/api/alerts/settings")
async def get_alert_settings():
    """전역 알림 설정 조회"""
    db = get_db()
    return {
        "toast_enabled": db.get_setting('alert_toast_enabled', '1') == '1',
        "sound_enabled": db.get_setting('alert_sound_enabled', '0') == '1',
        "sound_mode": db.get_setting('alert_sound_mode', 'single'),
        "sound_selected": int(db.get_setting('alert_sound_selected', '0') or 0),
        "image_enabled": db.get_setting('alert_image_enabled', '0') == '1',
        "image_mode": db.get_setting('alert_image_mode', 'single'),
        "image_selected": int(db.get_setting('alert_image_selected', '0') or 0)
    }


@app.put("/api/alerts/settings")
async def update_alert_settings(data: AlertSettingsUpdate):
    """전역 알림 설정 수정"""
    db = get_db()
    update_data = data.model_dump(exclude_unset=True)

    if 'toast_enabled' in update_data:
        db.set_setting('alert_toast_enabled', '1' if update_data['toast_enabled'] else '0')
    if 'sound_enabled' in update_data:
        db.set_setting('alert_sound_enabled', '1' if update_data['sound_enabled'] else '0')
    if 'sound_mode' in update_data:
        db.set_setting('alert_sound_mode', update_data['sound_mode'])
    if 'sound_selected' in update_data:
        db.set_setting('alert_sound_selected', str(update_data['sound_selected']))
    if 'image_enabled' in update_data:
        db.set_setting('alert_image_enabled', '1' if update_data['image_enabled'] else '0')
    if 'image_mode' in update_data:
        db.set_setting('alert_image_mode', update_data['image_mode'])
    if 'image_selected' in update_data:
        db.set_setting('alert_image_selected', str(update_data['image_selected']))

    return {"message": "Alert settings updated"}


@app.get("/api/alerts/sounds")
async def get_alert_sounds():
    """알림음 목록 조회"""
    db = get_db()
    sounds = db.get_all_alert_sounds()
    selected_id = int(db.get_setting('alert_sound_selected', '0') or 0)
    return {"sounds": sounds, "selected_id": selected_id}


@app.post("/api/alerts/sounds/upload")
async def upload_alert_sound(
    file: UploadFile = File(...),
    name: str = Form(...)
):
    """알림음 업로드"""
    from backend.config import AppConfig

    # 확장자 검증
    allowed_ext = {'.wav', '.mp3', '.ogg', '.flac'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_ext:
        raise HTTPException(400, f"Unsupported file type. Allowed: {allowed_ext}")

    sounds_dir = AppConfig.get_sounds_dir()

    # WAV가 아니면 변환 필요 (클라이언트에서 처리하거나 ffmpeg 사용)
    # 일단 그대로 저장
    output_name = f"{uuid.uuid4().hex}{file_ext}"
    output_path = sounds_dir / output_name

    content = await file.read()
    with open(output_path, 'wb') as f:
        f.write(content)

    db = get_db()
    sound_id = db.add_alert_sound(name, str(output_path))

    return {"id": sound_id, "name": name, "file_path": str(output_path)}


@app.delete("/api/alerts/sounds/{sound_id}")
async def delete_alert_sound(sound_id: int):
    """알림음 삭제"""
    db = get_db()
    sound = db.get_alert_sound_by_id(sound_id)
    if not sound:
        raise HTTPException(404, "Sound not found")

    # 파일도 삭제
    file_path = Path(sound['file_path'])
    if file_path.exists():
        file_path.unlink()

    db.delete_alert_sound(sound_id)
    return {"message": "Sound deleted"}


@app.get("/api/alerts/images")
async def get_alert_images():
    """알림 이미지 목록 조회"""
    db = get_db()
    images = db.get_all_alert_images()
    selected_id = int(db.get_setting('alert_image_selected', '0') or 0)
    return {"images": images, "selected_id": selected_id}


@app.post("/api/alerts/images/upload")
async def upload_alert_image(
    file: UploadFile = File(...),
    name: str = Form(...)
):
    """알림 이미지 업로드"""
    from backend.config import AppConfig

    # 확장자 검증
    allowed_ext = {'.png', '.jpg', '.jpeg'}
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_ext:
        raise HTTPException(400, f"Unsupported file type. Allowed: {allowed_ext}")

    images_dir = AppConfig.get_app_dir() / "images"
    images_dir.mkdir(exist_ok=True)

    output_name = f"{uuid.uuid4().hex}.png"
    output_path = images_dir / output_name

    content = await file.read()

    # 이미지 처리 (PIL로 2:1 비율 리사이즈)
    try:
        from PIL import Image
        import io

        img = Image.open(io.BytesIO(content))

        # 2:1 비율로 크롭 (364x182 권장, hero image 규격)
        target_ratio = 2.0
        current_ratio = img.width / img.height

        if current_ratio > target_ratio:
            # 너무 넓음 - 좌우 자르기
            new_width = int(img.height * target_ratio)
            left = (img.width - new_width) // 2
            img = img.crop((left, 0, left + new_width, img.height))
        elif current_ratio < target_ratio:
            # 너무 높음 - 상하 자르기
            new_height = int(img.width / target_ratio)
            top = (img.height - new_height) // 2
            img = img.crop((0, top, img.width, top + new_height))

        # 리사이즈
        img = img.resize((364, 182), Image.Resampling.LANCZOS)

        # PNG로 저장
        if img.mode in ('RGBA', 'LA', 'P'):
            img = img.convert('RGB')
        img.save(str(output_path), 'PNG')

    except ImportError:
        # PIL 없으면 그냥 저장
        with open(output_path, 'wb') as f:
            f.write(content)

    db = get_db()
    image_id = db.add_alert_image(name, str(output_path))

    return {"id": image_id, "name": name, "file_path": str(output_path)}


@app.delete("/api/alerts/images/{image_id}")
async def delete_alert_image(image_id: int):
    """알림 이미지 삭제"""
    db = get_db()
    image = db.get_alert_image_by_id(image_id)
    if not image:
        raise HTTPException(404, "Image not found")

    # 파일도 삭제
    file_path = Path(image['file_path'])
    if file_path.exists():
        file_path.unlink()

    db.delete_alert_image(image_id)
    return {"message": "Image deleted"}


@app.get("/api/alerts/images/file/{image_id}")
async def get_alert_image_file(image_id: int):
    """알림 이미지 파일 서빙"""
    db = get_db()
    image = db.get_alert_image_by_id(image_id)
    if not image:
        raise HTTPException(404, "Image not found")

    file_path = Path(image['file_path'])
    if not file_path.exists():
        raise HTTPException(404, "Image file not found")

    return FileResponse(file_path, media_type="image/png")


@app.get("/api/alerts/tags")
async def get_tag_alert_settings():
    """태그별 알림 설정 조회"""
    db = get_db()
    tags = db.get_all_tags()

    result = []
    for tag in tags:
        # 자리비움, 미분류는 알림 대상에서 제외
        if tag['name'] in ('자리비움', '미분류'):
            continue

        result.append({
            "id": tag['id'],
            "name": tag['name'],
            "color": tag['color'],
            "alert_enabled": bool(tag.get('alert_enabled', 0)),
            "alert_message": tag.get('alert_message') or '',
            "alert_cooldown": tag.get('alert_cooldown') or 30
        })

    return {"tags": result}


@app.put("/api/alerts/tags/{tag_id}")
async def update_tag_alert_settings(tag_id: int, data: TagAlertUpdate):
    """태그별 알림 설정 수정"""
    db = get_db()

    existing = db.get_tag_by_id(tag_id)
    if not existing:
        raise HTTPException(404, "Tag not found")

    update_data = data.model_dump(exclude_unset=True)
    if update_data:
        db.update_tag(tag_id, **update_data)

    return {"message": "Tag alert settings updated"}


# === Auto Start & Data Management Endpoints ===

@app.get("/api/settings/autostart")
async def get_autostart_status():
    """자동 시작 설정 상태 조회"""
    from backend.auto_start import AutoStartManager
    return {"enabled": AutoStartManager.is_enabled()}


@app.put("/api/settings/autostart")
async def set_autostart_status(data: dict):
    """자동 시작 설정 변경"""
    from backend.auto_start import AutoStartManager

    enabled = data.get('enabled', False)

    if enabled:
        success = AutoStartManager.enable()
    else:
        success = AutoStartManager.disable()

    if not success:
        raise HTTPException(500, "Failed to update auto-start setting")

    return {"enabled": AutoStartManager.is_enabled()}


@app.get("/api/data/db/backup")
async def backup_database():
    """데이터베이스 백업 (파일 다운로드)"""
    from fastapi.responses import FileResponse
    from backend.import_export import ImportExportManager
    from backend.config import AppConfig
    import tempfile

    db = get_db()
    ie_manager = ImportExportManager(db)

    # 임시 파일에 백업
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"activity_tracker_backup_{timestamp}.db"
    backup_path = Path(tempfile.gettempdir()) / backup_name

    success = ie_manager.export_database(str(backup_path))

    if not success:
        raise HTTPException(500, "Failed to create backup")

    return FileResponse(
        path=str(backup_path),
        filename=backup_name,
        media_type="application/octet-stream"
    )


@app.post("/api/data/db/restore")
async def restore_database(file: UploadFile = File(...)):
    """데이터베이스 복원 (앱 재시작 필요)"""
    from backend.import_export import ImportExportManager
    import tempfile

    # 확장자 검증
    if not file.filename.endswith('.db'):
        raise HTTPException(400, "Invalid file type. Only .db files are allowed.")

    # 임시 파일로 저장
    temp_path = Path(tempfile.gettempdir()) / f"restore_{uuid.uuid4().hex}.db"

    content = await file.read()
    with open(temp_path, 'wb') as f:
        f.write(content)

    db = get_db()
    ie_manager = ImportExportManager(db)

    success, message = ie_manager.import_database(str(temp_path))

    # 임시 파일 삭제
    if temp_path.exists():
        temp_path.unlink()

    if not success:
        raise HTTPException(500, message)

    return {"message": message, "restart_required": True}


@app.get("/api/data/rules/export")
async def export_rules():
    """분류 룰 내보내기 (JSON)"""
    from backend.import_export import ImportExportManager

    db = get_db()
    ie_manager = ImportExportManager(db)

    tags = db.get_all_tags()
    rules = db.get_all_rules(order_by='priority DESC')

    export_data = {
        "export_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "version": "1.0",
        "tags": tags,
        "rules": rules
    }

    return export_data


@app.post("/api/data/rules/import")
async def import_rules(
    file: UploadFile = File(...),
    merge_mode: bool = Form(True)
):
    """분류 룰 가져오기 (JSON)"""
    from backend.import_export import ImportExportManager
    import tempfile

    # 확장자 검증
    if not file.filename.endswith('.json'):
        raise HTTPException(400, "Invalid file type. Only .json files are allowed.")

    # 임시 파일로 저장
    temp_path = Path(tempfile.gettempdir()) / f"rules_{uuid.uuid4().hex}.json"

    content = await file.read()
    with open(temp_path, 'wb') as f:
        f.write(content)

    db = get_db()
    ie_manager = ImportExportManager(db)

    # 유효성 검증
    valid, message, preview = ie_manager.validate_rules_json(str(temp_path))

    if not valid:
        temp_path.unlink()
        raise HTTPException(400, message)

    # Import 실행
    success, result_message, stats = ie_manager.import_rules(str(temp_path), merge_mode)

    # 임시 파일 삭제
    if temp_path.exists():
        temp_path.unlink()

    if not success:
        raise HTTPException(500, result_message)

    _reload_rule_engine()

    return {
        "message": result_message,
        "stats": stats,
        "preview": preview
    }


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
