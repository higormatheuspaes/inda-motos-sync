import logging
import os
import sys

import atualizador
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
        info = atualizador.verificar_atualizacao()
        if info:
            versao, url = info
            logging.info(f"Atualização encontrada ({versao}); aplicando antes de sincronizar")
            atualizador.aplicar_atualizacao(versao, url, argumentos_relancar=["--sync"])
            return
        sync_engine.executar_sincronizacao()
    else:
        App().mainloop()


if __name__ == "__main__":
    main()
