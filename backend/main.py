import os
import sys
import threading
import time
import uvicorn
import webview
import multiprocessing

def get_base_dir():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(__file__)

def start_fastapi():
    sys.path.append(get_base_dir())
    from api import app
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="error")

if __name__ == '__main__':
    # CRITICAL: Required for PyInstaller + Uvicorn/Multiprocessing on Windows
    multiprocessing.freeze_support()
    
    # 1. Start FastAPI server in a background daemon thread
    server_thread = threading.Thread(target=start_fastapi, daemon=True)
    server_thread.start()

    # Give server 1 second to bind port
    time.sleep(1.0)

    # 2. Launch pywebview native standalone desktop window
    url = "http://127.0.0.1:8000/"
    
    window = webview.create_window(
        title="EPC Solar Engine Premium",
        url=url,
        width=1440,
        height=900,
        min_size=(1100, 700),
        resizable=True
    )
    
    # 3. Start native GUI window loop
    webview.start()
