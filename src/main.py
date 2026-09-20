import logging
import os
import sys

import sync_engine
from gui import App

os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/sync.log", encoding="utf-8"),
        logging.StreamHandler(),
    ],
)


def main():
    if "--sync" in sys.argv:
        sync_engine.executar_sincronizacao()
    else:
        App().mainloop()


if __name__ == "__main__":
    main()
