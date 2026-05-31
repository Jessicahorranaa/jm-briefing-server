import os
import json
from datetime import datetime
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import httpx
from groq import Groq

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["POST"],
    allow_headers=["*"],
)

NOTION_TOKEN    = os.environ["NOTION_TOKEN"]
NOTION_DATABASE = os.environ["NOTION_DATABASE_ID"]
GROQ_API_KEY    = os.environ["GROQ_API_KEY"]

groq_client = Groq(api_key=GROQ_API_KEY)


@app.post("/briefing")
async def receber_briefing(
    dados: str = Form(...),
    fotos_pessoais: list[UploadFile] = File(default=[]),
    referencias_visuais: list[UploadFile] = File(default=[]),
    fotos_referencias: list[UploadFile] = File(default=[]),
):
    d = json.loads(dados)
    nome = d.get("nome", "Cliente")
    diagnostico = gerar_diagnostico(d)
    url_notion = await criar_pagina_notion(d, diagnostico)
    return {"status": "ok", "mensagem": f"Briefing de {nome} recebido!", "notion": url_notion}


def gerar_diagnostico(d: dict) -> str:
    prompt = f"""
Você é uma diretora criativa especialista em marca pessoal feminina premium.
Com base neste briefing, escreva um diagnóstico estratégico de 3 a 5 parágrafos
para orientar a direção criativa do ensaio fotográfico de IA.

Inclua: leitura do posicionamento atual e desejado, tom emocional e visual recomendado,
paleta de sensações e direção estética, recomendações de poses/expressão/energia,
alertas sobre o que evitar.

Nome: {d.get('nome')} | Nicho: {d.get('nicho')} | Estágio: {d.get('estagio')}
Objetivo visual: {d.get('objetivo_visual')}
Sentimentos desejados: {d.get('sentimento')} | Evitar: {d.get('evitar')}
Frase de imagem: {d.get('frase_imagem')}
Corpo: {d.get('corpo')} | Pele: {d.get('pele')}
Cabelo: {d.get('cabelo_comp')} {d.get('cabelo_tex')} {d.get('cabelo_cor')}
Valorizar: {d.get('valorizar')} | Não alterar: {d.get('nao_alterar')}
Tons: {d.get('tons')} | Roupas: {d.get('roupa')} | Estilo: {d.get('estilo_ideal')}
Público deve sentir: {d.get('publico_sentir')}
Não transmitir: {d.get('nao_transmitir')}
Referências: {d.get('ref1_link')} / {d.get('ref2_link')} / {d.get('ref3_link')}
Obs finais: {d.get('obs_finais')}

Escreva em parágrafos corridos, tom profissional e acolhedor.
"""
    resp = groq_client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.7,
        max_tokens=1200,
    )
    return resp.choices[0].message.content


async def criar_pagina_notion(d: dict, diagnostico: str) -> str:
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    nome  = d.get("nome", "Cliente")
    nicho = d.get("nicho", "")
    hoje  = datetime.today().strftime("%Y-%m-%d")

    def txt(text, bold=False):
        return {"type": "text", "text": {"content": str(text)}, "annotations": {"bold": bold}}

    def paragraph(text):
        return {"object": "block", "type": "paragraph", "paragraph": {"rich_text": [txt(text)]}}

    def heading(level, text):
        return {"object": "block", "type": f"heading_{level}", f"heading_{level}": {"rich_text": [txt(text)]}}

    def divider():
        return {"object": "block", "type": "divider", "divider": {}}

    def callout(text, emoji="✦"):
        return {"object": "block", "type": "callout", "callout": {
            "rich_text": [txt(text)], "icon": {"type": "emoji", "emoji": emoji}, "color": "gray_background"}}

    def secao(titulo, valor):
        if not valor:
            return []
        v = ", ".join(valor) if isinstance(valor, list) else str(valor)
        return [{"object": "block", "type": "paragraph", "paragraph": {
            "rich_text": [txt(titulo + ": ", bold=True), txt(v)]}}]

    blocos = [
        callout(f"Oi, {nome.split()[0]}! Este é o diagnóstico estratégico do seu ensaio. 🤍"),
        divider(),
        heading(2, "✦ Diagnóstico Estratégico"),
    ]
    for p in diagnostico.split("\n\n"):
        if p.strip():
            blocos.append(paragraph(p.strip()))

    blocos += [
        divider(), heading(2, "01 · Posicionamento"),
        *secao("Nicho", nicho), *secao("Estágio", d.get("estagio")),
        *secao("Objetivo visual", d.get("objetivo_visual")),
        *secao("Sentimentos desejados", d.get("sentimento")),
        *secao("O que evitar", d.get("evitar")),
        divider(), heading(2, "02 · Corpo & Presença"),
        *secao("Altura", d.get("altura")), *secao("Peso", d.get("peso")),
        *secao("Corpo", d.get("corpo")), *secao("Tom de pele", d.get("pele")),
        *secao("Traços faciais", d.get("tracoes")),
        *secao("Valorizar", d.get("valorizar")),
        *secao("Não alterar", d.get("nao_alterar")),
        divider(), heading(2, "03 · Look & Estética"),
        *secao("Tons", d.get("tons")), *secao("Roupas", d.get("roupa")),
        *secao("Não quer usar", d.get("roupa_nao_quer")),
        *secao("Acessórios", d.get("acessorios")),
        *secao("Estilo ideal", d.get("estilo_ideal")),
        *secao("Referências de estilo", d.get("referencias_estilo")),
        divider(), heading(2, "04 · Percepção"),
        *secao("Público deve sentir", d.get("publico_sentir")),
        *secao("Objetivo das fotos", d.get("objetivo_fotos")),
        *secao("Não transmitir", d.get("nao_transmitir")),
        *secao("Não representa mais", d.get("nao_representa")),
        *secao("Referência 1", d.get("ref1_link")),
        *secao("Referência 2", d.get("ref2_link")),
        *secao("Referência 3", d.get("ref3_link")),
        divider(), *secao("Observações finais", d.get("obs_finais")),
    ]

    payload = {
        "parent": {"database_id": NOTION_DATABASE},
        "properties": {
            "Nome": {"title": [{"text": {"content": nome}}]},
            "Nicho": {"rich_text": [{"text": {"content": nicho}}]},
            "Data da entrada": {"date": {"start": hoje}},
            "Status": {"select": {"name": "Briefing recebido"}},
        },
        "children": blocos[:100],
    }

    async with httpx.AsyncClient() as client:
        r = await client.post("https://api.notion.com/v1/pages", headers=headers, json=payload)
        r.raise_for_status()
        data = r.json()

    if len(blocos) > 100:
        page_id = data["id"]
        async with httpx.AsyncClient() as client:
            await client.patch(
                f"https://api.notion.com/v1/blocks/{page_id}/children",
                headers=headers, json={"children": blocos[100:]})

    return data.get("url", "")


@app.get("/")
def health():
    return {"status": "JM Briefing Server rodando ✦"}
