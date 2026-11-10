"""독립 알림 창 프로세스. FastAPI/uvicorn을 불러오지 않는다."""
from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main() -> None:
    if len(sys.argv) < 2:
        return
    from backend.desktop_overlay import run_overlay_server

    run_overlay_server(int(sys.argv[1]))


if __name__ == "__main__":
    main()
