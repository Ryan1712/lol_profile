import os
import threading
import webbrowser

import uvicorn

HOST = os.getenv("HOST", "0.0.0.0")
PORT = int(os.getenv("PORT", "8000"))


def _open():
    try:
        webbrowser.open(f"http://127.0.0.1:{PORT}/")
    except Exception:
        pass


if __name__ == "__main__":
    # Trên hosting (Render/Codespaces) biến PORT được set sẵn -> không tự mở trình duyệt.
    if not os.getenv("PORT"):
        threading.Timer(1.2, _open).start()
    uvicorn.run("src.app:app", host=HOST, port=PORT, reload=False)
