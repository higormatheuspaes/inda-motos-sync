import json
import os

CAMINHO_ESTADO = "data/estado.json"


def carregar_estado():
    if not os.path.exists(CAMINHO_ESTADO):
        return {}
    with open(CAMINHO_ESTADO, "r", encoding="utf-8") as f:
        return json.load(f)


def salvar_estado(estado):
    os.makedirs("data", exist_ok=True)
    with open(CAMINHO_ESTADO, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def calcular_mudancas(produtos_atuais, estado_anterior):
    """Retorna só os produtos cujo estoque ou preço mudou desde o último envio."""
    mudancas = []
    for p in produtos_atuais:
        sku = p["sku"]
        anterior = estado_anterior.get(sku)
        if (
            anterior is None
            or anterior.get("estoque") != p["estoque"]
            or anterior.get("preco") != p["preco"]
        ):
            mudancas.append(p)
    return mudancas