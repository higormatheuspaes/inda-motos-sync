import html
import os
import smtplib
from datetime import datetime
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import config

COR_FUNDO = "#f4f6f8"
COR_CARD = "#ffffff"
COR_TEXTO = "#1f2937"
COR_TEXTO_SECUNDARIO = "#6b7280"
COR_ERRO = "#dc2626"
COR_SUCESSO = "#16a34a"
COR_ALERTA = "#d97706"
COR_BORDA = "#e5e7eb"

CAMINHO_LOGO = "assets/logo_indamotos.png"
AVISO_ATRASO = "As alterações foram enviadas à Magazord. Podem levar até 1 hora para aparecer no site."


def _estoque(item):
    return f"{item.get('estoque_antigo', '-')} → {item.get('estoque_novo', '-')}"


def _preco(item):
    return f"{item.get('preco_antigo', '-')} → {item.get('preco_novo', '-')}"


def _texto(sincronizados, erros, alertas):
    partes = [f"Relatório de sincronização Inda Motos ({datetime.now().strftime('%d/%m/%Y %H:%M')})", ""]
    if sincronizados:
        partes += [AVISO_ATRASO, ""]
    if sincronizados:
        partes.append(f"ATUALIZADOS ({len(sincronizados)}):")
        for i in sincronizados:
            partes.append(f"- SKU {i['sku']} ({i['nome']}): estoque {_estoque(i)} | preço {_preco(i)}")
        partes.append("")
    if erros:
        partes.append(f"ERROS ({len(erros)}):")
        for e in erros:
            partes.append(f"- SKU {e['sku']} ({e['nome']}): {e['mensagem']}")
            partes.append(f"    estoque {_estoque(e)} | preço {_preco(e)}")
        partes.append("")
    if alertas:
        partes.append(f"ALERTAS ({len(alertas)}) - já sincronizados, mas com variação grande:")
        partes.append("Revise na tela do sistema; se algum não devia ter mudado assim, dá pra reverter.")
        for a in alertas:
            partes.append(f"- SKU {a['sku']}: banco \"{a['nome_banco']}\" | Magazord \"{a['nome_magazord']}\"")
            partes.append(f"    estoque {_alerta_estoque(a)} | preço {_alerta_preco(a)}")
            partes.append(f"    motivo: {', '.join(a['motivos'])}")
        partes.append("")
    return "\n".join(partes)


def _alerta_estoque(a):
    return f"{a.get('estoque_antigo', '-')} → {a.get('estoque_novo', '-')}"


def _alerta_preco(a):
    return f"{a.get('preco_antigo', '-')} → {a.get('preco_novo', '-')}"


def _celula(conteudo, cor=COR_TEXTO, nowrap=False):
    espaco = "white-space:nowrap;" if nowrap else ""
    return (
        f'<td style="padding:10px 12px;border-bottom:1px solid {COR_BORDA};font-size:13px;'
        f'color:{cor};{espaco}">{html.escape(str(conteudo))}</td>'
    )


def _secao(titulo, cor, cabecalhos, linhas):
    if not linhas:
        return ""
    ths = "".join(
        f'<th align="left" style="padding:8px 12px;font-size:11px;text-transform:uppercase;'
        f'letter-spacing:.04em;color:{COR_TEXTO_SECUNDARIO};border-bottom:2px solid {COR_BORDA};">{h}</th>'
        for h in cabecalhos
    )
    return f"""
        <tr>
          <td style="padding:0 24px 8px 24px;">
            <div style="font-size:14px;font-weight:700;color:{cor};margin:20px 0 4px 0;">{titulo}</div>
            <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;">
              <tr>{ths}</tr>{"".join(linhas)}
            </table>
          </td>
        </tr>"""


def _montar_html(sincronizados, erros, alertas, com_logo):
    data_formatada = datetime.now().strftime("%d/%m/%Y às %H:%M")
    if com_logo:
        cabecalho_marca = '<img src="cid:logo_indamotos" alt="Inda Motos" style="height:36px;margin-bottom:12px;" />'
    else:
        cabecalho_marca = f'<div style="font-size:16px;font-weight:700;color:{COR_TEXTO};margin-bottom:12px;">INDA MOTOS</div>'

    resumo = (
        f'<span style="color:{COR_SUCESSO};">✓ {len(sincronizados)} atualizado(s)</span>&nbsp;&nbsp;'
        f'<span style="color:{COR_ERRO};">✗ {len(erros)} erro(s)</span>&nbsp;&nbsp;'
        f'<span style="color:{COR_ALERTA};">! {len(alertas)} alerta(s)</span>'
    )

    secao_ok = _secao(
        "Atualizados", COR_SUCESSO, ["SKU", "Produto", "Estoque", "Preço"],
        [
            f"<tr>{_celula(i['sku'])}{_celula(i['nome'])}"
            f"{_celula(_estoque(i), COR_TEXTO_SECUNDARIO, True)}{_celula(_preco(i), COR_TEXTO_SECUNDARIO, True)}</tr>"
            for i in sincronizados
        ],
    )
    secao_erros = _secao(
        "Erros (não gravado)", COR_ERRO, ["SKU", "Produto", "Estoque", "Preço", "Motivo"],
        [
            f"<tr>{_celula(e['sku'])}{_celula(e['nome'])}"
            f"{_celula(_estoque(e), COR_TEXTO_SECUNDARIO, True)}{_celula(_preco(e), COR_TEXTO_SECUNDARIO, True)}"
            f"{_celula(e['mensagem'], COR_ERRO)}</tr>"
            for e in erros
        ],
    )
    secao_alertas = _secao(
        "Alertas (já sincronizados — revise)", COR_ALERTA,
        ["SKU", "Produto (banco / Magazord)", "Estoque", "Preço", "Motivo"],
        [
            f"<tr>{_celula(a['sku'])}"
            f"{_celula(a['nome_banco'] + ' / ' + a['nome_magazord'])}"
            f"{_celula(_alerta_estoque(a), COR_TEXTO_SECUNDARIO, True)}"
            f"{_celula(_alerta_preco(a), COR_TEXTO_SECUNDARIO, True)}"
            f"{_celula(', '.join(a['motivos']), COR_ALERTA)}</tr>"
            for a in alertas
        ],
    )

    return f"""\
<html>
  <body style="margin:0;padding:0;background-color:{COR_FUNDO};font-family:'Segoe UI',Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{COR_FUNDO};padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="640" cellpadding="0" cellspacing="0" style="background-color:{COR_CARD};border-radius:8px;overflow:hidden;border:1px solid {COR_BORDA};">
            <tr>
              <td style="padding:20px 24px;border-bottom:1px solid {COR_BORDA};">
                {cabecalho_marca}
                <div style="font-size:15px;font-weight:700;color:{COR_TEXTO};">Relatório de sincronização</div>
                <div style="font-size:12px;color:{COR_TEXTO_SECUNDARIO};margin-top:2px;">{data_formatada}</div>
                <div style="font-size:13px;margin-top:10px;">{resumo}</div>
                {f'<div style="font-size:12px;color:{COR_TEXTO_SECUNDARIO};margin-top:10px;">{AVISO_ATRASO}</div>' if sincronizados else ''}
              </td>
            </tr>
            {secao_ok}
            {secao_erros}
            {secao_alertas}
            <tr>
              <td style="padding:16px 24px;background-color:{COR_FUNDO};">
                <div style="font-size:11px;color:{COR_TEXTO_SECUNDARIO};">E-mail automático do sistema de sincronização Inda Motos.</div>
              </td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


def _assunto(sincronizados, erros, alertas):
    if erros:
        return f"⚠ Sincronização Inda Motos — {len(erros)} erro(s), {len(sincronizados)} atualizado(s)"
    return f"Sincronização Inda Motos — {len(sincronizados)} atualizado(s), {len(alertas)} alerta(s)"


def enviar_relatorio(sincronizados, erros, alertas):
    msg = MIMEMultipart("related")
    msg["Subject"] = _assunto(sincronizados, erros, alertas)
    msg["From"] = config.SMTP_USER
    msg["To"] = config.EMAIL_DESTINO

    alternativo = MIMEMultipart("alternative")
    msg.attach(alternativo)

    com_logo = os.path.exists(CAMINHO_LOGO)
    alternativo.attach(MIMEText(_texto(sincronizados, erros, alertas), "plain", "utf-8"))
    alternativo.attach(MIMEText(_montar_html(sincronizados, erros, alertas, com_logo), "html", "utf-8"))

    if com_logo:
        with open(CAMINHO_LOGO, "rb") as f:
            imagem = MIMEImage(f.read())
        imagem.add_header("Content-ID", "<logo_indamotos>")
        imagem.add_header("Content-Disposition", "inline", filename="logo_indamotos.png")
        msg.attach(imagem)

    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT) as server:
        server.starttls()
        server.login(config.SMTP_USER, config.SMTP_PASSWORD)
        server.send_message(msg)
