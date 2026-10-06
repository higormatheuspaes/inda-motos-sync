import base64
import requests
import config

# Documentação: https://docs-v2.api.magazord.com.br/
TIPO_ESTOQUE_FISICO = 1
OPERACAO_AJUSTE = 0


def _headers():
    credencial = f"{config.MAGAZORD_TOKEN}:{config.MAGAZORD_SENHA}"
    token_b64 = base64.b64encode(credencial.encode()).decode()
    return {
        "Authorization": f"Basic {token_b64}",
        "Content-Type": "application/json",
    }


def _url(caminho):
    return f"{config.MAGAZORD_BASE_URL.rstrip('/')}/api{caminho}"


def _exigir(valor, nome):
    if not valor:
        raise RuntimeError(f"{nome} não configurado no .env")
    return valor


def _get(caminho, params):
    resp = requests.get(_url(caminho), params=params, headers=_headers(), timeout=60)
    resp.raise_for_status()
    return resp.json()


def listar_produtos_magazord():
    tabela = _exigir(config.MAGAZORD_TABELA_PRECO, "MAGAZORD_TABELA_PRECO")
    deposito = _exigir(config.MAGAZORD_DEPOSITO, "MAGAZORD_DEPOSITO")
    precos = _get("/v1/listPreco", {"tabelaPreco": tabela, "limit": 5000})
    estoques = _get("/v1/listEstoque", {"limit": 5000})
    for resp in (precos, estoques):
        if resp["total"] > len(resp["data"]):
            raise RuntimeError("listagem da Magazord incompleta; sincronização cancelada")

    catalogo = {}
    for p in precos["data"]:
        preco = p.get("precoVenda")
        catalogo[p["produto"]] = {
            "nome": p["produtoNome"],
            "preco": float(preco) if preco is not None else None,
            "estoque": None,
        }
    for e in estoques["data"]:
        if e["deposito"] != deposito:
            continue
        item = catalogo.setdefault(e["produto"], {"nome": e["descricaoProduto"], "preco": None, "estoque": None})
        item["estoque"] = int(e["quantidadeFisica"] or 0)
    return catalogo


def atualizar_estoque(sku, quantidade):
    """POST /v1/estoque: ajusta o estoque físico do produto para a quantidade informada."""
    payload = {
        "produto": sku,
        "deposito": _exigir(config.MAGAZORD_DEPOSITO, "MAGAZORD_DEPOSITO"),
        "quantidade": int(quantidade),
        "tipo": TIPO_ESTOQUE_FISICO,
        "tipoOperacao": OPERACAO_AJUSTE,
    }
    return requests.post(_url("/v1/estoque"), json=payload, headers=_headers(), timeout=15)


def atualizar_preco(sku, preco):
    """POST /v1/preco: o corpo é uma lista (máx. 100 itens); aqui vai um item por chamada."""
    payload = [{
        "produto": sku,
        "tabelaPreco": _exigir(config.MAGAZORD_TABELA_PRECO, "MAGAZORD_TABELA_PRECO"),
        "precoVenda": float(preco),
    }]
    return requests.post(_url("/v1/preco"), json=payload, headers=_headers(), timeout=15)
