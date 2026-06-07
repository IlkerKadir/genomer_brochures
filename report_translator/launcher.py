"""launcher.py — uvicorn'u arka planda başlatır, PyWebView ile gerçek pencere açar."""
import threading
import socket
import time
import uvicorn
import webview
import app as app_module


def _free_port():
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    p = s.getsockname()[1]
    s.close()
    return p


def main():
    port = _free_port()
    t = threading.Thread(
        target=lambda: uvicorn.run(app_module.app, host="127.0.0.1", port=port, log_level="warning"),
        daemon=True)
    t.start()
    time.sleep(1.0)
    webview.create_window("Genomer Rapor Çevirici", f"http://127.0.0.1:{port}",
                          width=1280, height=820)
    webview.start()


if __name__ == "__main__":
    main()
