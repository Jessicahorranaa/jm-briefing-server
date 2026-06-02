"""
JM Briefing Server
------------------
Recebe o briefing do formulário HTML (FormData com campo 'dados' = JSON),
gera um diagnóstico estratégico com IA (Groq) e cria uma página organizada
no banco do Notion "Briefings Recebidos".

Variáveis de ambiente necessárias (configurar no Render):
  NOTION_TOKEN        -> token da integração interna do Notion (secret_...)
  NOTION_DATABASE_ID  -> a8673f9f821f4800a909b4a0651d9bf9
  GROQ_API_KEY        -> chave da Groq (gsk_...)
"""

import os
import json
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)  # permite que o formulário (outro domínio) envie dados

NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "a8673f9f821f4800a909b4a0651d9bf9")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_MODEL = os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile")

NOTION_VERSION = "2022-06-28"
NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": NOTION_VERSION,
    "Content-Type": "application/json",
}

# Opções válidas dos selects no Notion (precisam bater exatamente)
SELECT_ESTAGIO = {"Construindo do zero", "Rebranding / mudança de fase", "Consolidação", "Lançamento"}
SELECT_PELE = {"Pele clara", "Pele morena", "Pele bronzeada", "Pele oliva", "Pele negra"}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def as_text(value):
    """Transforma listas/strings em texto limpo para propriedades de texto."""
    if value is None:
        return ""
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return str(value)


def rich(text):
    text = (text or "")[:1900]  # limite seguro do Notion (2000)
    return [{"type": "text", "text": {"content": text}}] if text else []


def heading(text):
    return {
        "object": "block",
        "type": "heading_2",
        "heading_2": {"rich_text": [{"type": "text", "text": {"content": text}}]},
    }


def paragraph(text):
    return {
        "object": "block",
        "type": "paragraph",
        "paragraph": {"rich_text": rich(text)},
    }


def callout(text):
    return {
        "object": "block",
        "type": "callout",
        "callout": {
            "rich_text": rich(text),
            "icon": {"emoji": "✨"},
            "color": "brown_background",
        },
    }


def bullet(text):
    return {
        "object": "block",
        "type": "bulleted_list_item",
        "bulleted_list_item": {"rich_text": rich(text)},
    }


# ---------------------------------------------------------------------------
# Diagnóstico estratégico via Groq
# ---------------------------------------------------------------------------
def gerar_diagnostico(d):
    if not GROQ_API_KEY:
        return "⚠️ GROQ_API_KEY não configurada — diagnóstico não gerado."

    resumo = json.dumps(d, ensure_ascii=False, indent=2)
    system = (
        "Você é diretora de arte e estrategista de imagem de uma agência premium de "
        "marca pessoal feminina (Jéssica Marques Studio). Recebe o briefing de uma "
        "cliente e escreve um DIAGNÓSTICO ESTRATÉGICO VISUAL curto, sofisticado e acionável."
    )
    user = (
        "Com base no briefing abaixo, escreva um diagnóstico em português do Brasil com estas seções, "
        "usando linguagem refinada e direta (sem enrolação):\n\n"
        "1. PERCEPÇÃO-ALVO — em 1-2 frases, a percepção central que a imagem dela precisa construir.\n"
        "2. DIREÇÃO VISUAL — paleta, tipo de luz, cenário e clima recomendados.\n"
        "3. POSE E EXPRESSÃO — como ela deve se posicionar/expressar para transmitir o que deseja.\n"
        "4. LOOKS E ESTILO — recomendações de roupa/acessório alinhadas ao posicionamento.\n"
        "5. CUIDADOS — o que EVITAR (com base no que ela não quer transmitir / não quer alterar).\n"
        "6. RECOMENDAÇÃO FINAL — 1 frase de direção criativa.\n\n"
        f"BRIEFING:\n{resumo}"
    )
    try:
        r = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": GROQ_MODEL,
                "temperature": 0.7,
                "max_tokens": 1100,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user", "content": user},
                ],
            },
            timeout=60,
        )
        r.raise_for_status()
        return r.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"⚠️ Não foi possível gerar o diagnóstico automaticamente: {e}"


# ---------------------------------------------------------------------------
# Upload de imagens para o Notion (opcional, não bloqueante)
# ---------------------------------------------------------------------------
def upload_to_notion(file_storage):
    """Faz upload de um arquivo e retorna o file_upload id, ou None se falhar."""
    try:
        create = requests.post(
            "https://api.notion.com/v1/file_uploads",
            headers={
                "Authorization": f"Bearer {NOTION_TOKEN}",
                "Notion-Version": NOTION_VERSION,
                "Content-Type": "application/json",
            },
            json={"filename": file_storage.filename, "content_type": file_storage.mimetype},
            timeout=30,
        )
        create.raise_for_status()
        up = create.json()
        up_id = up["id"]
        send = requests.post(
            up["upload_url"],
            headers={"Authorization": f"Bearer {NOTION_TOKEN}", "Notion-Version": NOTION_VERSION},
            files={"file": (file_storage.filename, file_storage.stream, file_storage.mimetype)},
            timeout=120,
        )
        send.raise_for_status()
        return up_id
    except Exception as e:
        print("Falha no upload de imagem:", e)
        return None


def image_block(file_upload_id):
    return {
        "object": "block",
        "type": "image",
        "image": {"type": "file_upload", "file_upload": {"id": file_upload_id}},
    }


# ---------------------------------------------------------------------------
# Monta as propriedades do Notion
# ---------------------------------------------------------------------------
def montar_propriedades(d):
    estagio = d.get("estagio")
    pele = d.get("tom_pele")
    props = {
        "Nome": {"title": [{"text": {"content": d.get("nome", "Sem nome")[:200]}}]},
        "Nicho": {"rich_text": rich(as_text(d.get("nicho")))},
        "Instagram": {"rich_text": rich(as_text(d.get("instagram")))},
        "Objetivo visual": {"rich_text": rich(as_text(d.get("objetivo_visual")))},
        "Sensações desejadas": {"rich_text": rich(as_text(d.get("sensacoes")))},
        "Altura": {"rich_text": rich(as_text(d.get("altura")))},
        "Peso": {"rich_text": rich(as_text(d.get("peso")))},
        "Traços faciais": {"rich_text": rich(as_text(d.get("tracos_faciais")))},
        "O que valorizar": {"rich_text": rich(as_text(d.get("valorizar")))},
        "O que não alterar": {"rich_text": rich(as_text(d.get("nao_alterar")))},
        "Looks selecionados": {"rich_text": rich(as_text(d.get("looks")))},
        "Calçados selecionados": {"rich_text": rich(as_text(d.get("calcados")))},
        "Estilo ideal": {"rich_text": rich(as_text(d.get("estilo_ideal")))},
        "Percepção do público": {"rich_text": rich(as_text(d.get("publico_sentir")))},
        "Objetivo das fotos": {"rich_text": rich(as_text(d.get("objetivo_fotos")))},
        "O que não transmitir": {"rich_text": rich(as_text(d.get("nao_transmitir")) + " " + as_text(d.get("nao_percebida")))},
        "Referências visuais": {"rich_text": rich(
            " | ".join(filter(None, [
                f"{d.get('ref1','')} ({d.get('ref1_pq','')})",
                f"{d.get('ref2','')} ({d.get('ref2_pq','')})",
                f"{d.get('ref3','')} ({d.get('ref3_pq','')})",
            ])))},
        "Observações finais": {"rich_text": rich(as_text(d.get("observacoes")))},
        "Status": {"select": {"name": "Recebido"}},
    }
    if estagio in SELECT_ESTAGIO:
        props["Estágio da marca"] = {"select": {"name": estagio}}
    if pele in SELECT_PELE:
        props["Tom de pele"] = {"select": {"name": pele}}
    return props


# ---------------------------------------------------------------------------
# Monta o corpo da página (diagnóstico + respostas completas)
# ---------------------------------------------------------------------------
def montar_corpo(d, diagnostico, foto_ids, ref_ids):
    blocks = [heading("✨ Diagnóstico Estratégico (IA)")]
    for par in diagnostico.split("\n"):
        if par.strip():
            blocks.append(callout(par.strip()) if par.strip().startswith(("1.", "2.", "3.", "4.", "5.", "6.")) else paragraph(par.strip()))

    blocks.append(heading("01 — Posicionamento"))
    blocks += [
        bullet(f"Estágio da marca: {as_text(d.get('estagio'))}"),
        bullet(f"O que quer transmitir: {as_text(d.get('sensacoes'))}"),
        bullet(f"Frase-chave: {as_text(d.get('frase'))}"),
        bullet(f"Não quer ser percebida como: {as_text(d.get('nao_percebida'))}"),
        paragraph(f"Objetivo visual: {as_text(d.get('objetivo_visual'))}"),
    ]

    blocks.append(heading("02 — Corpo e presença"))
    blocks += [
        bullet(f"Altura: {as_text(d.get('altura'))} · Peso: {as_text(d.get('peso'))}"),
        bullet(f"Corpo: {as_text(d.get('corpo'))}"),
        bullet(f"Tom de pele: {as_text(d.get('tom_pele'))}"),
        bullet(f"Cabelo: {as_text(d.get('cabelo'))} {as_text(d.get('cabelo_cor'))}"),
        bullet(f"Traços faciais: {as_text(d.get('tracos_faciais'))}"),
        bullet(f"Quer valorizar: {as_text(d.get('valorizar'))}"),
        paragraph(f"NÃO alterar: {as_text(d.get('nao_alterar'))}"),
    ]

    blocks.append(heading("03 — Look e estética"))
    blocks += [
        bullet(f"Tons: {as_text(d.get('tons'))}"),
        bullet(f"Looks: {as_text(d.get('looks'))}"),
        bullet(f"Acessórios: {as_text(d.get('acessorios'))}"),
        bullet(f"Calçados: {as_text(d.get('calcados'))}"),
        bullet(f"Estilo ideal: {as_text(d.get('estilo_ideal'))}"),
        bullet(f"Evitar (roupa/cor): {as_text(d.get('evitar_roupa'))}"),
        bullet(f"Não gosta (acessório/calçado): {as_text(d.get('nao_gosta_acessorio'))}"),
        paragraph(f"Referências de estilo: {as_text(d.get('referencias_estilo'))}"),
    ]

    blocks.append(heading("04 — Percepção"))
    blocks += [
        bullet(f"Público precisa sentir: {as_text(d.get('publico_sentir'))}"),
        bullet(f"Objetivo das fotos: {as_text(d.get('objetivo_fotos'))}"),
        bullet(f"NÃO transmitir: {as_text(d.get('nao_transmitir'))}"),
        paragraph(f"Hoje não representa mais: {as_text(d.get('nao_representa'))}"),
        paragraph(f"Ref 1: {d.get('ref1','')} — {d.get('ref1_pq','')}"),
        paragraph(f"Ref 2: {d.get('ref2','')} — {d.get('ref2_pq','')}"),
        paragraph(f"Ref 3: {d.get('ref3','')} — {d.get('ref3_pq','')}"),
    ]

    if foto_ids:
        blocks.append(heading("05 — Fotos da cliente"))
        blocks += [image_block(i) for i in foto_ids]
    if ref_ids:
        blocks.append(heading("Referências visuais enviadas"))
        blocks += [image_block(i) for i in ref_ids]
    if d.get("observacoes"):
        blocks.append(paragraph(f"Observações finais: {as_text(d.get('observacoes'))}"))

    return blocks[:100]  # Notion aceita até 100 blocos na criação


# ---------------------------------------------------------------------------
# Rotas
# ---------------------------------------------------------------------------
@app.route("/")
def home():
    return "JM Briefing Server ativo ✦", 200


@app.route("/webhook", methods=["POST"])
def webhook():
    raw = request.form.get("dados")
    if not raw:
        return jsonify({"error": "campo 'dados' ausente"}), 400
    try:
        d = json.loads(raw)
    except Exception as e:
        return jsonify({"error": f"JSON inválido: {e}"}), 400

    # 1) Diagnóstico
    diagnostico = gerar_diagnostico(d)

    # 2) Uploads (não bloqueiam o fluxo)
    foto_ids = [i for i in (upload_to_notion(f) for f in request.files.getlist("fotos")) if i]
    ref_ids = [i for i in (upload_to_notion(f) for f in request.files.getlist("referencias")) if i]

    # 3) Cria a página no Notion
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": montar_propriedades(d),
        "children": montar_corpo(d, diagnostico, foto_ids, ref_ids),
    }
    r = requests.post("https://api.notion.com/v1/pages", headers=NOTION_HEADERS, json=payload, timeout=60)
    if r.status_code >= 300:
        print("Erro Notion:", r.text)
        return jsonify({"error": "Falha ao criar página no Notion", "detalhe": r.text}), 500

    return jsonify({"ok": True, "page": r.json().get("url")}), 200


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
