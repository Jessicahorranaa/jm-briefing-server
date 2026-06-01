import os, json, requests
from datetime import datetime
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_DB_ID = os.environ.get("NOTION_DATABASE_ID", "a8673f9f821f4800a909b4a0651d9bf9")

def nh():
        return {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

def rt(t):
        return [{"text": {"content": str(t)[:2000]}}] if t else []

def tb(c):
        return {"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":c[:2000]}}]}}

def hb(c):
        return {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":c}}]}}

def db():
        return {"object":"block","type":"divider","divider":{}}

@app.get("/")
def health():
        return {"status": "JM Studio Briefing Visual v2 - online"}

@app.post("/webhook")
async def webhook(dados: str = Form(...)):
        try:
                    d = json.loads(dados)
                    print(f"[BRIEFING] {d.get('nome','?')}")
                    diag = gerar_diagnostico(d)
                    url = salvar_notion(d, diag)
                    return {"ok": True, "notion_url": url}
except Exception as e:
        import traceback; traceback.print_exc()
        return {"ok": False, "erro": str(e)}

def gerar_diagnostico(d):
        if not GROQ_API_KEY:
                    return "Groq nao configurado."
                cabelo = f"{d.get('cabelo_comprimento','')} {d.get('cabelo_textura','')} {d.get('cabelo_cor','')}".strip()
    refs = f"Ref1: {d.get('ref1_link','')} - {d.get('ref1_desc','')} | Ref2: {d.get('ref2_link','')} - {d.get('ref2_desc','')} | Ref3: {d.get('ref3_link','')} - {d.get('ref3_desc','')}"
    prompt = f"""Voce e Jessica Marques, diretora criativa de ensaio fotografico IA para marca pessoal feminina premium.
    Crie um DIAGNOSTICO ESTRATEGICO VISUAL com 5 secoes:
    1. LEITURA DA MARCA | 2. DIRECAO CRIATIVA | 3. LOOKS E STYLING | 4. POSES E EXPRESSOES | 5. PROXIMOS PASSOS

    BRIEFING: Nome:{d.get('nome','')} | Nicho:{d.get('nicho','')} | Estagio:{d.get('estagio','')}
    Transmitir:{d.get('objetivo_visual','')} | Sensacoes:{d.get('sensacoes','')} | Percepcao:{d.get('percepcao_principal','')}
    Nao transmitir:{d.get('nao_transmitir','')} | Publico sentir:{d.get('pub_sentir','')} | Objetivo fotos:{d.get('obj_fotos','')}
    Altura:{d.get('altura','')} | Peso:{d.get('peso','')} | Corpo:{d.get('corpo','')} | Tom:{d.get('tom_pele','')}
    Cabelo:{cabelo} | Tracos:{d.get('tracos','')} | Valorizar:{d.get('valorizar','')} | Nao alterar:{d.get('nao_alterar','')}
    Tons:{d.get('tons','')} | Looks:{d.get('looks','')} | Acessorios:{d.get('acessorios','')} | Calcados:{d.get('calcados','')}
    Estilo:{d.get('estilo_ideal','')} | Referencias:{refs} | Obs:{d.get('obs_finais','')}
    Escreva em portugues, sofisticado, 400 palavras."""
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
                              headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
                              json={"model":"llama-3.3-70b-versatile","messages":[{"role":"user","content":prompt}],"max_tokens":2000},
                              timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def salvar_notion(d, diag):
        nome = d.get("nome","Cliente")
    titulo = f"Briefing {nome} - {datetime.now().strftime('%d/%m/%Y')}"
    tom = d.get("tom_pele","")
    estagio = d.get("estagio","")
    cabelo = f"{d.get('cabelo_comprimento','')} {d.get('cabelo_textura','')} {d.get('cabelo_cor','')}".strip()
    refs = f"Ref 1: {d.get('ref1_link','')} - {d.get('ref1_desc','')}\nRef 2: {d.get('ref2_link','')} - {d.get('ref2_desc','')}\nRef 3: {d.get('ref3_link','')} - {d.get('ref3_desc','')}\nEstilo: {d.get('ref_estilo','')}"
    obj_v = f"{d.get('objetivo_visual','')}\nSensacoes: {d.get('sensacoes','')}\nPercepcao: {d.get('percepcao_principal','')}\nFrase: {d.get('frase_imagem','')}"
    nao_t = f"Evitar: {d.get('nao_percepcao','')}\nNao transmitir: {d.get('nao_transmitir','')}\nNao representa: {d.get('nao_representa','')}"
    looks_f = f"Looks: {d.get('looks','')}\nTons: {d.get('tons','')}\nNao quer: {d.get('nao_look','')}"
    calc_f = f"Calcados: {d.get('calcados','')}\nAcessorios: {d.get('acessorios','')}\nNao quer: {d.get('nao_acessorios','')}"
    tracos_f = f"Corpo: {d.get('corpo','')}\nTracos: {d.get('tracos','')}\nCabelo: {cabelo}"

    props = {
                "Nome": {"title": [{"text": {"content": titulo[:100]}}]},
                "Status": {"select": {"name": "Recebido"}},
                "Nicho": {"rich_text": rt(d.get("nicho",""))},
                "Instagram": {"rich_text": rt(d.get("instagram",""))},
                "Objetivo visual": {"rich_text": rt(obj_v)},
                "Sensações desejadas": {"rich_text": rt(d.get("sensacoes",""))},
                "Percepção do público": {"rich_text": rt(d.get("pub_sentir",""))},
                "Objetivo das fotos": {"rich_text": rt(d.get("obj_fotos",""))},
                "Referências visuais": {"rich_text": rt(refs)},
                "Altura": {"rich_text": rt(d.get("altura",""))},
                "Peso": {"rich_text": rt(d.get("peso",""))},
                "Traços faciais": {"rich_text": rt(tracos_f)},
                "O que valorizar": {"rich_text": rt(d.get("valorizar",""))},
                "O que não alterar": {"rich_text": rt(d.get("nao_alterar",""))},
                "O que não transmitir": {"rich_text": rt(nao_t)},
                "Looks selecionados": {"rich_text": rt(looks_f)},
                "Calçados selecionados": {"rich_text": rt(calc_f)},
                "Estilo ideal": {"rich_text": rt(d.get("estilo_ideal",""))},
                "Observações finais": {"rich_text": rt(d.get("obs_finais",""))},
    }
    if tom in ["Pele clara","Pele morena","Pele bronzeada","Pele oliva","Pele negra"]:
                props["Tom de pele"] = {"select": {"name": tom}}
            if estagio in ["Construindo do zero","Rebranding / mudança de fase","Consolidação","Lançamento"]:
                        props["Estágio da marca"] = {"select": {"name": estagio}}

    blocos = [hb("Diagnóstico Estratégico Visual"), db()]
    for chunk in [diag[i:i+1900] for i in range(0, len(diag), 1900)]:
                blocos.append(tb(chunk))
            blocos += [db(), hb("Dados do Briefing"), db(),
                               tb(f"Nome: {nome} | Nicho: {d.get('nicho','')} | Estagio: {estagio} | Instagram: {d.get('instagram','')}"),
                               tb(f"Altura: {d.get('altura','')} | Peso: {d.get('peso','')} | Tom: {tom} | Corpo: {d.get('corpo','')}"),
                               tb(f"Cabelo: {cabelo}\nTracos: {d.get('tracos','')}"),
                               tb(f"Estilo: {d.get('estilo_ideal','')}\nLooks: {d.get('looks','')}"),
                               tb(f"Nao transmitir: {d.get('nao_transmitir','')}\nValorizar: {d.get('valorizar','')}"),
                               tb(refs[:1900]),
                               tb(f"Obs: {d.get('obs_finais','')}"),
                      ]
    payload = {"parent": {"database_id": NOTION_DB_ID}, "properties": props, "children": blocos[:100]}
    r = requests.post("https://api.notion.com/v1/pages", headers=nh(), json=payload, timeout=30)
    r.raise_for_status()
    return r.json().get("url","")
