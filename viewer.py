"""
Flask 웹 뷰어 및 API
캡처된 화면을 타임라인으로 보여주고, 태깅 및 통계 기능을 제공합니다.
"""

import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, render_template, jsonify, request, send_from_directory

from database import Database
from utils import ensure_config_exists, get_config_path, resolve_data_path


app = Flask(__name__)

# 설정 파일 확인 및 생성
ensure_config_exists()
config_path = get_config_path()

# 설정 로드
with open(config_path, 'r', encoding='utf-8') as f:
    config = json.load(f)

# 경로 해석 (상대 경로 → 절대 경로)
db_path = resolve_data_path(config['storage']['database_path'])
screenshots_path = resolve_data_path(config['storage']['screenshots_dir'])

# 데이터베이스 초기화
db = Database(str(db_path))

# 카테고리 초기화 (DB가 비어있을 때만 config.json에서 로드)
db.init_categories(config['categories'])

# 스크린샷 디렉토리
screenshots_dir = screenshots_path
screenshots_dir.mkdir(parents=True, exist_ok=True)


# ========== 웹 페이지 라우트 ==========

@app.route('/')
def index():
    """메인 페이지 (타임라인)"""
    return render_template('timeline.html')


@app.route('/stats')
def stats():
    """통계 페이지"""
    return render_template('stats.html')


@app.route('/settings')
def settings():
    """설정 페이지"""
    return render_template('settings.html')


# ========== API 엔드포인트 ==========

@app.route('/api/dates', methods=['GET'])
def get_available_dates():
    """
    캡처된 날짜 목록 반환
    """
    try:
        dates = []
        if screenshots_dir.exists():
            for date_dir in sorted(screenshots_dir.iterdir(), reverse=True):
                if date_dir.is_dir():
                    dates.append(date_dir.name)
        return jsonify({"success": True, "dates": dates})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/captures/<date>', methods=['GET'])
def get_captures_by_date(date):
    """
    특정 날짜의 캡처 목록 반환
    """
    try:
        captures = db.get_captures_by_date(date)

        # 모니터별로 그룹화
        grouped = {}
        for capture in captures:
            timestamp = capture['timestamp']
            if timestamp not in grouped:
                grouped[timestamp] = {
                    'capture_id': None,  # 첫 번째 모니터 ID로 설정될 예정
                    'monitors': {}
                }

            # 첫 번째 모니터의 ID를 대표 capture_id로 사용
            if grouped[timestamp]['capture_id'] is None or capture['monitor_num'] == 1:
                grouped[timestamp]['capture_id'] = capture['id']

            grouped[timestamp]['monitors'][f"m{capture['monitor_num']}"] = {
                "id": capture['id'],
                "filepath": capture['filepath'],
                "monitor_num": capture['monitor_num'],
                "deleted_at": capture.get('deleted_at')  # soft delete 정보 포함
            }

        # 시간순 정렬된 리스트로 변환
        result = []
        for timestamp in sorted(grouped.keys()):
            result.append({
                "timestamp": timestamp,
                "capture_id": grouped[timestamp]['capture_id'],
                "monitors": grouped[timestamp]['monitors']
            })

        return jsonify({"success": True, "captures": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tags/<date>', methods=['GET'])
def get_tags_by_date(date):
    """
    특정 날짜의 태그 목록 반환 (v3.0: JOIN으로 카테고리/활동 상세 정보 포함)
    """
    try:
        tags = db.get_tags_by_date_with_details(date)
        return jsonify({"success": True, "tags": tags})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tags', methods=['POST'])
def add_tag():
    """
    새 태그 추가 (ID 기반 - v3.0)
    """
    try:
        data = request.json
        capture_id = data['capture_id']
        category_id = data['category_id']  # v3.0: INT ID
        activity_id = data['activity_id']  # v3.0: INT ID

        # capture 정보 조회
        capture = db.get_capture_by_id(capture_id)
        if not capture:
            return jsonify({"success": False, "error": "Capture not found"}), 404

        timestamp = datetime.fromisoformat(capture['timestamp'])

        # duration 계산 (config에서)
        duration_min = config['capture']['interval_minutes']

        # 태그 추가 (capture_id 포함, v3.0: category_id, activity_id)
        db.add_tag(timestamp, category_id, activity_id, duration_min, capture_id)

        # 자동 삭제 옵션이 켜져 있으면 이미지 삭제
        if config['storage']['auto_delete_after_tagging']:
            print(f"[AutoDelete] 자동 삭제 시작: capture_id={capture_id}")

            # 같은 timestamp의 모든 파일 경로 조회
            conn = db._get_connection()
            cursor = conn.cursor()
            cursor.execute("""
                SELECT filepath FROM captures
                WHERE datetime(timestamp) = datetime(?)
                AND filepath IS NOT NULL
            """, (timestamp,))

            filepaths = [row['filepath'] for row in cursor.fetchall()]
            conn.close()

            # 파일 삭제
            deleted_count = 0
            for filepath_str in filepaths:
                filepath = Path(filepath_str)
                if filepath.exists():
                    filepath.unlink()
                    deleted_count += 1
                    print(f"[AutoDelete] 파일 삭제: {filepath}")

            # DB에서 soft delete 처리
            db.mark_capture_deleted(capture_id)

            print(f"[AutoDelete] 완료: {deleted_count}개 파일 삭제, DB soft delete 처리")

        return jsonify({"success": True})
    except Exception as e:
        print(f"[Error] Tag creation failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """
    카테고리 목록 반환 (v3.0: activities 포함)
    """
    try:
        categories = db.get_categories()
        return jsonify({"success": True, "categories": categories})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/categories', methods=['POST'])
def create_category():
    """
    카테고리 추가 (v3.0)
    """
    try:
        data = request.json
        name = data.get('name')
        color = data.get('color', '#808080')
        order_index = data.get('order_index', 0)

        if not name:
            return jsonify({"success": False, "error": "Name is required"}), 400

        category_id = db.add_category(name, color, order_index)
        return jsonify({"success": True, "id": category_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/categories/<int:category_id>', methods=['PUT'])
def update_category(category_id):
    """
    카테고리 수정 (v3.0)
    """
    try:
        data = request.json
        name = data.get('name')
        color = data.get('color')
        order_index = data.get('order_index')

        db.update_category(category_id, name, color, order_index)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
def delete_category(category_id):
    """
    카테고리 삭제 (v3.0, ON DELETE RESTRICT)
    """
    try:
        db.delete_category(category_id)
        return jsonify({"success": True})
    except sqlite3.IntegrityError as e:
        # RESTRICT 에러: 태그가 연결되어 있음
        return jsonify({
            "success": False,
            "error": "이 카테고리를 사용하는 태그가 있습니다. 먼저 태그를 삭제하거나 다른 카테고리로 변경하세요."
        }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/categories/<int:category_id>/activities', methods=['POST'])
def create_activity(category_id):
    """
    활동 추가 (v3.0)
    """
    try:
        data = request.json
        name = data.get('name')
        order_index = data.get('order_index', 0)

        if not name:
            return jsonify({"success": False, "error": "Name is required"}), 400

        activity_id = db.add_activity(category_id, name, order_index)
        return jsonify({"success": True, "id": activity_id})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/activities/<int:activity_id>', methods=['PUT'])
def update_activity(activity_id):
    """
    활동 수정 (v3.0)
    """
    try:
        data = request.json
        name = data.get('name')
        order_index = data.get('order_index')

        db.update_activity(activity_id, name, order_index)
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/activities/<int:activity_id>', methods=['DELETE'])
def delete_activity(activity_id):
    """
    활동 삭제 (v3.0, ON DELETE RESTRICT)
    """
    try:
        db.delete_activity(activity_id)
        return jsonify({"success": True})
    except sqlite3.IntegrityError as e:
        # RESTRICT 에러: 태그가 연결되어 있음
        return jsonify({
            "success": False,
            "error": "이 활동을 사용하는 태그가 있습니다. 먼저 태그를 삭제하거나 다른 활동으로 변경하세요."
        }), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/stats/category', methods=['GET'])
def get_category_stats():
    """
    카테고리별 통계 반환 (미분류 포함)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # 태그된 통계
        stats = db.get_category_stats(start_date, end_date)

        # 전체 캡처 시간 계산
        from datetime import datetime, timedelta
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        # 해당 기간의 모든 캡처 조회
        total_captures = 0
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            captures = db.get_captures_by_date(date_str)
            # 모니터별로 중복 제거 (같은 시간의 캡처는 1회로)
            unique_times = set()
            for capture in captures:
                unique_times.add(capture['timestamp'])
            total_captures += len(unique_times)
            current += timedelta(days=1)

        # 전체 시간 = 캡처 수 * 간격
        interval_minutes = config['capture']['interval_minutes']
        total_minutes = total_captures * interval_minutes

        # 태그된 시간 합계
        tagged_minutes = sum(stat['total_minutes'] for stat in stats)

        # 미분류 시간
        untagged_minutes = total_minutes - tagged_minutes

        if untagged_minutes > 0:
            stats.append({
                'category': '미분류',
                'total_minutes': untagged_minutes
            })

        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/stats/activity', methods=['GET'])
def get_activity_stats():
    """
    활동별 통계 반환 (미분류 포함)
    """
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # 태그된 통계
        stats = db.get_activity_stats(start_date, end_date)

        # 카테고리 통계에서 미분류 시간 가져오기
        from datetime import datetime, timedelta
        start = datetime.strptime(start_date, '%Y-%m-%d')
        end = datetime.strptime(end_date, '%Y-%m-%d')

        # 해당 기간의 모든 캡처 조회
        total_captures = 0
        current = start
        while current <= end:
            date_str = current.strftime('%Y-%m-%d')
            captures = db.get_captures_by_date(date_str)
            # 모니터별로 중복 제거
            unique_times = set()
            for capture in captures:
                unique_times.add(capture['timestamp'])
            total_captures += len(unique_times)
            current += timedelta(days=1)

        # 전체 시간 = 캡처 수 * 간격
        interval_minutes = config['capture']['interval_minutes']
        total_minutes = total_captures * interval_minutes

        # 태그된 시간 합계
        tagged_minutes = sum(stat['total_minutes'] for stat in stats)

        # 미분류 시간
        untagged_minutes = total_minutes - tagged_minutes

        if untagged_minutes > 0:
            stats.append({
                'category': '미분류',
                'activity': '태그 안됨',
                'total_minutes': untagged_minutes
            })

        return jsonify({"success": True, "stats": stats})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/screenshots/<path:filename>')
def serve_screenshot(filename):
    """
    스크린샷 이미지 제공
    """
    return send_from_directory(screenshots_dir, filename)


@app.route('/api/captures/delete', methods=['POST'])
def delete_captures():
    """
    선택된 캡처 삭제 (ID 기반, hard delete - DB에서 완전 삭제)
    """
    try:
        data = request.json
        capture_ids = data.get('capture_ids', [])

        if not capture_ids:
            return jsonify({"success": False, "error": "삭제할 항목이 없습니다."}), 400

        deleted_files = 0
        deleted_records = 0

        for capture_id in capture_ids:
            try:
                # 캡처 정보 조회
                capture = db.get_capture_by_id(capture_id)
                if not capture:
                    continue

                timestamp = capture['timestamp']

                # 같은 timestamp의 모든 파일 경로 조회 및 삭제
                conn = db._get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT id, filepath FROM captures
                    WHERE datetime(timestamp) = datetime(?)
                """, (timestamp,))

                rows = cursor.fetchall()

                # 파일 삭제
                for row in rows:
                    filepath = row['filepath']
                    if filepath:
                        filepath_obj = Path(filepath)
                        if filepath_obj.exists():
                            filepath_obj.unlink()
                            deleted_files += 1

                # DB에서 hard delete (같은 timestamp의 모든 모니터)
                cursor.execute("""
                    DELETE FROM captures
                    WHERE datetime(timestamp) = datetime(?)
                """, (timestamp,))

                deleted_records += cursor.rowcount
                conn.commit()
                conn.close()

                print(f"[Delete] capture_id={capture_id}, timestamp={timestamp}: {deleted_files}개 파일, {deleted_records}개 레코드 삭제")

            except Exception as e:
                print(f"[Error] 캡처 삭제 실패 (ID={capture_id}): {e}")
                import traceback
                traceback.print_exc()
                continue

        return jsonify({
            "success": True,
            "deleted_files": deleted_files,
            "deleted_records": deleted_records
        })
    except Exception as e:
        print(f"[Error] Bulk delete failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


# ========== 설정 API ==========

@app.route('/api/status', methods=['GET'])
def get_capture_status():
    """
    현재 캡처 상태 조회
    """
    try:
        capture_instance = app.config.get('capture_instance')
        if not capture_instance:
            return jsonify({"success": False, "error": "캡처 인스턴스를 찾을 수 없습니다."}), 500

        status = {
            "is_running": capture_instance.is_running,
            "is_paused": capture_instance.is_paused,
            "scheduled_stop": app.config.get('scheduled_stop')
        }
        return jsonify({"success": True, "status": status})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/control/pause', methods=['POST'])
def pause_capture():
    """캡처 일시정지"""
    try:
        capture_instance = app.config.get('capture_instance')
        if not capture_instance:
            return jsonify({"success": False, "error": "캡처 인스턴스를 찾을 수 없습니다."}), 500

        capture_instance.pause_capture()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/control/resume', methods=['POST'])
def resume_capture():
    """캡처 재개"""
    try:
        capture_instance = app.config.get('capture_instance')
        if not capture_instance:
            return jsonify({"success": False, "error": "캡처 인스턴스를 찾을 수 없습니다."}), 500

        capture_instance.resume_capture()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/control/capture', methods=['POST'])
def manual_capture():
    """수동 캡처"""
    try:
        capture_instance = app.config.get('capture_instance')
        if not capture_instance:
            return jsonify({"success": False, "error": "캡처 인스턴스를 찾을 수 없습니다."}), 500

        captured_files = capture_instance.capture_all_monitors()
        return jsonify({"success": True, "files": captured_files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/config', methods=['GET'])
def get_config():
    """현재 설정 조회"""
    try:
        return jsonify({"success": True, "config": config})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/config', methods=['POST'])
def update_config():
    """설정 업데이트"""
    try:
        global config
        data = request.json

        # 캡처 설정 업데이트
        if 'interval_minutes' in data:
            config['capture']['interval_minutes'] = data['interval_minutes']
        if 'image_quality' in data:
            config['capture']['image_quality'] = data['image_quality']
        if 'auto_delete_after_tagging' in data:
            config['storage']['auto_delete_after_tagging'] = data['auto_delete_after_tagging']

        # config.json 파일에 저장
        with open('./config.json', 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        # 캡처 인스턴스 설정 업데이트
        capture_instance = app.config.get('capture_instance')
        if capture_instance and 'interval_minutes' in data:
            capture_instance.interval_minutes = data['interval_minutes']
        if capture_instance and 'image_quality' in data:
            capture_instance.image_quality = data['image_quality']

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/scheduled-stop', methods=['POST'])
def set_scheduled_stop():
    """예약 종료 설정"""
    try:
        data = request.json
        stop_time = data.get('stop_time')  # "HH:MM" 형식

        if stop_time:
            app.config['scheduled_stop'] = stop_time
            return jsonify({"success": True, "scheduled_stop": stop_time})
        else:
            return jsonify({"success": False, "error": "stop_time이 필요합니다."}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/scheduled-stop', methods=['DELETE'])
def cancel_scheduled_stop():
    """예약 종료 취소"""
    try:
        app.config['scheduled_stop'] = None
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/storage', methods=['GET'])
def get_storage_info():
    """저장 공간 정보 조회"""
    try:
        # 총 캡처 수 계산
        total_captures = 0
        total_size = 0

        if screenshots_dir.exists():
            for date_dir in screenshots_dir.iterdir():
                if date_dir.is_dir():
                    for img_file in date_dir.glob('*.jpg'):
                        total_captures += 1
                        total_size += img_file.stat().st_size

        # MB로 변환
        total_size_mb = round(total_size / (1024 * 1024), 2)

        return jsonify({
            "success": True,
            "storage": {
                "total_captures": total_captures,
                "total_size_mb": total_size_mb
            }
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/storage/delete-all', methods=['POST'])
def delete_all_images():
    """모든 캡처 이미지 파일 삭제 (DB 레코드와 태그는 유지)"""
    try:
        deleted_count = 0

        if screenshots_dir.exists():
            for date_dir in screenshots_dir.iterdir():
                if date_dir.is_dir():
                    for img_file in date_dir.glob('*.jpg'):
                        img_file.unlink()
                        deleted_count += 1
                    # 빈 디렉토리 삭제
                    if not any(date_dir.iterdir()):
                        date_dir.rmdir()

        # DB에서 모든 filepath를 NULL로 업데이트 (이미지 삭제됨 표시)
        conn = db._get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE captures SET filepath = NULL")
        updated_count = cursor.rowcount
        conn.commit()
        conn.close()

        print(f"[DeleteAll] {deleted_count}개 이미지 파일 삭제, {updated_count}개 DB 레코드 filepath=NULL로 업데이트")

        return jsonify({
            "success": True,
            "deleted_count": deleted_count
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ========== 캐싱 설정 ==========

@app.after_request
def add_cache_headers(response):
    """
    응답에 캐싱 헤더 추가
    - 정적 파일(CSS/JS): 1시간 캐싱
    - HTML 페이지: no-cache (항상 최신 상태)
    - API: no-cache (실시간 데이터)
    """
    # 정적 파일 (CSS, JS)은 긴 캐싱
    if request.path.startswith('/static/'):
        response.headers['Cache-Control'] = 'public, max-age=3600'  # 1시간
        response.headers['Expires'] = (datetime.now() + timedelta(hours=1)).strftime('%a, %d %b %Y %H:%M:%S GMT')

    # API 호출은 캐싱 안 함 (항상 최신 데이터)
    elif request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response.headers['Pragma'] = 'no-cache'
        response.headers['Expires'] = '0'

    # HTML 페이지는 짧은 캐싱 (빠른 전환)
    elif request.path in ['/', '/stats', '/settings'] or request.path.endswith('.html'):
        response.headers['Cache-Control'] = 'public, max-age=300'  # 5분

    return response


# ========== 메인 실행 ==========

def run_viewer(port=None):
    """
    Flask 뷰어 실행

    Args:
        port: 포트 번호 (기본값: config.json의 설정 사용)
    """
    if port is None:
        port = config['viewer']['port']

    print(f"\n[Viewer] 웹 뷰어 시작: http://localhost:{port}")
    print(f"[Viewer] Ctrl+C를 눌러 중단할 수 있습니다.\n")

    app.run(host='0.0.0.0', port=port, debug=False)


if __name__ == "__main__":
    run_viewer()
