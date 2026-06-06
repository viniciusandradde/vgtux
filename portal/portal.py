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
TOTAL_ETAPAS   = int(os.environ.get('TOTAL_ETAPAS', '20'))
ETAPAS_POR_DIA = int(os.environ.get('ETAPAS_POR_DIA', '2'))

RESUMO_PEND    = DATA_DIR / 'resumo_pendente.json'
RESUMO_ENVIADO = DATA_DIR / 'resumo_enviado.json'

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
    return ler_json('historico.json', {"inicio": "", "etapa_atual": 1, "etapas": []})

def _etapas(hist):
    """Lista de etapas (compatível com o formato antigo 'sessoes')."""
    return hist.get('etapas', hist.get('sessoes', []))

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

    etapas        = _etapas(hist)
    etapa_atual   = hist.get('etapa_atual', len([e for e in etapas if e.get('completa')]) + 1)
    sess_hoje     = [s for s in etapas if s.get('data') == hoje]
    comp_hoje     = [s for s in sess_hoje if s.get('completa')]
    livros_hoje   = [s for s in comp_hoje if s.get('titulo_livro')]
    total_sess    = len([e for e in etapas if e.get('completa')])
    total_livros  = len([s for s in etapas if s.get('titulo_livro')])

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
            "sessoes":      total_sess,
            "livros":       total_livros,
            "dias":         dias,
            "etapa_atual":  etapa_atual,
            "etapas_total": TOTAL_ETAPAS,
        },
        "historico":      etapas[-20:][::-1],
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
    etapas = [s for s in _etapas(hist) if s.get('resumo')]
    if 0 <= idx < len(etapas):
        return JSONResponse({"resumo": etapas[idx].get('resumo', ''),
                             "titulo": etapas[idx].get('titulo_livro', '')})
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

# ── Resumo do livro enviado pelo filho (via token, sem senha do pai) ──

def ler_pendente():
    try:
        if RESUMO_PEND.exists():
            return json.loads(RESUMO_PEND.read_text())
    except Exception:
        pass
    return None

def _linhas_validas(resumo):
    return [l.strip() for l in resumo.splitlines()
            if l.strip() and len(l.strip()) >= 20]

@app.get('/resumo', response_class=HTMLResponse)
def pagina_resumo(t: str = ''):
    pend = ler_pendente()
    valido = bool(pend and pend.get('token') == t and not pend.get('enviado'))
    lmin   = pend.get('linhas_minimas', 10) if pend else 10
    etapa  = pend.get('etapa', '?') if pend else '?'
    html = _RESUMO_HTML
    html = html.replace('__TOKEN__', t or '')
    html = html.replace('__LMIN__', str(lmin))
    html = html.replace('__ETAPA__', str(etapa))
    html = html.replace('__VALIDO__', 'true' if valido else 'false')
    return html

class ResumoIn(BaseModel):
    token:  str
    titulo: str
    resumo: str

@app.post('/api/resumo-enviar')
def enviar_resumo(payload: ResumoIn):
    pend = ler_pendente()
    if not pend or pend.get('token') != payload.token or pend.get('enviado'):
        raise HTTPException(400, "Link inválido ou já utilizado. Volte ao terminal.")
    lmin   = int(pend.get('linhas_minimas', 10))
    titulo = payload.titulo.strip() or "Livro sem título"
    linhas = _linhas_validas(payload.resumo)
    if len(linhas) < lmin:
        return JSONResponse(status_code=422, content={
            "ok": False,
            "erro": f"Faltam linhas: você tem {len(linhas)} de {lmin} "
                    f"(cada linha precisa de pelo menos 20 caracteres).",
            "linhas": len(linhas), "minimo": lmin,
        })
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    RESUMO_ENVIADO.write_text(json.dumps({
        "token":  payload.token,
        "etapa":  pend.get('etapa'),
        "titulo": titulo,
        "resumo": '\n'.join(linhas),
        "linhas": len(linhas),
        "ts":     datetime.now().isoformat(),
    }, ensure_ascii=False))
    pend['enviado'] = True
    RESUMO_PEND.write_text(json.dumps(pend, ensure_ascii=False))
    return {"ok": True, "linhas": len(linhas)}


# ── Página HTML do resumo (mobile-first; auth por token) ──────────
_RESUMO_HTML = r"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<title>Resumo do Livro — Minecraft Quest</title>
<style>
  :root { --verde:#16a34a; --verde2:#22c55e; --bg:#0f1117; --card:#171a23;
          --txt:#e6e8ee; --dim:#9aa3b2; --erro:#f87171; --borda:#262b3a; }
  * { box-sizing:border-box; margin:0; padding:0; }
  body { font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;
         background:var(--bg); color:var(--txt); min-height:100vh; padding:18px; }
  .wrap { max-width:620px; margin:0 auto; }
  header { text-align:center; margin:8px 0 18px; }
  header .tag { color:var(--verde2); font-weight:700; letter-spacing:1px; font-size:13px; }
  h1 { font-size:22px; margin-top:6px; }
  .card { background:var(--card); border:1px solid var(--borda); border-radius:14px;
          padding:18px; margin-bottom:14px; }
  label { display:block; font-size:14px; color:var(--dim); margin-bottom:6px; }
  input, textarea { width:100%; background:#0b0d13; color:var(--txt);
          border:1px solid var(--borda); border-radius:10px; padding:12px;
          font-size:16px; font-family:inherit; }
  textarea { min-height:240px; resize:vertical; line-height:1.6; }
  .regras { font-size:13px; color:var(--dim); line-height:1.7; }
  .contador { font-size:14px; margin-top:8px; font-weight:600; }
  .ok { color:var(--verde2); } .falta { color:var(--erro); }
  button { width:100%; background:var(--verde); color:#fff; border:0; border-radius:12px;
           padding:15px; font-size:17px; font-weight:700; margin-top:6px; cursor:pointer; }
  button:disabled { opacity:.5; }
  .msg { margin-top:12px; font-size:14px; min-height:20px; }
  .erro { color:var(--erro); } .sucesso { color:var(--verde2); }
  .final { text-align:center; padding:30px 12px; }
  .final .emoji { font-size:54px; }
  .invalido { text-align:center; color:var(--erro); padding:30px 12px; }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <div class="tag">⚔ MINECRAFT QUEST</div>
    <h1>✍️ Resumo do Livro — Etapa __ETAPA__</h1>
  </header>

  <div id="form-area">
    <div class="card">
      <div class="regras">
        📖 Escreva com <b>suas próprias palavras</b> o que você aprendeu.<br>
        ✅ Mínimo de <b>__LMIN__ linhas</b> &nbsp;•&nbsp; cada linha com <b>20+ caracteres</b>.
      </div>
    </div>
    <div class="card">
      <label for="titulo">Título do livro</label>
      <input id="titulo" type="text" placeholder="Ex.: O Pequeno Príncipe" autocomplete="off" />
    </div>
    <div class="card">
      <label for="resumo">Seu resumo (uma ideia por linha)</label>
      <textarea id="resumo" placeholder="Escreva uma linha por ideia..."></textarea>
      <div class="contador" id="contador">0 / __LMIN__ linhas válidas</div>
    </div>
    <button id="btn" onclick="enviar()">📤 Enviar resumo</button>
    <div class="msg" id="msg"></div>
  </div>

  <div id="sucesso-area" class="final" style="display:none">
    <div class="emoji">🎉</div>
    <h1>Resumo enviado!</h1>
    <p style="color:var(--dim);margin-top:10px">
      Pode voltar para o terminal — sua etapa vai liberar sozinha. 🟢
    </p>
  </div>

  <div id="invalido-area" class="invalido" style="display:none">
    <div class="emoji" style="font-size:48px">⚠️</div>
    <h1>Link inválido ou já usado</h1>
    <p style="color:var(--dim);margin-top:10px">
      Volte ao terminal e gere o resumo novamente.
    </p>
  </div>
</div>

<script>
  var TOKEN = "__TOKEN__";
  var LMIN  = parseInt("__LMIN__", 10);
  var VALIDO = (__VALIDO__);

  if (!VALIDO) {
    document.getElementById('form-area').style.display = 'none';
    document.getElementById('invalido-area').style.display = 'block';
  }

  function linhasValidas() {
    var t = document.getElementById('resumo').value;
    return t.split('\n').map(function(l){return l.trim();})
            .filter(function(l){ return l.length >= 20; });
  }
  function atualizar() {
    var n = linhasValidas().length;
    var c = document.getElementById('contador');
    c.textContent = n + ' / ' + LMIN + ' linhas válidas';
    c.className = 'contador ' + (n >= LMIN ? 'ok' : 'falta');
  }
  document.getElementById('resumo').addEventListener('input', atualizar);

  function enviar() {
    var titulo = document.getElementById('titulo').value.trim();
    var resumo = document.getElementById('resumo').value;
    var msg = document.getElementById('msg');
    msg.className = 'msg';
    if (!titulo) { msg.textContent = '⚠️ Escreva o título do livro.'; msg.className='msg erro'; return; }
    if (linhasValidas().length < LMIN) {
      msg.className='msg erro';
      msg.textContent = '⚠️ Faltam linhas válidas (' + linhasValidas().length + '/' + LMIN + ').';
      return;
    }
    var btn = document.getElementById('btn');
    btn.disabled = true; msg.textContent = 'Enviando...';
    fetch('/api/resumo-enviar', {
      method:'POST', headers:{'Content-Type':'application/json'},
      body: JSON.stringify({token:TOKEN, titulo:titulo, resumo:resumo})
    }).then(function(r){ return r.json().then(function(d){ return {s:r.status, d:d}; }); })
      .then(function(res){
        if (res.s === 200 && res.d.ok) {
          document.getElementById('form-area').style.display='none';
          document.getElementById('sucesso-area').style.display='block';
        } else {
          btn.disabled = false; msg.className='msg erro';
          msg.textContent = '❌ ' + (res.d.erro || 'Não foi possível enviar.');
        }
      }).catch(function(){
        btn.disabled=false; msg.className='msg erro';
        msg.textContent='❌ Erro de conexão. Tente de novo.';
      });
  }
</script>
</body>
</html>
"""
