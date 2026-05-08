import os
import sys
import webbrowser
import threading
import time
import logging
import uvicorn
from app.core.config import PORT, ENVIRONMENT

def open_browser(port: int) -> None:
    """Open the default web browser after a short delay."""
    time.sleep(2)
    url = f"http://localhost:{port}"
    webbrowser.open(url)
    logging.getLogger("dsa.main").info("Browser opened: %s", url)

def main() -> None:
    """Start the DSA AutoGrader server and open browser automatically."""
    print("\n" + "=" * 60)
    print("  DSA AutoGrader")
    print("  Starting server...")
    print("=" * 60)
    print(f"\n  URL:  http://localhost:{PORT}")
    print(f"  Docs: http://localhost:{PORT}/docs")
    print("\n  Browser will open automatically...")
    print("  Press Ctrl+C to stop the server.\n")

    # Launch browser in a background daemon thread
    browser_thread = threading.Thread(
        target=open_browser,
        args=(PORT,),
        daemon=True,
    )
    browser_thread.start()

    # Start uvicorn server
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=PORT,
        reload=(ENVIRONMENT == "development"),
        log_level="info",
        access_log=True,
    )


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nServer stopped by user.")
        sys.exit(0)
    except Exception as exc:
        print(f"\nStartup error: {exc}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
