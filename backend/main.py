import os
import sys
import threading
import time
import uvicorn
import webview
import multiprocessing
import socket
import traceback

# Redirect stdout and stderr to a log file in the same directory as the executable
log_file_path = os.path.join(os.path.dirname(sys.executable), "epc_solar_error.log")
sys.stdout = open(log_file_path, "a")
sys.stderr = open(log_file_path, "a")

def get_base_dir():
    if hasattr(sys, '_MEIPASS'):
        return sys._MEIPASS
    return os.path.dirname(__file__)

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        return s.getsockname()[1]

def wait_for_port(port, timeout=15):
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                s.connect(('127.0.0.1', port))
            return True
        except (ConnectionRefusedError, socket.timeout, OSError):
            time.sleep(0.5)
    return False

def start_fastapi(port):
    try:
        sys.path.append(get_base_dir())
        from api import app
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="error")
    except Exception as e:
        with open(log_file_path, "a") as f:
            f.write(f"FATAL ERROR in FastAPI thread: {e}\n")
            traceback.print_exc(file=f)

if __name__ == '__main__':
    # CRITICAL: Required for PyInstaller + Uvicorn/Multiprocessing on Windows
    multiprocessing.freeze_support()
    
    # Find a free port to avoid EADDRINUSE from any ghost processes
    free_port = get_free_port()

    # 1. Start FastAPI server in a background daemon thread
    server_thread = threading.Thread(target=start_fastapi, args=(free_port,), daemon=True)
    server_thread.start()

    # Wait for server to actually bind the port (up to 15 seconds)
    wait_for_port(free_port, timeout=15)

    # 2. Launch pywebview native standalone desktop window
    url = f"http://127.0.0.1:{free_port}/"
    
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
