import uvicorn
import os
import sys
import webbrowser
import threading
import time

# Add backend directory to sys.path so that 'app.main' can be resolved
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_dir)

def open_browser():
    time.sleep(1.5)
    print("\n[*] Auto-opening browser: http://127.0.0.1:8000/login/")
    webbrowser.open("http://127.0.0.1:8000/login/")

if __name__ == "__main__":
    print("[*] Starting Unified DSA AutoGrader Enterprise (FastAPI + Next.js)")
    print("[*] Login page: http://127.0.0.1:8000/login/")
    print("[*] Dashboard will be available at http://127.0.0.1:8000")
    
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True, reload_dirs=[backend_dir])
