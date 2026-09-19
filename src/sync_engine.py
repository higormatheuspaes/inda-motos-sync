import logging
import db_firebird
import magazord_api
import state_manager
import status_manager
import notifier

def executar_sincronizacao():
    """Roda a sincronização e retorna um resumo (usado pela GUI e pelo modo --sync)."""
    logging.info("Iniciando sincronização")

    produtos = db_firebird.buscar_produtos_para_sincronizar()
    estado_anterior = state_manager.carregar_estado()
    mudancas = state_manager.calcular_mudancas(produtos, estado_anterior)

    logging.info(f"{len(produtos)} produtos lidos, {len(mudancas)} com mudança")

    erros = []
    sincronizados = []
    novo_estado = dict(estado_anterior)

    for produto in mudancas:
        sku = produto[sku]
        anterior = estado_anterior.get(sku, {})

        try:
            resp_estoque = magazord_api.atualizar_estoque(sku, produto["estoque"])
            resp_preco = magazord_api.atualizar_precos(sku, produto["preco"])

            if resp_estoque.status_code >= 400 or resp_preco.status_code >= 400:
                erros.append({
                    "sku": sku,
                    "mensagem": f"estoque={resp_estoque.status_code} preco={resp_preco.status_code}",
                })
                continue

            sincronizados.append({
                "sku": sku,
                "nome": produto.get("nome", ""),
                "estoque_antigo": anterior.get("estoque"),
                "estoque_novo": produto["estoque"],
                "preco_antigo": anterior.get("preco"),
                "preco_novo": produto["preco"],
            })
            novo_estado[sku] = {"estoque": produto["estoque"], "preco": produto["preco"]}
        except Exception as e:
            logging.exception(f"Erro ao processar SKU {sku}")
            erros.append({"sku": sku, "mensagem": str(e)})

    state_manager.salvar_estado(novo_estado)
    status_manager.salvar_status(
        sucesso=(len(erros) == 0),
        produtos_sincronizados=sincronizados,
        erros=erros,
    )

    if erros:
        logging.warning(f"{len(erros)} erros encontrados")
        notifier.enviar_email_erros(erros)

    logging.info(f"Sincronização finalizada: {len(sincronizados)} produtos, {len(erros)} erros")
    return {"sincronizados": sincronizados, "erros": erros}

