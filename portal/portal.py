#!/usr/bin/env python3
"""
Portal do Pai Vinny — Backend FastAPI
Lê /data (volume compartilhado com o container do filho)
e expõe API + SSE para o dashboard web.
"""

import os, json, time, asyncio
from pathlib import Path
from datetime import datetime, date
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sse_starlette.sse import EventSourceResponse
from pydantic import BaseModel

DATA_DIR       = Path('/data')
PORTAL_SENHA   = os.environ.get('PORTAL_SENHA', 'pai123')
# Duração da sessão (min) — deve casar com SESSAO_MINUTOS de sessao.py
SESSAO_MINUTOS = int(os.environ.get('SESSAO_MINUTOS', '30'))

app = FastAPI(title="Portal Pai Vinny")

# ── Leitura de dados ──────────────────────────────────────────

def ler_json(nome, default):
    f = DATA_DIR / nome
    try:
        if f.exists():
            return json.loads(f.read_text())
    except Exception:
        pass
    return default

def ler_historico():
    return ler_json('historico.json', {"inicio": "", "sessoes": []})

def ler_dicas():
    return ler_json('dicas.json', [])

def ler_online():
    f = DATA_DIR / 'online.json'
    try:
        if f.exists() and (time.time() - f.stat().st_mtime) < 90:
            return json.loads(f.read_text())
    except Exception:
        pass
    return {"ativo": False}

def ler_trail(n=40):
    f = DATA_DIR / 'trail.log'
    try:
        if f.exists():
            linhas = [l for l in f.read_text().strip().split('\n') if l]
            return linhas[-n:]
    except Exception:
        pass
    return []

def get_estado():
    hist   = ler_historico()
    online = ler_online()
    dicas  = ler_dicas()
    trail  = ler_trail()
    hoje   = str(date.today())

    sess_hoje     = [s for s in hist.get('sessoes', []) if s.get('data') == hoje]
    comp_hoje     = [s for s in sess_hoje if s.get('completa')]
    livros_hoje   = [s for s in comp_hoje if s.get('titulo_livro')]
    total_sess    = len(hist.get('sessoes', []))
    total_livros  = len([s for s in hist.get('sessoes', []) if s.get('titulo_livro')])

    dias = 0
    if hist.get('inicio'):
        try:
            primeira = datetime.strptime(hist['inicio'], '%Y-%m-%d').date()
            dias = (date.today() - primeira).days + 1
        except Exception:
            pass

    # Tempo decorrido e restante na sessão atual
    timer = None
    if online.get('ativo') and online.get('inicio'):
        try:
            inicio_dt = datetime.fromisoformat(online['inicio'])
            elapsed   = int((datetime.now() - inicio_dt).total_seconds())
            restante  = max(0, SESSAO_MINUTOS * 60 - elapsed)
            timer = {"elapsed": elapsed, "restante": restante,
                     "inicio_iso": online['inicio']}
        except Exception:
            pass

    return {
        "online": {
            "ativo":  online.get('ativo', False),
            "sessao": online.get('sessao', 0),
            "timer":  timer,
        },
        "hoje": {
            "sessoes_usadas":   len(sess_hoje),
            "sessoes_completas": len(comp_hoje),
            "livros":           len(livros_hoje),
        },
        "total": {
            "sessoes": total_sess,
            "livros":  total_livros,
            "dias":    dias,
        },
        "historico":      hist.get('sessoes', [])[-20:][::-1],
        "trail":          trail,
        "dicas_pendentes": len([d for d in dicas if not d.get('mostrada')]),
    }

def checar(senha):
    if senha != PORTAL_SENHA:
        raise HTTPException(401, "Senha inválida")

# ── Endpoints ─────────────────────────────────────────────────

@app.get('/', response_class=HTMLResponse)
def home():
    return (Path('/app/portal.html')).read_text()

@app.get('/api/estado')
def api_estado(senha: str = ''):
    checar(senha)
    return JSONResponse(get_estado())

@app.get('/api/resumo/{idx}')
def api_resumo(idx: int, senha: str = ''):
    checar(senha)
    hist = ler_historico()
    sessoes = [s for s in hist.get('sessoes', []) if s.get('resumo')]
    if 0 <= idx < len(sessoes):
        return JSONResponse({"resumo": sessoes[idx].get('resumo', ''),
                             "titulo": sessoes[idx].get('titulo_livro', '')})
    raise HTTPException(404)

@app.get('/api/stream')
async def api_stream(request: Request, senha: str = ''):
    checar(senha)
    async def gen():
        while True:
            if await request.is_disconnected():
                break
            yield {'data': json.dumps(get_estado())}
            await asyncio.sleep(4)
    return EventSourceResponse(gen())

class DicaIn(BaseModel):
    texto: str
    tipo:  str = 'login'   # 'login' | 'realtime'

@app.post('/api/dica')
def api_dica(payload: DicaIn, senha: str = ''):
    checar(senha)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if payload.tipo == 'realtime':
        (DATA_DIR / 'mensagem.txt').write_text(payload.texto)
    else:
        dicas = ler_dicas()
        dicas.append({
            "id":        str(int(time.time())),
            "timestamp": datetime.now().isoformat(),
            "texto":     payload.texto,
            "tipo":      "login",
            "mostrada":  False,
        })
        (DATA_DIR / 'dicas.json').write_text(
            json.dumps(dicas, ensure_ascii=False, indent=2)
        )
    return {"ok": True}

@app.delete('/api/mensagem')
def limpar_mensagem(senha: str = ''):
    checar(senha)
    f = DATA_DIR / 'mensagem.txt'
    if f.exists():
        f.write_text('')
    return {"ok": True}
