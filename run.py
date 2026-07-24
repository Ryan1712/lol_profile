import threading
import webbrowser

import uvicorn

HOST = "127.0.0.1"
PORT = 8000


def _open():
    webbrowser.open(f"http://{HOST}:{PORT}/")


if __name__ == "__main__":
    threading.Timer(1.2, _open).start()
    uvicorn.run("src.app:app", host=HOST, port=PORT, reload=False)
