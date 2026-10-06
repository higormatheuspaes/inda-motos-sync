import re
import unicodedata

PALAVRAS_GENERICAS = {"de", "da", "do", "e", "com", "para", "p", "em", "ao", "a", "o", "x", "original", "nacional"}


def _tokens(texto):
    s = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode().upper()
    palavras = re.sub(r"[^A-Z0-9]+", " ", s).split()
    return {p for p in palavras if len(p) > 1 and p.lower() not in PALAVRAS_GENERICAS}


def _pontuacao(tokens_banco, tokens_outro):
    return len(tokens_banco & tokens_outro) / len(tokens_banco) if tokens_banco else 0


def _tem_peca_e_modelo(comum):
    tem_peca = any(t.isalpha() and len(t) >= 4 for t in comum)
    tem_modelo = any(any(c.isdigit() for c in t) for t in comum)
    return tem_peca and tem_modelo


def nomes_conferem(nome_banco, nome_magazord):
    ta, tb = _tokens(nome_banco), _tokens(nome_magazord)
    pontos = _pontuacao(ta, tb)
    comum = ta & tb
    tem_modelo = any(any(c.isdigit() for c in t) for t in comum)
    return pontos >= 0.4 and (tem_modelo or pontos >= 0.75)


def sugerir_codigo(nome_banco, catalogo, excluir):
    ta = _tokens(nome_banco)
    candidatos = []
    for codigo, v in catalogo.items():
        if codigo == excluir:
            continue
        tb = _tokens(v["nome"])
        pontos = _pontuacao(ta, tb)
        if pontos >= 0.5 and _tem_peca_e_modelo(ta & tb):
            candidatos.append((pontos, codigo, v["nome"]))
    if not candidatos:
        return None
    _, codigo, nome = max(candidatos)
    return codigo, nome
