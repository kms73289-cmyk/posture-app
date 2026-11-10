# 바른자세 — 실행 방법

분석은 Python(MediaPipe)에서 수행하고, UI는 React가 FastAPI와 REST/WebSocket/MJPEG로 통신합니다.

## 사전 요구

- Python 3.10+ (기존 `requirements.txt` + FastAPI)
- Node.js 18+

## 의존성

프로젝트 루트에서:

```bash
pip install -r requirements.txt
cd frontend
npm install
```

## 개발 실행 (두 프로세스)

터미널 1 — API (포트 8000)

```bash
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000 --reload-exclude frontend --timeout-graceful-shutdown 3
```

`--reload-exclude frontend` 가 없으면 UI 파일 저장 때 서버가 재시작되며, 열린 WebSocket 때문에 API가 멈출 수 있습니다.

터미널 2 — Vite (포트 5173, `/api`·`/ws`를 8000으로 프록시)

```bash
cd frontend
npm run dev
```

브라우저에서 `http://127.0.0.1:5173` 을 엽니다.

## 배포 (한 포트)

```bash
cd frontend
npm run build
cd ..
uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

`frontend/dist`가 있으면 FastAPI가 UI를 같이 서빙합니다. `http://127.0.0.1:8000`

## 데이터 위치

- 기록: `~/.posture_app/posture_data_v2.json`
- 알림 사진: `~/.posture_app/alert_images/`
- 설정: `~/.posture_app/app_settings.json`

기존 tkinter 앱(`python posture.py`)은 그대로 둘 수 있습니다. 동시에 카메라를 쓰면 한쪽이 실패할 수 있습니다.

## 추가한 패키지

- Python: `fastapi`, `uvicorn[standard]`
- 프론트: React 18, Vite, TypeScript, React Router, TanStack Query, Zustand, Tailwind, recharts, lucide-react, pretendard
