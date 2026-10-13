import logging
import db_firebird
import magazord_api
import state_manager
import status_manager
import notifier
from conferencia import nomes_conferem, sugerir_codigo

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


def _mensagem_nome_divergente(sku, nome, nome_magazord, catalogo):
    msg = f"nome não confere com o código na Magazord (\"{nome_magazord}\")"
    sugestao = sugerir_codigo(nome, catalogo, excluir=sku)
    if sugestao:
        codigo, nome_sugerido = sugestao
        msg += f". Mais parecido: código {codigo}, \"{nome_sugerido}\""
    return msg


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


def _pendente(sku, nome_banco, ref, produto, motivos):
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


def executar_sincronizacao(on_progress=None):
    """Roda a sincronização e retorna um resumo (usado pela GUI e pelo modo --sync).

    Itens com alerta de variação não são gravados: ficam em "alertas" para
    aprovação individual na tela (ver sincronizar_alerta).

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
        elif not nomes_conferem(nome, ref["nome"]):
            mensagem = _mensagem_nome_divergente(sku, nome, ref["nome"], catalogo)
            erros.append({**dados, "mensagem": mensagem})
        elif _ja_igual(ref, produto):
            novo_estado[sku] = {"estoque": produto["estoque"], "preco": produto["preco"]}
        else:
            motivos = _motivos_do_item(ref, produto["estoque"], produto["preco"])
            if motivos:
                alertas.append(_pendente(sku, nome, ref, produto, motivos))
            else:
                try:
                    resp_estoque = magazord_api.atualizar_estoque(
                        sku, produto["estoque"], criar_registro=ref.get("estoque") is None
                    )
                    resp_preco = magazord_api.atualizar_preco(sku, produto["preco"])
                    falhas = _falhas_http(resp_estoque, resp_preco)
                    if falhas:
                        erros.append({**dados, "mensagem": " | ".join(falhas)})
                    else:
                        sincronizados.append(dados)
                        novo_estado[sku] = {"estoque": produto["estoque"], "preco": produto["preco"]}
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
        f"Sincronização finalizada: {len(sincronizados)} atualizados, {len(erros)} erros, {len(alertas)} aguardando aprovação"
    )
    return {"sincronizados": sincronizados, "erros": erros, "alertas": alertas}


def sincronizar_alerta(item):
    """Grava um item que estava aguardando aprovação e o tira da lista de alertas."""
    sku = item["sku"]
    resp_estoque = magazord_api.atualizar_estoque(
        sku, item["estoque_novo"], criar_registro=item.get("estoque_antigo") is None
    )
    resp_preco = magazord_api.atualizar_preco(sku, item["preco_novo"])
    falhas = _falhas_http(resp_estoque, resp_preco)
    if falhas:
        return False, " | ".join(falhas)

    estado = state_manager.carregar_estado()
    estado[sku] = {"estoque": item["estoque_novo"], "preco": item["preco_novo"]}
    state_manager.salvar_estado(estado)

    status = status_manager.carregar_status()
    produtos = status.get("produtos", []) + [{
        "sku": sku,
        "nome": item["nome_banco"],
        "estoque_antigo": item["estoque_antigo"],
        "estoque_novo": item["estoque_novo"],
        "preco_antigo": item["preco_antigo"],
        "preco_novo": item["preco_novo"],
    }]
    restantes = [a for a in status.get("alertas", []) if a["sku"] != sku]
    status_manager.salvar_status(
        sucesso=not status.get("erros"),
        produtos_sincronizados=produtos,
        erros=status.get("erros", []),
        alertas=restantes,
    )
    logging.info(f"SKU {sku} aprovado e sincronizado manualmente")
    return True, "sincronizado"


def tentar_novamente(item):
    """Tenta de novo um item que tinha ficado em erro (SKU não encontrada ou nome
    divergente). Reconsulta a Magazord: se continuar bloqueado, devolve o novo
    motivo; se a variação for grande, vira alerta; senão grava normalmente.

    Retorna (resultado, mensagem), onde resultado é "sincronizado", "alerta" ou "erro".
    """
    sku = item["sku"]
    nome = item["nome"]
    catalogo = magazord_api.listar_produtos_magazord()
    ref = catalogo.get(sku, {})

    if not ref:
        return "erro", "SKU não encontrada na Magazord"
    if not nomes_conferem(nome, ref["nome"]):
        return "erro", _mensagem_nome_divergente(sku, nome, ref["nome"], catalogo)

    status = status_manager.carregar_status()
    restantes_erros = [e for e in status.get("erros", []) if e["sku"] != sku]

    motivos = _motivos_do_item(ref, item["estoque_novo"], item["preco_novo"])
    if motivos:
        produto = {"estoque": item["estoque_novo"], "preco": item["preco_novo"]}
        alertas = status.get("alertas", []) + [_pendente(sku, nome, ref, produto, motivos)]
        status_manager.salvar_status(
            sucesso=not restantes_erros,
            produtos_sincronizados=status.get("produtos", []),
            erros=restantes_erros,
            alertas=alertas,
        )
        return "alerta", f"nome confere agora, mas com variação grande ({', '.join(motivos)}). Foi para a aba Alertas"

    resp_estoque = magazord_api.atualizar_estoque(
        sku, item["estoque_novo"], criar_registro=ref.get("estoque") is None
    )
    resp_preco = magazord_api.atualizar_preco(sku, item["preco_novo"])
    falhas = _falhas_http(resp_estoque, resp_preco)
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
    status_manager.salvar_status(
        sucesso=not restantes_erros,
        produtos_sincronizados=produtos,
        erros=restantes_erros,
        alertas=status.get("alertas", []),
    )
    logging.info(f"SKU {sku} corrigido e sincronizado manualmente")
    return "sincronizado", "atualizado com sucesso"
