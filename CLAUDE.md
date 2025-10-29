# Activity Tracker V2

## 프로젝트 소개

PC 활동을 실시간 추적하여 태그별로 자동 분류하고 통계를 시각화하는 개인용 데스크톱 애플리케이션.

**핵심 기능:**
- Windows 활성 창 자동 감지 (2초 간격)
- Chrome URL 추적 (WebSocket 기반 확장 프로그램)
- 화면 잠금/idle 상태 감지
- 우선순위 기반 자동 태그 분류
- 대시보드/타임라인 UI (PyQt6)
- 시스템 트레이 백그라운드 실행

**기술 스택:**
- Backend: Python, SQLite (WAL), ctypes, psutil, websockets
- Frontend: PyQt6, matplotlib
- Chrome Extension: Manifest V3

---

## 아키텍처

**상세한 시스템 구조, 모듈 설명, 데이터 흐름은 `ARCHITECTURE.md` 참고**

---

## 대화 스타일 가이드

Never compliment me or be affirming excessively (like saying "You're absolutely right!" etc). Criticize my ideas if it's actually need to be critiqued, ask clarifying questions for a much better and precise accuracy answer if you're unsure about my question, and give me funny insults when you found I did any mistakes.