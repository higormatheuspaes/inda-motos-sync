import json
import os
from datetime import datetime

CAMINHO_STATUS = "data/status.json"

def salvar_status(sucesso, produtos_sincronizados, erros):
    """
    produtos_sincronizados: lista de dicts
        {sku, nome, estoque_antigo, estoque_novo, preco_antigo, preco_novo}
    erros: lista de dicts
        {sku, nome, estoque_antigo, estoque_novo, preco_antigo, preco_novo, mensagem}
    """

    status = {
        "ultima_execucao": datetime.now().isoformat(),
        "sucesso": sucesso,
        "total_produtos": len(produtos_sincronizados),
        "total_erros": len(erros),
        "produtos": produtos_sincronizados[-50:],
        "erros": erros,
    }

    os.makedirs("data", exist_ok=True)
    with open(CAMINHO_STATUS, "w", encoding="utf-8") as f:
        json.dump(status, f, ensure_ascii=False, indent=2)

def carregar_status():
    if not os.path.exists(CAMINHO_STATUS):
        return {
            "ultima_execucao": None,
            "sucesso": None,
            "total_produtos": 0,
            "total_erros": 0,
            "produtos": [],
            "erros": [],
        }
    with open(CAMINHO_STATUS, "r", encoding="utf-8") as f:
        return json.load(f)