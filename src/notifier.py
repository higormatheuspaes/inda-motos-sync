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
COR_BORDA = "#e5e7eb"

CAMINHO_LOGO = "assets/logo_indamotos.png"


def _montar_texto_simples(lista_erros):
    corpo = "As seguintes inconsistências ocorreram na sincronização de hoje:\n\n"
    for erro in lista_erros:
        nome = erro.get("nome", "")
        estoque = f"{erro.get('estoque_antigo', '-')} → {erro.get('estoque_novo', '-')}"
        preco = f"{erro.get('preco_antigo', '-')} → {erro.get('preco_novo', '-')}"
        corpo += (
            f"- SKU {erro['sku']} ({nome}): {erro['mensagem']}\n"
            f"    Estoque tentado: {estoque}  |  Preço tentado: {preco}\n"
        )
    return corpo


def _linha_html(erro):
    nome = erro.get("nome", "")
    estoque = f"{erro.get('estoque_antigo', '-')} → {erro.get('estoque_novo', '-')}"
    preco = f"{erro.get('preco_antigo', '-')} → {erro.get('preco_novo', '-')}"
    return f"""
        <tr>
            <td style="padding:10px 12px;border-bottom:1px solid {COR_BORDA};font-size:13px;color:{COR_TEXTO};">{erro['sku']}</td>
            <td style="padding:10px 12px;border-bottom:1px solid {COR_BORDA};font-size:13px;color:{COR_TEXTO};">{nome}</td>
            <td style="padding:10px 12px;border-bottom:1px solid {COR_BORDA};font-size:13px;color:{COR_TEXTO_SECUNDARIO};white-space:nowrap;">{estoque}</td>
            <td style="padding:10px 12px;border-bottom:1px solid {COR_BORDA};font-size:13px;color:{COR_TEXTO_SECUNDARIO};white-space:nowrap;">{preco}</td>
            <td style="padding:10px 12px;border-bottom:1px solid {COR_BORDA};font-size:13px;color:{COR_ERRO};">{erro['mensagem']}</td>
        </tr>"""


def _montar_html(lista_erros, com_logo):
    linhas = "".join(_linha_html(e) for e in lista_erros)
    data_formatada = datetime.now().strftime("%d/%m/%Y às %H:%M")

    if com_logo:
        cabecalho_marca = '<img src="cid:logo_indamotos" alt="Inda Motos" style="height:36px;margin-bottom:12px;" />'
    else:
        cabecalho_marca = f'<div style="font-size:16px;font-weight:700;color:{COR_TEXTO};margin-bottom:12px;">INDA MOTOS</div>'

    return f"""\
<html>
  <body style="margin:0;padding:0;background-color:{COR_FUNDO};font-family:'Segoe UI',Arial,sans-serif;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background-color:{COR_FUNDO};padding:24px 0;">
      <tr>
        <td align="center">
          <table role="presentation" width="600" cellpadding="0" cellspacing="0" style="background-color:{COR_CARD};border-radius:8px;overflow:hidden;border:1px solid {COR_BORDA};">
            <tr>
              <td style="padding:20px 24px;border-bottom:1px solid {COR_BORDA};">
                {cabecalho_marca}
                <div style="font-size:15px;font-weight:700;color:{COR_ERRO};">⚠ {len(lista_erros)} inconsistência(s) na sincronização</div>
                <div style="font-size:12px;color:{COR_TEXTO_SECUNDARIO};margin-top:2px;">{data_formatada}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:0 24px 8px 24px;">
                <table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="border-collapse:collapse;margin-top:16px;">
                  <tr>
                    <th align="left" style="padding:8px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:{COR_TEXTO_SECUNDARIO};border-bottom:2px solid {COR_BORDA};">SKU</th>
                    <th align="left" style="padding:8px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:{COR_TEXTO_SECUNDARIO};border-bottom:2px solid {COR_BORDA};">Produto</th>
                    <th align="left" style="padding:8px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:{COR_TEXTO_SECUNDARIO};border-bottom:2px solid {COR_BORDA};">Estoque</th>
                    <th align="left" style="padding:8px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:{COR_TEXTO_SECUNDARIO};border-bottom:2px solid {COR_BORDA};">Preço</th>
                    <th align="left" style="padding:8px 12px;font-size:11px;text-transform:uppercase;letter-spacing:.04em;color:{COR_TEXTO_SECUNDARIO};border-bottom:2px solid {COR_BORDA};">Erro</th>
                  </tr>{linhas}
                </table>
              </td>
            </tr>
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


def enviar_email_erros(lista_erros):
    if not lista_erros:
        return

    total = len(lista_erros)
    msg = MIMEMultipart("related")
    msg["Subject"] = f"⚠ Sincronização Inda Motos — {total} inconsistência(s) encontrada(s)"
    msg["From"] = config.SMTP_USER
    msg["To"] = config.EMAIL_DESTINO

    alternativo = MIMEMultipart("alternative")
    msg.attach(alternativo)

    com_logo = os.path.exists(CAMINHO_LOGO)
    alternativo.attach(MIMEText(_montar_texto_simples(lista_erros), "plain", "utf-8"))
    alternativo.attach(MIMEText(_montar_html(lista_erros, com_logo), "html", "utf-8"))

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
