import firebird.driver as firebird
import config

def buscar_produtos_para_sincronizar()
    """
    Retorna lista de dicts: {sku, nome, estoque, preco}

    Query confirmada em cima do schema real do Sisfatura:
      - PRODUTO.FG_SITE = 1         -> produto marcado para ir ao site
      - ESTOQUE (filial matriz)     -> quantidade disponível
      - SUB_TAB_PRECO (CD_TABELA=1) -> preço da tabela "1-PADRAO"
    """

    conn = fb.connect(
        database=config.FB_DATABASE,
        user=config.FB_USER,
        password=config.FB_PASSWORD,
        host=config.FB_HOST,
        port=config.FB_PORT
    )

    cur = conn.cursor()

    # TODO: confirmar código exato da filial matriz (assumido = 1)
    # TODO: confirmar se "disponível" = QT_PROD - QT_PROD_RESERVADA
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
    for row in cur.fetchAll():
        produtos.append({
        "sku": str(row[0]),
            "nome": row[1],
            "estoque": row[2] or 0,
            "preco": float(row[3]) if row[3] is not None else 0.0,
        })

    cur.close()
    conn.close()
    return produtos