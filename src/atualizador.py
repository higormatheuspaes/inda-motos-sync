import json
import logging
import os
import subprocess
import sys
import urllib.request

REPO = "higormatheuspaes/inda-motos-sync"
URL_RELEASE = f"https://api.github.com/repos/{REPO}/releases/tags/latest"
ARQUIVO_VERSAO = "versao.txt"
NOME_EXE = "sync_inda_motos.exe"
NOME_EXE_NOVO = "sync_inda_motos.exe.novo"
NOME_SCRIPT_TROCA = "_aplicar_atualizacao.bat"


def versao_local():
    if not os.path.exists(ARQUIVO_VERSAO):
        return None
    with open(ARQUIVO_VERSAO, "r", encoding="ascii") as f:
        return f.read().strip()


def _info_remota():
    req = urllib.request.Request(URL_RELEASE, headers={"User-Agent": "inda-motos-sync-updater"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        dados = json.load(resp)
    assets = {a["name"]: a["browser_download_url"] for a in dados.get("assets", [])}
    if "versao.txt" not in assets or "sync_inda_motos_standalone.exe" not in assets:
        return None
    with urllib.request.urlopen(assets["versao.txt"], timeout=15) as resp:
        versao_remota = resp.read().decode("ascii").strip()
    return versao_remota, assets["sync_inda_motos_standalone.exe"]


def verificar_atualizacao():
    """Retorna (versao_remota, url_exe) se houver uma versão nova, ou None.

    Na primeira execução (sem versao.txt local ainda) só grava a versão
    atual como referência, sem disparar atualização — presume-se que o
    .exe já instalado é a versão corrente.
    """
    try:
        info = _info_remota()
    except Exception:
        logging.exception("Falha ao verificar atualização")
        return None
    if info is None:
        return None

    versao_remota, url_exe = info
    versao_atual = versao_local()
    if versao_atual is None:
        with open(ARQUIVO_VERSAO, "w", encoding="ascii") as f:
            f.write(versao_remota)
        return None
    if versao_remota == versao_atual:
        return None
    return versao_remota, url_exe


def aplicar_atualizacao(versao_remota, url_exe, argumentos_relancar=()):
    """Baixa o .exe novo e prepara a troca. Quem chamou precisa encerrar o
    processo atual logo em seguida (a troca só acontece depois que o .exe
    atual for fechado, por isso o script de troca espera alguns segundos)."""
    req = urllib.request.Request(url_exe, headers={"User-Agent": "inda-motos-sync-updater"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        conteudo = resp.read()
    with open(NOME_EXE_NOVO, "wb") as f:
        f.write(conteudo)

    with open(ARQUIVO_VERSAO, "w", encoding="ascii") as f:
        f.write(versao_remota)

    argumentos = " ".join(argumentos_relancar)
    script = (
        "@echo off\r\n"
        "timeout /t 2 /nobreak >nul\r\n"
        f'move /y "{NOME_EXE_NOVO}" "{NOME_EXE}"\r\n'
        f'start "" "{NOME_EXE}" {argumentos}\r\n'
        'del "%~f0"\r\n'
    )
    with open(NOME_SCRIPT_TROCA, "w", encoding="ascii") as f:
        f.write(script)

    if sys.platform == "win32":
        flags = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        flags = 0
    caminho_script = os.path.abspath(NOME_SCRIPT_TROCA)
    subprocess.Popen(
        ["cmd", "/c", caminho_script],
        creationflags=flags,
        close_fds=True,
        cwd=os.getcwd(),
    )
