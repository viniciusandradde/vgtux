#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║         GERENCIADOR DE SESSÕES EDUCACIONAIS v1.1            ║
║              Minecraft Quest — Pai Vinny                     ║
║   Jornada de 20 etapas (desafios Linux), máx. 2 por dia.    ║
╚══════════════════════════════════════════════════════════════╝
"""

import os, sys, json, time, secrets, shutil, subprocess, threading
from datetime import date, datetime
from pathlib import Path

# ═══════════════════════════════════════════════════════════════
# CONFIGURAÇÕES
# ═══════════════════════════════════════════════════════════════
SESSAO_MINUTOS   = int(os.environ.get('SESSAO_MINUTOS', '30'))
LEITURA_MINUTOS  = int(os.environ.get('LEITURA_MINUTOS', '30'))
ETAPAS_POR_DIA   = int(os.environ.get('ETAPAS_POR_DIA', '2'))
TOTAL_ETAPAS     = 20
LINHAS_BASE      = 10
CICLO_DIAS       = 10
CICLO_INCREMENTO = 2

ADMIN_DOMAIN = os.environ.get('ADMIN_DOMAIN', 'adminvgtux.vsanexus.com')

DATA_DIR        = Path('/data')
DATA_FILE       = DATA_DIR / 'historico.json'
TRAIL_FILE      = DATA_DIR / 'trail.log'
ONLINE_FILE     = DATA_DIR / 'online.json'
DICAS_FILE      = DATA_DIR / 'dicas.json'
MENSAGEM_FILE   = DATA_DIR / 'mensagem.txt'
RESUMO_PEND     = DATA_DIR / 'resumo_pendente.json'
RESUMO_ENVIADO  = DATA_DIR / 'resumo_enviado.json'
RESET_FLAG      = DATA_DIR / 'reset.flag'

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
# AS 20 ETAPAS — desafios Linux progressivos
# Cada etapa: título, missão, dica, comando de verificação (bash),
# e uma pista (teaser) da próxima. A verificação roda como o jogador,
# com $HOME apontando para a casa dele.
# ═══════════════════════════════════════════════════════════════
ETAPAS = [
    {  # 1
        "titulo": "Primeiro Contato",
        "missao": "Toda aventura começa com um lar. Crie uma pasta chamada\n"
                  "  'aventura' na sua casa — será sua base de operações.",
        "dica":   "Use:  mkdir aventura     (veja onde está com  pwd  e  ls )",
        "verificar": 'test -d "$HOME/aventura"',
        "teaser": "Toda base precisa de um diário de bordo...",
    },
    {  # 2
        "titulo": "O Diário de Bordo",
        "missao": "Entre na pasta 'aventura' e crie um arquivo vazio\n"
                  "  chamado 'diario.txt'.",
        "dica":   "Use:  cd aventura   e depois   touch diario.txt",
        "verificar": 'test -f "$HOME/aventura/diario.txt"',
        "teaser": "Um diário em branco não conta história nenhuma...",
    },
    {  # 3
        "titulo": "As Primeiras Palavras",
        "missao": "Escreva o seu nome dentro do 'diario.txt'.\n"
                  "  O arquivo não pode mais ficar vazio!",
        "dica":   'Use:  echo "Meu Nome" > diario.txt',
        "verificar": 'test -s "$HOME/aventura/diario.txt"',
        "teaser": "Aprenda a ler o que você mesmo escreveu...",
    },
    {  # 4
        "titulo": "O Leitor",
        "missao": "Leia o diario.txt na tela com 'cat'. Depois crie um novo\n"
                  "  arquivo 'dia2.txt' com uma frase sobre seu dia.",
        "dica":   'Use:  cat diario.txt    e depois    echo "Hoje eu..." > dia2.txt',
        "verificar": 'test -s "$HOME/aventura/dia2.txt"',
        "teaser": "Heróis sempre guardam uma cópia de segurança...",
    },
    {  # 5
        "titulo": "Cópia de Segurança",
        "missao": "Faça uma cópia do 'diario.txt' chamada 'backup.txt'.",
        "dica":   "Use:  cp diario.txt backup.txt",
        "verificar": 'test -f "$HOME/aventura/backup.txt"',
        "teaser": "Às vezes um nome precisa mudar...",
    },
    {  # 6
        "titulo": "O Renomeador",
        "missao": "Renomeie 'dia2.txt' para 'memorias.txt'\n"
                  "  (o dia2.txt deve deixar de existir).",
        "dica":   "Use:  mv dia2.txt memorias.txt",
        "verificar": 'test -f "$HOME/aventura/memorias.txt" && ! test -f "$HOME/aventura/dia2.txt"',
        "teaser": "Um bom explorador mantém seus tesouros organizados...",
    },
    {  # 7
        "titulo": "O Organizador",
        "missao": "Crie uma pasta 'tesouros' dentro de aventura e mova o\n"
                  "  'backup.txt' para dentro dela.",
        "dica":   "Use:  mkdir tesouros   e depois   mv backup.txt tesouros/",
        "verificar": 'test -f "$HOME/aventura/tesouros/backup.txt"',
        "teaser": "Quantas coisas você consegue listar?",
    },
    {  # 8
        "titulo": "A Lista",
        "missao": "Crie 'lista.txt' com pelo menos 5 linhas — 5 coisas\n"
                  "  de que você gosta, uma por linha.",
        "dica":   'Use várias vezes:  echo "futebol" >> lista.txt  (>> adiciona)',
        "verificar": 'test "$(wc -l < "$HOME/aventura/lista.txt" 2>/dev/null || echo 0)" -ge 5',
        "teaser": "E se você precisar PROCURAR algo no meio de tudo?",
    },
    {  # 9
        "titulo": "O Caçador (grep)",
        "missao": "Procure uma palavra dentro de 'lista.txt' usando grep e\n"
                  "  salve o que encontrar em 'achado.txt'.",
        "dica":   "Use:  grep palavra lista.txt > achado.txt",
        "verificar": 'test -f "$HOME/aventura/achado.txt"',
        "teaser": "Hora de criar seu primeiro feitiço executável...",
    },
    {  # 10
        "titulo": "O Pequeno Feiticeiro",
        "missao": "Crie um script 'ola.sh' que imprime uma saudação e\n"
                  "  torne-o executável.",
        "dica":   "echo 'echo Ola, mundo' > ola.sh   e depois   chmod +x ola.sh",
        "verificar": 'test -x "$HOME/aventura/ola.sh"',
        "teaser": "Um feitiço só tem valor quando é lançado...",
    },
    {  # 11
        "titulo": "Lançando o Feitiço",
        "missao": "Execute o 'ola.sh' e guarde a saída dele em 'saida.txt'.",
        "dica":   "Use:  ./ola.sh > saida.txt",
        "verificar": 'test -s "$HOME/aventura/saida.txt"',
        "teaser": "Que horas são no mundo da máquina?",
    },
    {  # 12
        "titulo": "O Relógio do Sistema",
        "missao": "Salve a data e a hora atuais dentro de 'tempo.txt'.",
        "dica":   "Use:  date > tempo.txt",
        "verificar": 'test -s "$HOME/aventura/tempo.txt"',
        "teaser": "Comandos podem se unir como peças de LEGO (|)...",
    },
    {  # 13
        "titulo": "A Engrenagem (pipe)",
        "missao": "Conte quantos arquivos existem na pasta e salve o número\n"
                  "  em 'quantos.txt' — ligando dois comandos com um '|'.",
        "dica":   "Use:  ls | wc -l > quantos.txt",
        "verificar": 'test -s "$HOME/aventura/quantos.txt"',
        "teaser": "A máquina pode guardar segredos em variáveis...",
    },
    {  # 14
        "titulo": "O Segredo Guardado",
        "missao": "Crie uma variável com o nome do seu herói e use echo para\n"
                  "  gravar esse valor em 'heroi.txt'.",
        "dica":   'Use:  HEROI=Steve   e depois   echo "$HEROI" > heroi.txt',
        "verificar": 'test -s "$HOME/aventura/heroi.txt"',
        "teaser": "E se um tesouro estiver escondido em qualquer lugar?",
    },
    {  # 15
        "titulo": "O Mapa do Tesouro (find)",
        "missao": "Use 'find' para listar todos os arquivos .txt e salve esse\n"
                  "  mapa em 'mapa.txt'.",
        "dica":   'Use:  find . -name "*.txt" > mapa.txt',
        "verificar": 'test -s "$HOME/aventura/mapa.txt"',
        "teaser": "Ordem traz clareza — coloque tudo em ordem...",
    },
    {  # 16
        "titulo": "A Ordem (sort)",
        "missao": "Ordene as linhas de 'lista.txt' em ordem alfabética e\n"
                  "  salve o resultado em 'ordenado.txt'.",
        "dica":   "Use:  sort lista.txt > ordenado.txt",
        "verificar": 'test -s "$HOME/aventura/ordenado.txt"',
        "teaser": "Quem é você dentro desta máquina?",
    },
    {  # 17
        "titulo": "Quem Sou Eu?",
        "missao": "Descubra o nome do seu usuário no sistema e salve-o\n"
                  "  em 'eu.txt'.",
        "dica":   "Use:  whoami > eu.txt",
        "verificar": 'test -s "$HOME/aventura/eu.txt"',
        "teaser": "Tesouros viajam melhor quando empacotados...",
    },
    {  # 18
        "titulo": "O Empacotador (tar)",
        "missao": "Empacote a pasta 'tesouros' inteira em um arquivo\n"
                  "  chamado 'tesouros.tar'.",
        "dica":   "Use:  tar -cf tesouros.tar tesouros",
        "verificar": 'test -f "$HOME/aventura/tesouros.tar"',
        "teaser": "Junte suas histórias numa só...",
    },
    {  # 19
        "titulo": "A Grande União",
        "missao": "Junte o conteúdo de 'diario.txt' e 'lista.txt' em um único\n"
                  "  arquivo chamado 'tudo.txt'.",
        "dica":   "Use:  cat diario.txt lista.txt > tudo.txt",
        "verificar": 'test -s "$HOME/aventura/tudo.txt"',
        "teaser": "O FINAL está próximo. Prepare sua conquista...",
    },
    {  # 20
        "titulo": "A Conquista Final",
        "missao": "Você chegou ao fim da jornada! Crie 'conquista.txt' e\n"
                  "  escreva a frase:  COMPLETEI A JORNADA",
        "dica":   'Use:  echo "COMPLETEI A JORNADA" > conquista.txt',
        "verificar": 'grep -qi "completei a jornada" "$HOME/aventura/conquista.txt" 2>/dev/null',
        "teaser": "",
    },
]

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
    dados = {"inicio": str(date.today()), "etapa_atual": 1, "etapas": []}
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE) as f:
                dados = json.load(f)
        except Exception:
            pass
    # Migração de formatos antigos (v1.0 usava "sessoes")
    if "etapas" not in dados:
        dados["etapas"] = dados.pop("sessoes", [])
    if "etapa_atual" not in dados:
        completas = len([e for e in dados["etapas"] if e.get("completa")])
        dados["etapa_atual"] = min(completas + 1, TOTAL_ETAPAS + 1)
    dados.setdefault("inicio", str(date.today()))
    return dados

def salvar_dados(dados):
    _garantir_data()
    with open(DATA_FILE, 'w') as f:
        json.dump(dados, f, indent=2, ensure_ascii=False)

def etapas_completas_hoje(dados):
    hoje = str(date.today())
    return [e for e in dados["etapas"] if e.get("data") == hoje and e.get("completa")]

def calcular_linhas_minimas(dados):
    try:
        primeira = date.fromisoformat(dados["inicio"])
        dias = (date.today() - primeira).days
        return LINHAS_BASE + (dias // CICLO_DIAS) * CICLO_INCREMENTO
    except Exception:
        return LINHAS_BASE

def aplicar_reset_se_pedido():
    """Se o pai pediu reset pelo portal (reset.flag em /data), limpa a casa
    da aventura do filho. O progresso em /data já foi zerado pelo portal."""
    try:
        if RESET_FLAG.exists():
            aventura = Path.home() / 'aventura'
            if aventura.exists():
                shutil.rmtree(aventura, ignore_errors=True)
            RESET_FLAG.unlink(missing_ok=True)
    except Exception:
        pass

def escrever_trail(msg):
    try:
        _garantir_data()
        carimbo = datetime.now().strftime('%d/%m %H:%M')
        with open(TRAIL_FILE, 'a') as f:
            f.write(f"[{carimbo}] {msg}\n")
    except Exception:
        pass

# ═══════════════════════════════════════════════════════════════
# HEARTBEAT + MENSAGENS PARA O PORTAL
# ═══════════════════════════════════════════════════════════════

def escrever_heartbeat(num_etapa, inicio_iso, pid):
    try:
        _garantir_data()
        ONLINE_FILE.write_text(json.dumps({
            "ativo":   True,
            "sessao":  num_etapa,
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
    com_resumo = [e for e in dados["etapas"] if e.get("titulo_livro")]
    if not com_resumo:
        return
    print(f"\n{cor('  📚 SUA BIBLIOTECA:', C.VERDE, C.NEGRITO)}")
    separador('─', 58, C.VERDE)
    for i, e in enumerate(com_resumo[-8:], 1):
        idx     = cor(f'{i:2}.', C.DIM)
        titulo  = cor(e.get('titulo_livro', '?'), C.BRANCO)
        linhas  = cor(f"{e.get('linhas_resumo', '?')} linhas", C.AMARELO)
        data    = cor(f"[{e.get('data', '')}]", C.DIM)
        print(f"  {idx}  {titulo}  {linhas}  {data}")
    total = cor(f"Total: {len(com_resumo)} livro(s)  🏆", C.CIANO)
    print(f"\n  {total}")
    separador('─', 58, C.VERDE)

# ═══════════════════════════════════════════════════════════════
# SESSÃO BASH COM TIMER
# ═══════════════════════════════════════════════════════════════

def executar_sessao_bash(minutos, num_etapa=1, inicio_iso=None):
    resultado = {'motivo': 'saiu'}
    if inicio_iso is None:
        inicio_iso = datetime.now().isoformat()

    proc = subprocess.Popen(['/bin/bash', '-i'])

    def heartbeat_loop():
        while proc.poll() is None:
            escrever_heartbeat(num_etapa, inicio_iso, proc.pid)
            time.sleep(30)
        escrever_offline()

    def mensagem_loop():
        while proc.poll() is None:
            verificar_mensagem(proc.pid)
            time.sleep(5)

    def aviso_cinco():
        try:
            with open(f'/proc/{proc.pid}/fd/1', 'w') as tty:
                tty.write(
                    f'\n\n{C.AMARELO}{C.NEGRITO}'
                    f'  ⚠️   5 minutos restantes nesta etapa!{C.RESET}\n\n'
                )
        except Exception:
            pass

    def encerrar():
        resultado['motivo'] = 'timeout'
        try:
            proc.terminate()
        except ProcessLookupError:
            pass

    escrever_heartbeat(num_etapa, inicio_iso, proc.pid)

    th = threading.Thread(target=heartbeat_loop, daemon=True)
    tm = threading.Thread(target=mensagem_loop,  daemon=True)
    th.start()
    tm.start()

    t_aviso = threading.Timer(max(1, (minutos - 5)) * 60, aviso_cinco)
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
# VERIFICAÇÃO DO DESAFIO
# ═══════════════════════════════════════════════════════════════

def verificar_missao(etapa):
    """Roda o comando de verificação da etapa como o jogador. True se concluiu."""
    try:
        r = subprocess.run(['/bin/bash', '-lc', etapa['verificar']],
                           timeout=15,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        return r.returncode == 0
    except Exception:
        return False

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
  👉  Quando terminar, volte aqui para registrar o resumo.

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
            relogio = cor(f'{mins:02d}:{secs:02d}', C.AMARELO, C.NEGRITO)
            sys.stdout.write(f"\r  ⏱  {relogio} restantes  [{barra}]  ")
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
# RESUMO DO LIVRO — ENVIADO PELO PORTAL WEB
# ═══════════════════════════════════════════════════════════════

def coletar_resumo_portal(numero_etapa, linhas_minimas):
    """Gera um link para o portal, aguarda o filho enviar o resumo de lá.
    Retorna (titulo, resumo, n_linhas) ou None se ele cancelar (Ctrl+C)."""
    token = secrets.token_urlsafe(6)
    try:
        RESUMO_ENVIADO.unlink(missing_ok=True)
    except Exception:
        pass
    RESUMO_PEND.write_text(json.dumps({
        "token":          token,
        "etapa":          numero_etapa,
        "linhas_minimas": linhas_minimas,
        "criado":         datetime.now().isoformat(),
        "enviado":        False,
    }, ensure_ascii=False))

    url = f"https://{ADMIN_DOMAIN}/resumo?t={token}"

    limpar()
    separador('═', 58, C.VERDE)
    print(cor('  ✍️   RESUMO DO LIVRO  —  pelo portal web', C.VERDE, C.NEGRITO))
    separador('═', 58, C.VERDE)
    print(f"""
  Agora registre o que você aprendeu no livro.
  Desta vez você escreve pelo {cor('navegador', C.CIANO, C.NEGRITO)}, no portal!

  {cor('1.', C.AMARELO)}  Abra este link no celular ou no computador:

      {cor(url, C.CIANO, C.NEGRITO)}

  {cor('2.', C.AMARELO)}  Escreva o título do livro e o resumo
      ({cor(f'mínimo {linhas_minimas} linhas, cada uma com 20+ caracteres', C.DIM)})

  {cor('3.', C.AMARELO)}  Toque em ENVIAR. Esta tela vai liberar sozinha. ✨

  {cor('📱  No celular:', C.MAGENTA, C.NEGRITO)} abra o navegador (Chrome/Safari) e
      digite o endereço acima na barra de busca.
""")
    separador('─', 58, C.VERDE)
    print(cor("\n  ⏳  Aguardando o seu resumo chegar pelo portal...", C.AMARELO))
    print(cor("     (se precisar, você pode pressionar Ctrl+C para sair e\n"
              "      voltar depois — sua etapa fica salva)", C.DIM))

    giro = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
    i = 0
    try:
        while True:
            if RESUMO_ENVIADO.exists():
                try:
                    data = json.loads(RESUMO_ENVIADO.read_text())
                except Exception:
                    data = {}
                if data.get("token") == token:
                    RESUMO_ENVIADO.unlink(missing_ok=True)
                    RESUMO_PEND.unlink(missing_ok=True)
                    sys.stdout.write("\r" + " " * 50 + "\r")
                    return (data.get("titulo", "Livro"),
                            data.get("resumo", ""),
                            int(data.get("linhas", 0)))
            sys.stdout.write(f"\r  {cor(giro[i % len(giro)], C.CIANO)}  aguardando envio... ")
            sys.stdout.flush()
            i += 1
            time.sleep(2)
    except KeyboardInterrupt:
        print(cor("\n\n  Sem problema! Volte quando enviar o resumo. 👋", C.DIM))
        return None

# ═══════════════════════════════════════════════════════════════
# TELAS
# ═══════════════════════════════════════════════════════════════

def tela_inicio_etapa(dados, numero, etapa):
    total_livros = len([e for e in dados["etapas"] if e.get("titulo_livro")])
    feitas_hoje  = len(etapas_completas_hoje(dados))
    limpar()
    separador('═', 58, C.VERDE)
    print(cor(f'  ⚔   QUEST LINUX — ETAPA {numero} DE {TOTAL_ETAPAS}', C.VERDE, C.NEGRITO))
    separador('═', 58, C.VERDE)
    print(f"""
  {cor(etapa['titulo'], C.CIANO, C.NEGRITO)}

  🗓  Data:            {cor(str(date.today()), C.CIANO)}
  ⏱  Tempo da etapa:  {cor(f'{SESSAO_MINUTOS} minutos', C.AMARELO)}
  📚  Livros lidos:    {cor(str(total_livros), C.VERDE)}
  🎯  Hoje:            {cor(f'{feitas_hoje}/{ETAPAS_POR_DIA} etapas', C.AMARELO)}
""")
    separador('─', 58, C.AMARELO)
    print(cor('\n  🧩  SUA MISSÃO:', C.AMARELO, C.NEGRITO))
    print(f"\n  {cor(etapa['missao'], C.BRANCO)}\n")
    print(cor(f"  💡  Dica:  {etapa['dica']}", C.DIM))
    separador('─', 58, C.AMARELO)
    print(cor("\n  Quando terminar a missão, digite  exit  para eu conferir.", C.VERDE))
    pausar("  Pressione ENTER para começar a explorar...")

def tela_missao_incompleta(etapa):
    limpar()
    separador('═', 58, C.VERMELHO)
    print(cor('  🔍  MISSÃO AINDA NÃO CONCLUÍDA', C.VERMELHO, C.NEGRITO))
    separador('═', 58, C.VERMELHO)
    print(f"""
  Quase lá! Ainda não encontrei o que a missão pede.

  {cor('🧩  Missão:', C.AMARELO)}
  {cor(etapa['missao'], C.BRANCO)}

  {cor('💡  Dica:', C.CIANO)}  {etapa['dica']}

  Vamos tentar de novo — você consegue!
""")
    separador('─', 58, C.VERMELHO)
    try:
        resp = input(cor("\n  ENTER para voltar ao terminal  •  'sair' para sair: ", C.DIM)).strip().lower()
    except (EOFError, KeyboardInterrupt):
        return False
    return resp != 'sair'

def tela_desafio_concluido(etapa):
    limpar()
    separador('═', 58, C.VERDE)
    print(cor('  ✅  DESAFIO CONCLUÍDO!', C.VERDE, C.NEGRITO))
    separador('═', 58, C.VERDE)
    print(f"""
  Mandou muito bem na etapa "{cor(etapa['titulo'], C.CIANO, C.NEGRITO)}"!

  Agora vem a parte que constrói a sua mente: a leitura.
  Para liberar a próxima etapa, leia e registre um resumo.
""")
    pausar("  Pressione ENTER para começar o tempo de leitura...")

def tela_etapa_concluida(dados, numero, etapa):
    limpar()
    separador('═', 58, C.VERDE)
    print(cor(f'  🏆  ETAPA {numero} CONCLUÍDA!', C.VERDE, C.NEGRITO))
    separador('═', 58, C.VERDE)
    restantes = TOTAL_ETAPAS - numero
    print(f"""
  📚 Livro registrado na sua biblioteca!
  ✅ Etapas concluídas: {cor(f'{numero}/{TOTAL_ETAPAS}', C.AMARELO, C.NEGRITO)}
""")
    mostrar_biblioteca(dados)
    if numero < TOTAL_ETAPAS and etapa.get('teaser'):
        proxima = ETAPAS[numero]  # próxima etapa (0-based -> numero)
        print(cor(f"\n  🔮  PRÓXIMA ETAPA ({numero + 1}): {proxima['titulo']}", C.MAGENTA, C.NEGRITO))
        print(cor(f"      {etapa['teaser']}", C.DIM))
    if restantes > 0:
        print(cor(f"\n  Faltam {restantes} etapa(s) para a grande recompensa final! 🎁", C.CIANO))

def tela_limite_diario(dados):
    limpar()
    separador('═', 58, C.MAGENTA)
    print(cor('  🌙  FIM DO DIA — LIMITE ATINGIDO', C.MAGENTA, C.NEGRITO))
    separador('═', 58, C.MAGENTA)
    total_livros = len([e for e in dados["etapas"] if e.get("titulo_livro")])
    concluidas   = dados["etapa_atual"] - 1
    print(f"""
  Você usou suas {cor(str(ETAPAS_POR_DIA), C.AMARELO)} etapas de hoje. Incrível!

  ✅ Progresso:  {cor(f'{concluidas}/{TOTAL_ETAPAS}', C.VERDE, C.NEGRITO)} etapas
  📚 Biblioteca: {cor(str(total_livros), C.AMARELO, C.NEGRITO)} livro(s)

  Volte amanhã para continuar a jornada! 🗡️
""")
    separador('─', 58)

def tela_jornada_concluida(dados):
    limpar()
    separador('═', 58, C.AMARELO)
    print(cor('  🎉🎉  JORNADA COMPLETA — VOCÊ VENCEU!  🎉🎉', C.AMARELO, C.NEGRITO))
    separador('═', 58, C.AMARELO)
    total_livros = len([e for e in dados["etapas"] if e.get("titulo_livro")])
    print(f"""
  Você concluiu as {cor(str(TOTAL_ETAPAS), C.VERDE, C.NEGRITO)} etapas da Quest Linux!
  📚 E ainda leu {cor(str(total_livros), C.AMARELO, C.NEGRITO)} livros pelo caminho.

  {cor('🎁  RECOMPENSA FINAL DESBLOQUEADA:', C.MAGENTA, C.NEGRITO)}

      Agora sim — chegou a hora de {cor('JOGAR MINECRAFT COM O SEU PAI!', C.VERDE, C.NEGRITO)}

      👉  Dentro do terminal, digite:  {cor('iniciar-minecraft', C.CIANO, C.NEGRITO)}
      👉  Combine o horário com o Pai Vinny e divirtam-se juntos. 🟢
""")
    mostrar_biblioteca(dados)

# ═══════════════════════════════════════════════════════════════
# UMA ETAPA COMPLETA
# ═══════════════════════════════════════════════════════════════

def fazer_etapa(dados):
    """Executa uma etapa: desafio (verificado) + leitura + resumo via portal.
    Retorna True se concluiu, False se o filho saiu no meio."""
    numero = dados["etapa_atual"]
    etapa  = ETAPAS[numero - 1]

    # Recupera registro incompleto desta etapa (caso tenha desconectado antes)
    registro = next((e for e in dados["etapas"]
                     if e.get("numero") == numero and not e.get("completa")), None)
    if registro is None:
        registro = {"numero": numero, "numero_do_dia": numero,
                    "data": str(date.today()),
                    "inicio": datetime.now().isoformat(),
                    "completa": False, "desafio_ok": False, "resumo_enviado": False}
        dados["etapas"].append(registro)
        salvar_dados(dados)
        escrever_trail(f"🏁 Iniciou a etapa {numero}: {etapa['titulo']}")

    # ── Fase 1: desafio Linux (verificado) ──
    if not registro.get("desafio_ok"):
        tela_inicio_etapa(dados, numero, etapa)
        while True:
            executar_sessao_bash(SESSAO_MINUTOS, numero, registro["inicio"])
            if verificar_missao(etapa):
                registro["desafio_ok"] = True
                salvar_dados(dados)
                escrever_trail(f"✅ Desafio da etapa {numero} concluído: {etapa['titulo']}")
                break
            if not tela_missao_incompleta(etapa):
                return False

    # ── Fase 2: leitura + resumo pelo portal ──
    tela_desafio_concluido(etapa)
    temporizador_leitura(LEITURA_MINUTOS)
    lmin = calcular_linhas_minimas(dados)
    res  = coletar_resumo_portal(numero, lmin)
    if res is None:
        return False
    titulo, resumo, n_linhas = res

    registro.update({
        "fim":           datetime.now().isoformat(),
        "titulo_livro":  titulo,
        "resumo":        resumo,
        "linhas_resumo": n_linhas,
        "resumo_enviado": True,
        "completa":      True,
    })
    dados["etapa_atual"] = numero + 1
    salvar_dados(dados)
    escrever_trail(f"📚 Etapa {numero} concluída — livro: {titulo}")

    tela_etapa_concluida(dados, numero, etapa)
    return True

# ═══════════════════════════════════════════════════════════════
# FLUXO PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def main():
    # SSH não-interativo (scp, rsync...)
    if len(sys.argv) > 1 and sys.argv[1] == '-c':
        os.execv('/bin/bash', ['/bin/bash'] + sys.argv[1:])
        return

    _garantir_data()
    aplicar_reset_se_pedido()
    dados = carregar_dados()

    mostrar_dicas_login()

    # ── Jornada já concluída? ──
    if dados["etapa_atual"] > TOTAL_ETAPAS:
        tela_jornada_concluida(dados)
        print(MENSAGEM_PAI)
        pausar()
        sys.exit(0)

    # ── Limite diário ──
    if len(etapas_completas_hoje(dados)) >= ETAPAS_POR_DIA:
        tela_limite_diario(dados)
        print(MENSAGEM_PAI)
        pausar()
        sys.exit(0)

    # ── Faz até ETAPAS_POR_DIA etapas neste login ──
    while (len(etapas_completas_hoje(dados)) < ETAPAS_POR_DIA
           and dados["etapa_atual"] <= TOTAL_ETAPAS):
        ok = fazer_etapa(dados)
        if not ok:
            break
        if (len(etapas_completas_hoje(dados)) < ETAPAS_POR_DIA
                and dados["etapa_atual"] <= TOTAL_ETAPAS):
            pausar(f"\n  Pressione ENTER para começar sua próxima etapa de hoje "
                   f"({len(etapas_completas_hoje(dados)) + 1}/{ETAPAS_POR_DIA})...")

    # ── Encerramento ──
    if dados["etapa_atual"] > TOTAL_ETAPAS:
        tela_jornada_concluida(dados)
    else:
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
