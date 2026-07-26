import asyncio
import os
import sys
import time
import traceback

from app.bot import main


if __name__ == "__main__":
    while True:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            raise
        except Exception:
            traceback.print_exc()
            print("Bot stopped after an error. Restarting process in 30 seconds...", flush=True)
            time.sleep(30)
            os.execv(sys.executable, [sys.executable, *sys.argv])
