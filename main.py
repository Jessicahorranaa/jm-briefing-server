import os, json, requests
from datetime import datetime
from fastapi import FastAPI, Form
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
NOTION_TOKEN = os.environ.get("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.environ.get("NOTION_DATABASE_ID", "a8673f9f821f4800a909b4a0651d9bf9")

def nh():
    return {"Authorization": f"Bearer {NOTION_TOKEN}", "Content-Type": "application/json", "Notion-Version": "2022-06-28"}

@app.get("/")
def health():
    return {"status": "JM Studio Briefing Visual v1 - online"}

@app.post("/webhook")
async def webhook(dados: str = Form(...)):
    try:
        d = json.loads(dados)
        nome = d.get("nome", "Cliente")
        print(f"[BRIEFING] {nome}")
        diag = gerar_diagnostico(d)
        salvar_notion(d, diag)
        return {"ok": True}
    except Exception as e:
        print(f"[ERRO] {e}")
        return {"ok": False, "erro": str(e)}

def gerar_diagnostico(d):
    if not GROQ_API_KEY:
        return "Groq nao configurado."
    nome = d.get("nome", "cliente")
    prompt = "Voce e Jessica Marques, diretora criativa de ensaio fotografico IA para marca pessoal feminina premium. Briefing: Nome: " + str(d.get("nome")) + " | Nicho: " + str(d.get("nicho")) + " | Estagio: " + str(d.get("estagioMarca")) + " | Sensacoes: " + str(d.get("sensacoesDesejadas")) + " | Percepcao: " + str(d.get("percepcaoMaisImportante")) + " | NAO transmitir: " + str(d.get("naoTransmitir")) + " | Estilo: " + str(d.get("estiloIdeal")) + " | Looks: " + str(d.get("looksPreferidos")) + " | Cores: " + str(d.get("coresPreferidas")) + " | Valorizar: " + str(d.get("oquevValorizar")) + " | NAO alterar: " + str(d.get("naoAlterar")) + ". Crie diagnostico com 5 secoes: LEITURA DA MARCA, DIRECAO CRIATIVA, LOOKS E STYLING, POSES E EXPRESSOES, PROXIMOS PASSOS. Portugues, sofisticado, personalizado."
    r = requests.post("https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
        json={"model": "llama-3.3-70b-versatile", "messages": [{"role": "user", "content": prompt}], "max_tokens": 2000},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]

def tb(c): return {"object":"block","type":"paragraph","paragraph":{"rich_text":[{"type":"text","text":{"content":c[:2000]}}]}}
def hb(c): return {"object":"block","type":"heading_2","heading_2":{"rich_text":[{"type":"text","text":{"content":c}}]}}
def db(): return {"object":"block","type":"divider","divider":{}}
def ck(t): return [t[i:i+1900] for i in range(0,len(t),1900)]

def salvar_notion(d, diag):
    titulo = "Briefing " + d.get("nome","?") + " - " + datetime.now().strftime("%d/%m/%Y")
    tom = d.get("tomPele","")
    estagio = d.get("estagioMarca","")
    props = {
        "Nome": {"title": [{"text": {"content": titulo}}]},
        "Status": {"select": {"name": "Recebido"}},
        "Nicho": {"rich_text": [{"text": {"content": d.get("nicho","")[:2000]}}]},
        "Instagram": {"rich_text": [{"text": {"content": d.get("instagram","")[:2000]}}]},
        "Objetivo visual": {"rich_text": [{"text": {"content": d.get("percepcaoMaisImportante","")[:2000]}}]},
        "Sensacoes desejadas": {"rich_text": [{"text": {"content": d.get("sensacoesDesejadas","")[:2000]}}]},
        "Percepcao do publico": {"rich_text": [{"text": {"content": d.get("percepcaoPublico","")[:2000]}}]},
        "Objetivo das fotos": {"rich_text": [{"text": {"content": d.get("objetivoFotos","")[:2000]}}]},
        "Altura": {"rich_text": [{"text": {"content": d.get("altura","")[:200]}}]},
        "Peso": {"rich_text": [{"text": {"content": d.get("peso","")[:200]}}]},
        "Estilo ideal": {"rich_text": [{"text": {"content": d.get("estiloIdeal","")[:2000]}}]},
        "Looks selecionados": {"rich_text": [{"text": {"content": d.get("looksPreferidos","")[:2000]}}]},
        "Calcados selecionados": {"rich_text": [{"text": {"content": d.get("calcados","")[:2000]}}]},
        "O que valorizar": {"rich_text": [{"text": {"content": d.get("oquevValorizar","")[:2000]}}]},
        "O que nao alterar": {"rich_text": [{"text": {"content": d.get("naoAlterar","")[:2000]}}]},
        "O que nao transmitir": {"rich_text": [{"text": {"content": d.get("naoTransmitir","")[:2000]}}]},
        "Tracos faciais": {"rich_text": [{"text": {"content": d.get("tracosFaciais","")[:2000]}}]},
        "Observacoes finais": {"rich_text": [{"text": {"content": d.get("obsFinal","")[:2000]}}]},
    }
    if tom in ["Pele clara","Pele morena","Pele bronzeada","Pele oliva","Pele negra"]:
        props["Tom de pele"] = {"select": {"name": tom}}
    if estagio in ["Construindo do zero","Rebranding / mudança de fase","Consolidação","Lançamento"]:
        props["Estagio da marca"] = {"select": {"name": estagio}}
    refs = d.get("referenciasVisuais",[])
    rt = " | ".join(["Ref"+str(i)+":"+r["referencia"] for i,r in enumerate(refs,1) if r.get("referencia")])
    if rt: props["Referencias visuais"] = {"rich_text": [{"text": {"content": rt[:2000]}}]}
    headers = nh()
    blocos = [hb("Dados do Briefing"), db()]
    for k,v in [("Nicho",d.get("nicho","")),("Estagio",estagio),("Instagram",d.get("instagram","")),
        ("Sensacoes",d.get("sensacoesDesejadas","")),("Percepcao",d.get("percepcaoMaisImportante","")),
        ("Frase",d.get("fraseImagem","")),("Corpo",d.get("corpo","")),("Tom",tom),
        ("Cabelo",d.get("cabelo","")),("Tracos",d.get("tracosFaciais","")),
        ("Valorizar",d.get("oquevValorizar","")),("NaoAlterar",d.get("naoAlterar","")),
        ("Cores",d.get("coresPreferidas","")),("Looks",d.get("looksPreferidos","")),
        ("Calcados",d.get("calcados","")),("Estilo",d.get("estiloIdeal","")),
        ("Objetivo",d.get("objetivoFotos","")),("NaoTransmitir",d.get("naoTransmitir","")),
        ("Obs",d.get("obsFinal",""))]:
        if v: [blocos.append(tb(c)) for c in ck("- "+k+": "+v)]
    blocos += [db(), hb("Diagnostico Estrategico IA"), db()]
    [blocos.append(tb(c)) for c in ck(diag)]
    payload = {"parent": {"database_id": NOTION_DATABASE_ID}, "properties": props, "children": blocos[:100]}
    r = requests.post("https://api.notion.com/v1/pages", headers=headers, json=payload, timeout=30)
    r.raise_for_status()
    if len(blocos) > 100:
        pid = r.json()["id"]
        rem = blocos[100:]
        while rem:
            batch, rem = rem[:100], rem[100:]
            requests.patch("https://api.notion.com/v1/blocks/"+pid+"/children", headers=headers, json={"children": batch}, timeout=30)
