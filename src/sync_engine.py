import logging
import db_firebird
import magazord_api
import state_manager
import status_manager
import notifier

LIMITE_VARIACAO_PRECO = 0.20
LIMITE_VARIACAO_ESTOQUE = 0.50


def _motivos_do_item(ref, estoque_novo, preco_novo):
    motivos = []
    if ref.get("preco") and preco_novo is not None:
        variacao = (preco_novo - ref["preco"]) / ref["preco"]
        if abs(variacao) > LIMITE_VARIACAO_PRECO:
            motivos.append(f"preço mudou {variacao:+.0%}")
    estoque_ref = ref.get("estoque")
    if estoque_ref is not None and estoque_ref != 0:
        if estoque_novo == 0:
            motivos.append("estoque zerou")
        elif abs(estoque_novo - estoque_ref) / estoque_ref > LIMITE_VARIACAO_ESTOQUE:
            motivos.append("estoque mudou mais de 50%")
    return motivos


def _ja_igual(ref, produto):
    return (
        ref.get("estoque") == produto["estoque"]
        and ref.get("preco") is not None
        and abs(ref["preco"] - produto["preco"]) < 0.005
    )


def _falhas_http(resp_estoque, resp_preco):
    return [
        f"{rotulo} {resp.status_code}: {' '.join(resp.text.split())[:200]}"
        for rotulo, resp in (("estoque", resp_estoque), ("preço", resp_preco))
        if resp.status_code >= 400
    ]


def _alerta(sku, nome_banco, ref, produto, motivos):
    """Registro informativo de um item que JÁ FOI gravado, mas com variação
    grande o suficiente pra merecer revisão (ver reverter_alerta)."""
    return {
        "sku": sku,
        "nome_banco": nome_banco,
        "nome_magazord": ref["nome"],
        "estoque_antigo": ref.get("estoque"),
        "estoque_novo": produto["estoque"],
        "preco_antigo": ref.get("preco"),
        "preco_novo": produto["preco"],
        "motivos": motivos,
    }


def _gravar(sku, estoque_novo, preco_novo, ref):
    resp_estoque = magazord_api.atualizar_estoque(sku, estoque_novo, criar_registro=ref.get("estoque") is None)
    resp_preco = magazord_api.atualizar_preco(sku, preco_novo)
    return _falhas_http(resp_estoque, resp_preco)


def executar_sincronizacao(on_progress=None):
    """Roda a sincronização e retorna um resumo (usado pela GUI e pelo modo --sync).

    Sincroniza direto pelo SKU, sem conferir se o nome do banco bate com o da
    Magazord. Itens com variação grande de preço/estoque são gravados do
    mesmo jeito, mas entram em "alertas" para revisão (ver reverter_alerta).

    on_progress, se informado, é chamado como on_progress(atual, total) antes
    de processar o primeiro item (atual=0) e após cada item processado.
    """
    logging.debug("Iniciando sincronização")

    produtos = db_firebird.buscar_produtos_para_sincronizar()
    estado_anterior = state_manager.carregar_estado()
    mudancas = state_manager.calcular_mudancas(produtos, estado_anterior)
    catalogo = magazord_api.listar_produtos_magazord()

    logging.debug(f"{len(produtos)} produtos lidos, {len(mudancas)} com mudança")

    total = len(mudancas)
    if on_progress:
        on_progress(0, total)

    erros = []
    sincronizados = []
    alertas = []
    novo_estado = dict(estado_anterior)

    for indice, produto in enumerate(mudancas, start=1):
        sku = produto["sku"]
        nome = produto.get("nome", "")
        ref = catalogo.get(sku, {})
        dados = {
            "sku": sku,
            "nome": nome,
            "estoque_antigo": ref.get("estoque"),
            "estoque_novo": produto["estoque"],
            "preco_antigo": ref.get("preco"),
            "preco_novo": produto["preco"],
        }

        if not ref:
            erros.append({**dados, "mensagem": "SKU não encontrada na Magazord"})
        elif _ja_igual(ref, produto):
            novo_estado[sku] = {"estoque": produto["estoque"], "preco": produto["preco"]}
        else:
            try:
                falhas = _gravar(sku, produto["estoque"], produto["preco"], ref)
                if falhas:
                    erros.append({**dados, "mensagem": " | ".join(falhas)})
                else:
                    sincronizados.append(dados)
                    novo_estado[sku] = {"estoque": produto["estoque"], "preco": produto["preco"]}
                    motivos = _motivos_do_item(ref, produto["estoque"], produto["preco"])
                    if motivos:
                        alertas.append(_alerta(sku, nome, ref, produto, motivos))
            except Exception as e:
                logging.exception(f"Erro ao processar SKU {sku}")
                erros.append({**dados, "mensagem": str(e)})

        if on_progress:
            on_progress(indice, total)

    state_manager.salvar_estado(novo_estado)
    status_manager.salvar_status(
        sucesso=(len(erros) == 0),
        produtos_sincronizados=sincronizados,
        erros=erros,
        alertas=alertas,
    )

    if erros:
        logging.warning(f"{len(erros)} erros encontrados")
    if erros or alertas:
        try:
            notifier.enviar_relatorio(sincronizados, erros, alertas)
        except Exception:
            logging.exception("Falha ao enviar e-mail do relatório de sincronização")

    logging.info(
        f"Sincronização finalizada: {len(sincronizados)} atualizados, {len(erros)} erros, {len(alertas)} alertas"
    )
    return {"sincronizados": sincronizados, "erros": erros, "alertas": alertas}


def tentar_novamente(item):
    """Tenta de novo um item que tinha ficado em erro (SKU não encontrada ou
    falha ao gravar). Reconsulta a Magazord e grava de novo; se a variação
    for grande, entra também em alertas (gravado, mas revisável)."""
    sku = item["sku"]
    nome = item["nome"]
    catalogo = magazord_api.listar_produtos_magazord()
    ref = catalogo.get(sku, {})

    if not ref:
        return "erro", "SKU não encontrada na Magazord"

    status = status_manager.carregar_status()
    restantes_erros = [e for e in status.get("erros", []) if e["sku"] != sku]

    try:
        falhas = _gravar(sku, item["estoque_novo"], item["preco_novo"], ref)
    except Exception as e:
        return "erro", str(e)
    if falhas:
        return "erro", " | ".join(falhas)

    estado = state_manager.carregar_estado()
    estado[sku] = {"estoque": item["estoque_novo"], "preco": item["preco_novo"]}
    state_manager.salvar_estado(estado)

    produtos = status.get("produtos", []) + [{
        "sku": sku,
        "nome": nome,
        "estoque_antigo": ref.get("estoque"),
        "estoque_novo": item["estoque_novo"],
        "preco_antigo": ref.get("preco"),
        "preco_novo": item["preco_novo"],
    }]

    motivos = _motivos_do_item(ref, item["estoque_novo"], item["preco_novo"])
    alertas = status.get("alertas", [])
    if motivos:
        produto = {"estoque": item["estoque_novo"], "preco": item["preco_novo"]}
        alertas = alertas + [_alerta(sku, nome, ref, produto, motivos)]

    status_manager.salvar_status(
        sucesso=not restantes_erros,
        produtos_sincronizados=produtos,
        erros=restantes_erros,
        alertas=alertas,
    )
    logging.info(f"SKU {sku} sincronizado manualmente (tentar de novo)")
    if motivos:
        return "alerta", f"sincronizado, mas com variação grande ({', '.join(motivos)})"
    return "sincronizado", "atualizado com sucesso"


def reverter_alerta(item):
    """Reverte um alerta já sincronizado, voltando aos valores que a Magazord
    tinha antes dessa sincronização, e tira o item da lista de alertas."""
    sku = item["sku"]
    estoque_alvo = item.get("estoque_antigo")
    preco_alvo = item.get("preco_antigo")
    if estoque_alvo is None and preco_alvo is None:
        return False, "não há valores anteriores registrados pra reverter"

    falhas = []
    if estoque_alvo is not None:
        resp = magazord_api.atualizar_estoque(sku, estoque_alvo)
        if resp.status_code >= 400:
            falhas.append(f"estoque {resp.status_code}: {' '.join(resp.text.split())[:200]}")
    if preco_alvo is not None:
        resp = magazord_api.atualizar_preco(sku, preco_alvo)
        if resp.status_code >= 400:
            falhas.append(f"preço {resp.status_code}: {' '.join(resp.text.split())[:200]}")
    if falhas:
        return False, " | ".join(falhas)

    estado = state_manager.carregar_estado()
    item_estado = estado.setdefault(sku, {})
    if estoque_alvo is not None:
        item_estado["estoque"] = estoque_alvo
    if preco_alvo is not None:
        item_estado["preco"] = preco_alvo
    state_manager.salvar_estado(estado)

    status = status_manager.carregar_status()
    restantes = [a for a in status.get("alertas", []) if a["sku"] != sku]
    status_manager.salvar_status(
        sucesso=not status.get("erros"),
        produtos_sincronizados=status.get("produtos", []),
        erros=status.get("erros", []),
        alertas=restantes,
    )
    logging.info(f"SKU {sku} revertido manualmente")
    return True, "revertido"
