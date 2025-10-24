"""
Flask 웹 뷰어 및 API
캡처된 화면을 타임라인으로 보여주고, 태깅 및 통계 기능을 제공합니다.
"""

import json
import os
from datetime import datetime, timedelta
from pathlib import Path

from flask import Flask, render_template, jsonify, request, send_from_directory

from database import Database


app = Flask(__name__)

# 설정 로드
with open('./config.json', 'r', encoding='utf-8') as f:
    config = json.load(f)

# 데이터베이스 초기화
db = Database(config['storage']['database_path'])

# 스크린샷 디렉토리
screenshots_dir = Path(config['storage']['screenshots_dir'])


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
                grouped[timestamp] = {}
            grouped[timestamp][f"m{capture['monitor_num']}"] = {
                "id": capture['id'],
                "filepath": capture['filepath'],
                "monitor_num": capture['monitor_num']
            }

        # 시간순 정렬된 리스트로 변환
        result = []
        for timestamp in sorted(grouped.keys()):
            result.append({
                "timestamp": timestamp,
                "monitors": grouped[timestamp]
            })

        return jsonify({"success": True, "captures": result})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tags/<date>', methods=['GET'])
def get_tags_by_date(date):
    """
    특정 날짜의 태그 목록 반환
    """
    try:
        tags = db.get_tags_by_date(date)
        return jsonify({"success": True, "tags": tags})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/tags', methods=['POST'])
def add_tag():
    """
    새 태그 추가
    """
    try:
        data = request.json
        start_time = datetime.fromisoformat(data['start_time'])
        end_time = datetime.fromisoformat(data['end_time'])
        category = data['category']
        activity = data['activity']

        # 지속 시간 계산 (분)
        duration_min = int((end_time - start_time).total_seconds() / 60)

        # 태그 추가
        db.add_tag(start_time, category, activity, duration_min)

        # 자동 삭제 옵션이 켜져 있으면 이미지 삭제
        if config['storage']['auto_delete_after_tagging']:
            print(f"[AutoDelete] 자동 삭제 시작")
            print(f"[AutoDelete] 태그 저장된 시간 (UTC): {start_time}")

            # UTC 시간을 로컬 시간으로 변환
            # start_time이 timezone-aware면 로컬 시간으로 변환
            if start_time.tzinfo is not None:
                # UTC를 로컬 시간으로 변환 (타임존 제거)
                import datetime as dt
                local_time = start_time.replace(tzinfo=dt.timezone.utc).astimezone(tz=None).replace(tzinfo=None)
                print(f"[AutoDelete] 로컬 시간으로 변환: {local_time}")
            else:
                local_time = start_time
                print(f"[AutoDelete] 이미 로컬 시간: {local_time}")

            # DB에서 이 태그와 같은 시간의 캡처를 찾아서 삭제
            conn = db._get_connection()
            cursor = conn.cursor()

            # DB에 어떤 timestamp들이 있는지 확인
            cursor.execute("SELECT timestamp FROM captures ORDER BY timestamp DESC LIMIT 5")
            recent_captures = cursor.fetchall()
            print(f"[AutoDelete] DB의 최근 캡처 5개:")
            for rc in recent_captures:
                print(f"  - {rc[0]}")

            # 로컬 시간으로 captures 찾기 (이미 DELETED인 것은 제외)
            cursor.execute("SELECT id, timestamp, filepath FROM captures WHERE datetime(timestamp) = datetime(?) AND filepath != 'DELETED'", (local_time,))
            captures = cursor.fetchall()

            print(f"[AutoDelete] 매칭된 캡처 개수: {len(captures)}")

            # 매칭 안 되면 직접 비교 시도
            if len(captures) == 0:
                print(f"[AutoDelete] datetime() 매칭 실패, 직접 비교 시도")
                cursor.execute("SELECT id, timestamp, filepath FROM captures WHERE timestamp = ? AND filepath != 'DELETED'", (local_time,))
                captures = cursor.fetchall()
                print(f"[AutoDelete] 직접 비교 결과: {len(captures)}개")

            # 파일 삭제 및 DB filepath를 'DELETED'로 변경
            deleted_count = 0
            for capture in captures:
                capture_id = capture[0]
                capture_timestamp = capture[1]
                filepath = Path(capture[2])
                print(f"[AutoDelete] 처리 중: ID={capture_id}, timestamp={capture_timestamp}, file={filepath}")

                if filepath.exists():
                    filepath.unlink()
                    deleted_count += 1
                    print(f"[Delete] 파일 삭제됨: {filepath}")
                else:
                    print(f"[Warning] 파일 없음: {filepath}")

            # DB에서 filepath를 'DELETED'로 업데이트 (레코드는 유지)
            if len(captures) > 0:
                cursor.execute("UPDATE captures SET filepath = 'DELETED' WHERE datetime(timestamp) = datetime(?)", (local_time,))
                conn.commit()
                print(f"[AutoDelete] DB에서 {len(captures)}개 레코드의 filepath를 'DELETED'로 업데이트")

            conn.close()

            print(f"[AutoDelete] 완료: 이미지 파일 {deleted_count}개 삭제 (DB 레코드 유지, filepath='DELETED')")

        return jsonify({"success": True})
    except Exception as e:
        print(f"[Error] Tag creation failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/categories', methods=['GET'])
def get_categories():
    """
    카테고리 목록 반환
    """
    try:
        categories = db.get_categories()
        return jsonify({"success": True, "categories": categories})
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
    선택된 캡처 삭제 (이미지 파일 + DB 레코드)
    """
    try:
        data = request.json
        timestamps = data.get('timestamps', [])

        if not timestamps:
            return jsonify({"success": False, "error": "삭제할 항목이 없습니다."}), 400

        deleted_count = 0

        for timestamp_str in timestamps:
            try:
                # 타임스탬프로 DB에서 캡처 정보 조회
                timestamp = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                date_str = timestamp.strftime("%Y-%m-%d")

                # DB에서 해당 타임스탬프의 모든 모니터 캡처 조회
                captures = db.get_captures_by_date(date_str)

                for capture in captures:
                    if capture['timestamp'] == timestamp_str:
                        # 파일 삭제
                        filepath = Path(capture['filepath'])
                        if filepath.exists():
                            filepath.unlink()
                            deleted_count += 1

                # DB에서 레코드 삭제
                conn = db._get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM captures WHERE timestamp = ?", (timestamp_str,))
                conn.commit()
                conn.close()

            except Exception as e:
                print(f"[Error] 캡처 삭제 실패 ({timestamp_str}): {e}")
                continue

        return jsonify({
            "success": True,
            "deleted_count": deleted_count
        })
    except Exception as e:
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
