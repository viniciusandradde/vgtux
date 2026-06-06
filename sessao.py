#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║         GERENCIADOR DE SESSÕES EDUCACIONAIS v2               ║
║              Minecraft Quest — Pai Vinny                     ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, sys, json, time, signal, subprocess, threading
from datetime import date, datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ═══════════════════════════════════════════════════════════════
SESSAO_MINUTOS   = int(os.environ.get('SESSAO_MINUTOS', '30'))
LEITURA_MINUTOS  = int(os.environ.get('LEITURA_MINUTOS', '30'))
SESSOES_POR_DIA  = 2
LINHAS_BASE      = 10
CICLO_DIAS       = 10
CICLO_INCREMENTO = 2

DATA_DIR      = Path('/data')
DATA_FILE     = DATA_DIR / 'historico.json'
TRAIL_FILE    = DATA_DIR / 'trail.log'
ONLINE_FILE   = DATA_DIR / 'online.json'
DICAS_FILE    = DATA_DIR / 'dicas.json'
MENSAGEM_FILE = DATA_DIR / 'mensagem.txt'

# ═══════════════════════════════════════════════════════════════
# CORES ANSI
# ═══════════════════════════════════════════════════════════════
class C:
    VERDE   = '\033[92m'
    AMARELO = '\033[93m'
    VERMELHO= '\033[91m'
    AZUL    = '\033[94m'
    MAGENTA = '\033[95m'
    CIANO   = '\033[96m'
    BRANCO  = '\033[97m'
    NEGRITO = '\033[1m'
    DIM     = '\033[2m'
    RESET   = '\033[0m'

def cor(texto, *estilos):
    return ''.join(estilos) + str(texto) + C.RESET

# ═══════════════════════════════════════════════════════════════
# MENSAGEM DO PAI VINNY
# ═══════════════════════════════════════════════════════════════
MENSAGEM_PAI = f"""{C.MAGENTA}{C.NEGRITO}
  ╔══════════════════════════════════════════════════════╗
  ║         💌  UMA MENSAGEM DO SEU PAI  💌              ║
  ╚══════════════════════════════════════════════════════╝
{C.RESET}{C.BRANCO}
  Filho,

  A vida é feita de etapas. Cada uma exige mais do que
  a anterior — e é exatamente assim que você cresce.

  Hoje você aprendeu comandos Linux. Amanhã pode ser
  código, medicina, engenharia, ou qualquer coisa que
  seu coração escolher. Mas o que nenhuma escola ensina:
  quem aprende todos os dias, nunca para de evoluir.

  Os livros que você lê constroem quem você será.
  Cada linha que você escreve de resumo é uma semente
  plantada na sua memória — ela vai crescer quando você
  menos esperar.

  Não desanime quando parecer difícil. O difícil é
  exatamente o lugar onde o crescimento acontece.
  A montanha mais alta tem a vista mais bonita.

  Cada esforço que você faz hoje, eu vejo. E me enche
  de um orgulho que não cabe no peito.

  Vai em frente. O mundo precisa do que você tem a
  oferecer. E eu estarei sempre aqui, torcendo por você.
{C.MAGENTA}{C.NEGRITO}
  Te amo muito.

                                     — Pai Vinny ❤️
{C.RESET}"""

# ═══════════════════════════════════════════════════════════════
# DADOS
# ═══════════════════════════════════════════════════════════════

def _garantir_data():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def carregar_dados():
    _garantir_data()
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {"inicio": str(date.today()), "sessoes": []}

def salvar_dados(dados):
    _garantir_data()
    with open(DATA_FILE, 'w') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def sessoes_hoje(dados):
    hoje = str(date.today())
    return [s for s in dados["sessoes"] if s.get("data") == hoje]

def calcular_linhas_minimas(dados):
    try:
        primeira = date.fromisoformat(dados["inicio"])
        dias = (date.today() - primeira).days
        return LINHAS_BASE + (dias // CICLO_DIAS) * CICLO_INCREMENTO
    except Exception:
        return LINHAS_BASE

# ═══════════════════════════════════════════════════════════════
# HEARTBEAT + MENSAGENS PARA O PORTAL
# ═══════════════════════════════════════════════════════════════

def escrever_heartbeat(num_sessao, inicio_iso, pid):
    try:
        _garantir_data()
        ONLINE_FILE.write_text(json.dumps({
            "ativo":   True,
            "sessao":  num_sessao,
            "inicio":  inicio_iso,
            "pid":     pid,
            "ts":      datetime.now().isoformat()
        }))
    except Exception:
        pass

def escrever_offline():
    try:
        _garantir_data()
        ONLINE_FILE.write_text(json.dumps({
            "ativo": False,
            "ts":    datetime.now().isoformat()
        }))
    except Exception:
        pass

def verificar_mensagem(bash_pid):
    """Lê mensagem em tempo real enviada pelo pai e exibe no terminal do filho."""
    try:
        if MENSAGEM_FILE.exists():
            content = MENSAGEM_FILE.read_text().strip()
            if content:
                MENSAGEM_FILE.write_text('')
                msg = (
                    f'\n\n{C.MAGENTA}{C.NEGRITO}'
                    f'  ╔══════════════════════════════════════╗\n'
                    f'  ║  💬  MENSAGEM DO SEU PAI VINNY  💬  ║\n'
                    f'  ╚══════════════════════════════════════╝{C.RESET}\n'
                    f'  {C.BRANCO}{content}{C.RESET}\n\n'
                )
                # Escreve diretamente no terminal do processo bash
                try:
                    with open(f'/proc/{bash_pid}/fd/1', 'w') as tty:
                        tty.write(msg)
                except Exception:
                    pass
    except Exception:
        pass

def mostrar_dicas_login():
    """Exibe as dicas enfileiradas pelo pai que ainda não foram mostradas."""
    try:
        _garantir_data()
        if not DICAS_FILE.exists():
            return
        dicas = json.loads(DICAS_FILE.read_text())
        pendentes = [d for d in dicas if not d.get('mostrada')]
        if not pendentes:
            return

        limpar()
        print(f'\n{cor("  💬 MENSAGENS DO SEU PAI:", C.MAGENTA, C.NEGRITO)}\n')
        separador('─', 58, C.MAGENTA)
        for d in pendentes:
            print(f'\n  {cor(d["texto"], C.BRANCO)}')
            d['mostrada'] = True
        separador('─', 58, C.MAGENTA)

        DICAS_FILE.write_text(json.dumps(dicas, ensure_ascii=False, indent=2))
        pausar("  Pressione ENTER para continuar...")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# UTILITÁRIOS DE TELA
# ═══════════════════════════════════════════════════════════════

def limpar():
    os.system('clear')
    os.system('stty sane 2>/dev/null')

def separador(char='─', n=58, cor_char=C.AZUL):
    print(cor_char + char * n + C.RESET)

def pausar(msg="  Pressione ENTER para continuar..."):
    try:
        input(cor(f"\n{msg}", C.DIM))
    except (EOFError, KeyboardInterrupt):
        pass

def mostrar_biblioteca(dados):
    sessoes_com_resumo = [s for s in dados["sessoes"] if s.get("titulo_livro")]
    if not sessoes_com_resumo:
        return
    print(f"\n{cor('  📚 SUA BIBLIOTECA:', C.VERDE, C.NEGRITO)}")
    separador('─', 58, C.VERDE)
    for i, s in enumerate(sessoes_com_resumo[-8:], 1):
        idx     = cor(f'{i:2}.', C.DIM)
        titulo  = cor(s.get('titulo_livro', '?'), C.BRANCO)
        linhas  = cor(f"{s.get('linhas_resumo', '?')} linhas", C.AMARELO)
        data    = cor(f"[{s.get('data', '')}]", C.DIM)
        print(f"  {idx}  {titulo}  {linhas}  {data}")
    total = cor(f"Total: {len(sessoes_com_resumo)} livro(s)  🏆", C.CIANO)
    print(f"\n  {total}")
    separador('─', 58, C.VERDE)

# ═══════════════════════════════════════════════════════════════
# SESSÃO BASH COM TIMER
# ═══════════════════════════════════════════════════════════════

def executar_sessao_bash(minutos, num_sessao=1, inicio_iso=None):
    resultado = {'motivo': 'saiu'}
    if inicio_iso is None:
        inicio_iso = datetime.now().isoformat()

    proc = subprocess.Popen(['/bin/bash', '-i'])

    # Thread: heartbeat a cada 30 s
    def heartbeat_loop():
        while proc.poll() is None:
            escrever_heartbeat(num_sessao, inicio_iso, proc.pid)
            time.sleep(30)
        escrever_offline()

    # Thread: verifica mensagem do pai a cada 5 s
    def mensagem_loop():
        while proc.poll() is None:
            verificar_mensagem(proc.pid)
            time.sleep(5)

    def aviso_cinco():
        try:
            with open(f'/proc/{proc.pid}/fd/1', 'w') as tty:
                tty.write(
                    f'\n\n{C.AMARELO}{C.NEGRITO}'
                    f'  ⚠️   5 minutos restantes na sessão!{C.RESET}\n\n'
                )
        except Exception:
            pass

    def encerrar():
        resultado['motivo'] = 'timeout'
        try:
            proc.terminate()
        except ProcessLookupError:
            pass

    # Escreve estado inicial antes de iniciar as threads
    escrever_heartbeat(num_sessao, inicio_iso, proc.pid)

    th = threading.Thread(target=heartbeat_loop, daemon=True)
    tm = threading.Thread(target=mensagem_loop,  daemon=True)
    th.start()
    tm.start()

    t_aviso = threading.Timer((minutos - 5) * 60, aviso_cinco)
    t_fim   = threading.Timer(minutos * 60, encerrar)
    t_aviso.start()
    t_fim.start()

    try:
        proc.wait()
    except KeyboardInterrupt:
        proc.terminate()
    finally:
        t_aviso.cancel()
        t_fim.cancel()

    escrever_offline()
    os.system('stty sane 2>/dev/null')
    return resultado['motivo']

# ═══════════════════════════════════════════════════════════════
# TEMPORIZADOR DE LEITURA
# ═══════════════════════════════════════════════════════════════

def temporizador_leitura(minutos):
    limpar()
    separador('═', 58, C.MAGENTA)
    print(cor('  📖  TEMPO DE LEITURA', C.MAGENTA, C.NEGRITO))
    separador('═', 58, C.MAGENTA)
    print(f"""
  Muito bem! Agora é hora de alimentar a mente.

  👉  Vá até sua estante de livros.
  👉  Escolha um livro e leia com atenção.
  👉  Quando terminar, volte aqui para escrever o resumo.

  {cor('Quando estiver com o livro em mãos, pressione ENTER', C.VERDE)}
  {cor('para iniciar o cronômetro.', C.VERDE)}
""")
    pausar("  Pressione ENTER para começar o cronômetro de leitura...")

    segundos_total = minutos * 60
    inicio = time.time()
    avisos = {20*60: "💡 A leitura ativa novos caminhos no cérebro!",
              10*60: "🔥 Metade do caminho! Continue focado!",
               5*60: "⭐ Últimos 5 minutos — absorva cada palavra!"}

    print()
    try:
        for restante in range(segundos_total, 0, -1):
            elapsed = segundos_total - restante
            pct    = int((elapsed / segundos_total) * 32)
            barra  = cor('█' * pct, C.MAGENTA) + cor('░' * (32 - pct), C.DIM)
            mins, secs = divmod(restante, 60)
            sys.stdout.write(
                f"\r  ⏱  {cor(f'{mins:02d}:{secs:02d}', C.AMARELO, C.NEGRITO)} "
                f"restantes  [{barra}]  "
            )
            sys.stdout.flush()
            if restante in avisos:
                sys.stdout.write(f"\r  {cor(avisos[restante], C.CIANO)}" + ' ' * 20 + '\n')
                sys.stdout.flush()
                time.sleep(2)
            else:
                time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n  {cor('Cronômetro pausado. Aguardando o tempo restante...', C.AMARELO)}")
        restante_real = max(0, segundos_total - int(time.time() - inicio))
        if restante_real > 0:
            time.sleep(restante_real)

    sys.stdout.write(
        f"\r  {cor('✅ Tempo de leitura concluído! Incrível!', C.VERDE, C.NEGRITO)}"
        + ' ' * 30 + '\n\n'
    )
    sys.stdout.flush()

# ═══════════════════════════════════════════════════════════════
# COLETA E VALIDAÇÃO DO RESUMO
# ═══════════════════════════════════════════════════════════════

def coletar_resumo(linhas_minimas):
    limpar()
    separador('═', 58, C.VERDE)
    print(cor('  ✍️   RESUMO DO LIVRO', C.VERDE, C.NEGRITO))
    separador('═', 58, C.VERDE)
    print(f"""
  Escreva o que você aprendeu com o livro.

  Regras:
    ✅  Mínimo de {cor(str(linhas_minimas), C.AMARELO, C.NEGRITO)} linhas
    ✅  Cada linha com pelo menos 20 caracteres
    ✅  Com suas próprias palavras

  Quando terminar, escreva {cor('FIM', C.VERMELHO, C.NEGRITO)} numa linha sozinha.
""")
    separador('─', 58)

    while True:
        try:
            titulo_livro = input(f"\n  {cor('Título do livro:', C.CIANO)} ").strip()
        except (EOFError, KeyboardInterrupt):
            titulo_livro = "Livro sem título"
            break
        if titulo_livro:
            break
        print(cor("  ⚠️  Por favor, informe o título.", C.AMARELO))

    print(f"\n  {cor('Escreva seu resumo linha por linha:', C.VERDE)}\n")
    linhas_resumo = []
    num_linha = 1

    while True:
        try:
            linha = input(f"  {cor(f'Linha {num_linha:2}:', C.DIM)} ")
        except (EOFError, KeyboardInterrupt):
            break

        if linha.strip().upper() == "FIM":
            break
        if not linha.strip():
            print(cor("  (linha em branco ignorada)", C.DIM))
            continue
        if len(linha.strip()) < 20:
            print(cor("  ❌  Linha muito curta. Explique melhor e tente de novo.", C.VERMELHO))
            continue

        linhas_resumo.append(linha.strip())
        faltam = max(0, linhas_minimas - len(linhas_resumo))
        if faltam > 0:
            print(cor(f"  ✔  {len(linhas_resumo)}/{linhas_minimas} — faltam {faltam}!", C.DIM))
        else:
            extra = len(linhas_resumo) - linhas_minimas
            bonus = f"  (+{extra} bônus! 🌟)" if extra else ""
            print(cor(f"  ✔  Linha {len(linhas_resumo)} — mínimo atingido!{bonus}", C.VERDE))
        num_linha += 1

    if len(linhas_resumo) < linhas_minimas:
        limpar()
        print(f"\n{cor('  ❌  Resumo incompleto!', C.VERMELHO, C.NEGRITO)}")
        print(f"  Você escreveu {len(linhas_resumo)} linha(s) mas precisa de {linhas_minimas}.")
        pausar()
        return coletar_resumo(linhas_minimas)

    limpar()
    separador('═', 58, C.VERDE)
    print(cor('  ✅  RESUMO APROVADO!', C.VERDE, C.NEGRITO))
    separador('═', 58, C.VERDE)
    print(f"""
  📖 Livro:  {cor(titulo_livro, C.BRANCO, C.NEGRITO)}
  📝 Linhas: {cor(str(len(linhas_resumo)), C.AMARELO, C.NEGRITO)}

  Incrível! Você registrou {len(linhas_resumo)} ideias na sua memória.
""")
    return titulo_livro, '\n'.join(linhas_resumo), len(linhas_resumo)

# ═══════════════════════════════════════════════════════════════
# TELAS
# ═══════════════════════════════════════════════════════════════

def tela_inicio_sessao(dados, numero_sessao):
    lmin        = calcular_linhas_minimas(dados)
    total_livros= len([s for s in dados["sessoes"] if s.get("titulo_livro")])
    total_sess  = len(dados["sessoes"])
    limpar()
    separador('═', 58, C.VERDE)
    print(cor(f'  ⚔   MINECRAFT QUEST — SESSÃO {numero_sessao} DE {SESSOES_POR_DIA}', C.VERDE, C.NEGRITO))
    separador('═', 58, C.VERDE)
    print(f"""
  {cor('Bem-vindo, Explorador!', C.BRANCO, C.NEGRITO)}

  🗓  Data:            {cor(str(date.today()), C.CIANO)}
  ⏱  Duração:         {cor(f'{SESSAO_MINUTOS} minutos', C.AMARELO)}
  📚  Livros lidos:    {cor(str(total_livros), C.VERDE)}
  🏆  Total sessões:   {cor(str(total_sess), C.VERDE)}
  📝  Linhas mínimas:  {cor(str(lmin), C.AMARELO)} {cor(f'(+{CICLO_INCREMENTO} a cada {CICLO_DIAS} dias)', C.DIM)}
""")
    separador('─', 58)
    mostrar_biblioteca(dados)
    pausar("  Pressione ENTER para iniciar a sessão...")

def tela_sessao_encerrada(motivo):
    limpar()
    separador('═', 58, C.AMARELO)
    print(cor('  ⏰  SESSÃO ENCERRADA', C.AMARELO, C.NEGRITO))
    separador('═', 58, C.AMARELO)
    if motivo == 'timeout':
        print(f"""
  {cor('Seu tempo de exploração acabou!', C.VERMELHO, C.NEGRITO)}

  Para desbloquear sua segunda sessão:

    📖  Vá até sua estante de livros
    ⏱   Leia por {cor(str(LEITURA_MINUTOS), C.AMARELO)} minutos
    ✍️   Escreva um resumo e ganhe mais {cor(str(SESSAO_MINUTOS), C.VERDE)} min!
""")

def tela_limite_diario(dados):
    limpar()
    separador('═', 58, C.MAGENTA)
    print(cor('  🌙  FIM DO DIA — LIMITE ATINGIDO', C.MAGENTA, C.NEGRITO))
    separador('═', 58, C.MAGENTA)
    total_livros = len([s for s in dados["sessoes"] if s.get("titulo_livro")])
    print(f"""
  Você usou suas {cor(str(SESSOES_POR_DIA), C.AMARELO)} sessões de hoje. Incrível!

  📊 Hoje:  {cor('2', C.VERDE)} sessões  •  {cor(str(SESSOES_POR_DIA * SESSAO_MINUTOS), C.VERDE)} minutos  •  1 livro lido
  📚 Total de livros na biblioteca: {cor(str(total_livros), C.AMARELO, C.NEGRITO)}

  Volte amanhã para novas aventuras! 🗡️
""")
    separador('─', 58)

# ═══════════════════════════════════════════════════════════════
# FLUXO PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def main():
    # SSH não-interativo (scp, rsync...)
    if len(sys.argv) > 1 and sys.argv[1] == '-c':
        os.execv('/bin/bash', ['/bin/bash'] + sys.argv[1:])
        return

    _garantir_data()
    dados = carregar_dados()

    # Dicas do pai enfileiradas (aparecem uma vez ao login)
    mostrar_dicas_login()

    hoje  = sessoes_hoje(dados)
    completas = [s for s in hoje if s.get("completa")]

    # ── Limite diário ──
    if len(completas) >= SESSOES_POR_DIA:
        tela_limite_diario(dados)
        print(MENSAGEM_PAI)
        pausar()
        sys.exit(0)

    # ── Resumo pendente de sessão anterior (desconectou no meio) ──
    incompleta = next((s for s in hoje if not s.get("completa")), None)
    if incompleta and not incompleta.get("resumo_enviado"):
        limpar()
        print(cor('\n  ⚠️   Resumo pendente da última sessão!', C.AMARELO, C.NEGRITO))
        print('  Complete o gate de leitura para continuar.\n')
        pausar()
        temporizador_leitura(LEITURA_MINUTOS)
        lmin = calcular_linhas_minimas(dados)
        titulo, resumo, n = coletar_resumo(lmin)
        incompleta.update({"titulo_livro": titulo, "resumo": resumo,
                           "linhas_resumo": n, "resumo_enviado": True, "completa": True})
        salvar_dados(dados)
        hoje      = sessoes_hoje(dados)
        completas = [s for s in hoje if s.get("completa")]

    num_sessao = len(completas) + 1

    # ── Inicia Sessão 1 ──
    tela_inicio_sessao(dados, num_sessao)

    inicio_iso = datetime.now().isoformat()
    registro   = {"data": str(date.today()), "numero_do_dia": num_sessao,
                  "inicio": inicio_iso, "completa": False, "resumo_enviado": False}
    dados["sessoes"].append(registro)
    salvar_dados(dados)

    motivo = executar_sessao_bash(SESSAO_MINUTOS, num_sessao, inicio_iso)
    registro["fim"] = datetime.now().isoformat()
    salvar_dados(dados)

    # ── Gate: leitura + resumo ──
    if num_sessao < SESSOES_POR_DIA:
        tela_sessao_encerrada(motivo)
        print(MENSAGEM_PAI)
        pausar("  Pressione ENTER para iniciar o cronômetro de leitura...")

        temporizador_leitura(LEITURA_MINUTOS)

        lmin = calcular_linhas_minimas(dados)
        titulo, resumo, n_linhas = coletar_resumo(lmin)
        registro.update({"titulo_livro": titulo, "resumo": resumo,
                         "linhas_resumo": n_linhas, "resumo_enviado": True, "completa": True})
        salvar_dados(dados)

        limpar()
        print(f"\n{cor('  📚 Livro adicionado à sua biblioteca!', C.VERDE, C.NEGRITO)}\n")
        mostrar_biblioteca(dados)
        pausar(f"\n  Pressione ENTER para iniciar a sessão {num_sessao + 1} de {SESSAO_MINUTOS} min...")

        # ── Sessão 2 ──
        tela_inicio_sessao(dados, num_sessao + 1)
        inicio2 = datetime.now().isoformat()
        r2 = {"data": str(date.today()), "numero_do_dia": num_sessao + 1,
              "inicio": inicio2, "completa": False, "resumo_enviado": True}
        dados["sessoes"].append(r2)
        salvar_dados(dados)

        executar_sessao_bash(SESSAO_MINUTOS, num_sessao + 1, inicio2)
        r2.update({"fim": datetime.now().isoformat(), "completa": True})
        salvar_dados(dados)
    else:
        registro.update({"completa": True})
        salvar_dados(dados)

    # ── Fim do dia ──
    tela_limite_diario(dados)
    print(MENSAGEM_PAI)
    pausar()

# ═══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        os.system('stty sane 2>/dev/null')
        escrever_offline()
        print(cor('\n\n  Até a próxima!\n', C.DIM))
        sys.exit(0)
    except Exception as e:
        os.system('stty sane 2>/dev/null')
        escrever_offline()
        print(cor(f'\n  [ERRO]: {e}', C.VERMELHO))
        print(cor('  Abrindo bash de emergência...', C.AMARELO))
        os.execv('/bin/bash', ['/bin/bash', '-i'])
