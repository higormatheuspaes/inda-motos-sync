import logging
import os

import fdb
import config


def _incluir_pasta_do_cliente_no_path():
    # o fbclient.dll do Firebird 3+/4 depende de DLLs da própria pasta dele
    if not config.FB_CLIENT_LIBRARY:
        return
    pasta = os.path.dirname(config.FB_CLIENT_LIBRARY)
    caminhos = os.environ.get("PATH", "").split(os.pathsep)
    if pasta and pasta not in caminhos:
        os.environ["PATH"] = pasta + os.pathsep + os.environ.get("PATH", "")


def buscar_produtos_para_sincronizar():
    dsn = f"{config.FB_HOST}/{config.FB_PORT}:{config.FB_DATABASE}"
    _incluir_pasta_do_cliente_no_path()

    try:
        conn = fdb.connect(
            dsn=dsn,
            user=config.FB_USER,
            password=config.FB_PASSWORD,
            charset=config.FB_CHARSET,
            fb_library_name=config.FB_CLIENT_LIBRARY,
        )
    except fdb.DatabaseError:
        cliente = fdb.load_api(config.FB_CLIENT_LIBRARY).client_library_name
        logging.error(
            "Falha ao conectar em %s (usuário %s, charset %s) usando o cliente Firebird %s",
            dsn, config.FB_USER, config.FB_CHARSET, cliente,
        )
        raise
    cur = conn.cursor()

    query = """
        SELECT
            p.CD_REF,
            p.DS_PROD,
            (e.QT_PROD - COALESCE(e.QT_PROD_RESERVADA, 0)) AS ESTOQUE,
            stp.VL_VENDA AS PRECO
        FROM PRODUTO p
        LEFT JOIN ESTOQUE e ON e.CD_REF = p.CD_REF AND e.CD_FILIAL = 1
        LEFT JOIN SUB_TAB_PRECO stp ON stp.CD_REF = p.CD_REF AND stp.CD_TABELA = 1
        WHERE p.FG_SITE = 1
    """
    cur.execute(query)

    produtos = []
    for row in cur.fetchall():
        produtos.append({
            "sku": str(row[0]),
            "nome": row[1],
            "estoque": int(row[2]) if row[2] is not None else 0,
            "preco": float(row[3]) if row[3] is not None else 0.0,
        })

    cur.close()
    conn.close()
    return produtos