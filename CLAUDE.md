# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

ScreenCapture is a personal activity tracking tool that automatically captures screenshots at regular intervals and provides a web-based viewer for reviewing, tagging, and analyzing daily computer usage patterns. All data is stored locally for privacy.

## Architecture

**Multi-threaded Design:**
- `run.py` orchestrates all components via threading
- Main thread runs the system tray (pystray) - blocking
- Background threads: capture loop, Flask web server, scheduled stop checker, browser opener
- Capture instance is shared between threads via `app.config['capture_instance']`

**Core Modules:**
- `capture.py` - ScreenCapture class handles periodic multi-monitor screenshots (mss + PIL)
- `viewer.py` - Flask app serving web UI and REST API endpoints
- `database.py` - Database class wraps SQLite operations (captures, tags, categories tables)
- `run.py` - Entry point that starts all threads and system tray

**Data Flow:**
1. Capture: mss.grab() → PIL → JPEG → filesystem + DB insert
2. Tagging: User selects category/activity → POST /api/tags → DB insert → optional image deletion
3. Stats: GET /api/stats → DB query (aggregation) → calculate "untagged" time → JSON response

## Running the Application

**Start everything (recommended):**
```bash
python run.py
```
This starts the capture loop, Flask server (port 5000), system tray icon, and opens browser automatically.

**Individual components (for debugging):**
```bash
# Terminal 1 - capture only
python capture.py

# Terminal 2 - web viewer only
python viewer.py
```

**Dependencies:**
```bash
pip install -r requirements.txt
```

## Key Implementation Details

**Multi-Monitor Handling:**
- Each monitor is saved as a separate file: `HH-MM-SS_m1.jpg`, `HH-MM-SS_m2.jpg`
- Web UI groups by timestamp and displays monitors side-by-side
- capture.py:121-186 implements capture_all_monitors()

**Screen Lock Detection:**
- Two-layer defense: Windows API check (is_screen_locked) + black screen detection (is_black_screen)
- If ANY monitor is locked/black, entire capture cycle is skipped
- Prevents capturing lock screens for privacy
- See capture.py:21-82

**Auto-Delete After Tagging:**
- Controlled by config.json: `storage.auto_delete_after_tagging`
- When enabled, POST /api/tags triggers database.get_captures_by_time_range() → os.remove() → database.delete_captures_by_time_range()
- Tags remain in DB even after images are deleted

**Untagged Time Calculation:**
- Total time = (number of captures) × (interval_minutes)
- Tagged time = sum of all tag durations
- Untagged time = total - tagged
- Displayed as "미분류" category in stats
- See viewer.py for implementation in get_category_stats endpoint

**Scheduled Stop:**
- User sets time in settings (HH:MM format)
- Stored in app.config['scheduled_stop']
- check_scheduled_stop thread (run.py:117-134) syncs to capture_instance.scheduled_stop
- Capture loop checks every iteration (capture.py:198-203)

## Database Schema

**captures** - Screenshot metadata
- timestamp (DATETIME), monitor_num (INTEGER), filepath (TEXT)
- Index on timestamp

**tags** - Activity logs
- timestamp (DATETIME - start time), category (TEXT), activity (TEXT), duration_min (INTEGER)
- Index on timestamp

**categories** - Category definitions from config.json
- name (TEXT), color (TEXT), activities (TEXT - JSON array)

## Configuration

Edit `config.json` to change:
- `capture.interval_minutes` - Screenshot interval (default: 3)
- `capture.image_quality` - JPEG quality 50-100 (default: 50)
- `storage.auto_delete_after_tagging` - Auto-delete images after tagging (default: true)
- `viewer.port` - Flask server port (default: 5000)
- `categories` - Activity categories and colors

## API Endpoints

**Captures:**
- GET /api/dates - List available dates
- GET /api/captures/<date> - Get captures for date (grouped by timestamp)
- GET /screenshots/<path> - Serve image files

**Tags:**
- GET /api/tags/<date> - Get tags for date
- POST /api/tags - Add new tag (body: timestamp, category, activity, duration_min)
- GET /api/categories - Get all categories

**Stats:**
- GET /api/stats/category?start_date=&end_date= - Category stats (includes untagged)
- GET /api/stats/activity?start_date=&end_date= - Activity stats (includes untagged)

**Control:**
- GET /api/status - Current capture status (running/paused)
- POST /api/control/pause - Pause capture
- POST /api/control/resume - Resume capture
- POST /api/control/capture - Trigger manual capture
- GET /api/config - Get current config
- POST /api/config - Update config
- POST /api/scheduled-stop - Set scheduled stop time
- DELETE /api/scheduled-stop - Cancel scheduled stop

**Storage:**
- GET /api/storage - Storage info (total captures, size)
- POST /api/storage/delete-all - Delete all images

## Common Development Tasks

**Add new activity category:**
1. Edit config.json → add to categories array
2. Restart application (categories table is reinitialized on startup)

**Change capture interval:**
1. Edit config.json → capture.interval_minutes
2. OR use Settings page in web UI → POST /api/config

**Debug capture issues:**
- Run `python capture.py` standalone to see console output
- Check is_screen_locked() and is_black_screen() logic in capture.py

**Modify database schema:**
1. Edit Database._create_tables() in database.py
2. Delete data/activity.db to recreate (WARNING: loses all data)
3. OR write migration code to alter existing tables

## Project Constraints

- Windows-only (uses ctypes.windll for screen lock detection)
- Python 3.8+
- All data stored locally (no cloud sync)
- Flask binds to 0.0.0.0:5000 (accessible on local network)
- System tray requires GUI environment (won't work in headless mode)
