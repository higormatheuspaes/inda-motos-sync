import base64
import requests
import config

def _headers():
    credencial = f"{config.MAGAZORD_TOKEN}:{config.MAGAZORD_SENHA}"
    token_b64 = base64.b64encode(credencial.encode()).decode()
    return {
        "Authorization": f"Basic {token_b64}",
        "Content-Type": "application/json",
    }

def atualizar_estoque(sku, quantidade):
    """
        AJUSTAR payload exato conforme doc real (docs-v2.api.magazord.com.br)
        assim que tiver credencial pra testar ao vivo.
    """
    url = f"{config.MAGAZORD_BASE_URL}/estoque"
    payload = {
        "produto": sku,
        "quantidade": quantidade,
    }
    return requests.post(url, json=payload, headers=_headers(), timeout=15)

def atualizar_preco(sku, preco):
    url = f"{config.MAGAZORD_BASE_URL}/preco"
    payload = {
        "produto": sku,
        "precoPor": preco,
    }
    return requests.post(url, json=payload, headers=_headers(), timeout=15)