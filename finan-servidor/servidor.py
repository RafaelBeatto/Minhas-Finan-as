"""Servidor local do módulo Finan: guarda a Client Secret longe do navegador.

Atende /api/finan em http://127.0.0.1:8766 e, se a pasta dist/ existir, o sistema compilado.
Só aceita conexões do próprio computador.
"""
import hmac
import io
import json
import os
import re
import sys
import threading
import traceback
import urllib.request
import webbrowser
from datetime import date
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import requests
from dotenv import load_dotenv
import categorias
import comparativo
import exportar
import financeiro as fin
import historico
import inteligencia
import pluggy

PORTA = int(os.getenv("FINAN_PORTA", os.getenv("PORT", "8766")))
HOST = os.getenv("FINAN_HOST", "127.0.0.1")
PREFIXO = "/api/finan"
PASTA = Path(__file__).resolve().parent
DIST = PASTA.parent / "dist"
DADOS = Path(os.getenv("FINAN_DADOS", PASTA / "dados"))
ARQUIVO_HISTORICO = DADOS / "historico.db"
ARQUIVO_REGRAS = DADOS / "regras.json"
ARQUIVO_ORCAMENTO = DADOS / "orcamento.json"
ARQUIVO_ASSINATURAS = DADOS / "assinaturas.json"
ARQUIVO_CATEGORIAS = DADOS / "categorias.json"
LOCAL = re.compile(r"(127\.0\.0\.1|localhost)(:\d+)?$")
ORIGEM_LOCAL = re.compile(r"http://(127\.0\.0\.1|localhost)(:\d+)?$")
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

load_dotenv(DADOS / ".env")
CLIENT_ID = os.getenv("PLUGGY_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("PLUGGY_CLIENT_SECRET", "").strip()
ITEM_ID = os.getenv("PLUGGY_ITEM_ID", "").strip()

# Modo nuvem: com FINAN_TOKEN, a API aceita só quem envia o token no cabeçalho
# Authorization e o servidor pode ficar acessível pela internet.
TOKEN = os.getenv("FINAN_TOKEN", "").strip()
NUVEM = bool(TOKEN)

gravando = threading.Lock()  # regras e limites: uma gravação por vez
sincronizando = threading.Lock()


class ErroApi(Exception):
    def __init__(self, status, mensagem):
        super().__init__(mensagem)
        self.status = status
        self.mensagem = mensagem


def _transacoes():
    transacoes = historico.carregar(ARQUIVO_HISTORICO)
    fin.aplicar_regras(transacoes, fin.carregar_regras(ARQUIVO_REGRAS))
    return transacoes


def _configurado():
    return bool(CLIENT_ID and CLIENT_SECRET and ITEM_ID)


def _ignoradas():
    return fin.carregar_ignoradas(ARQUIVO_ASSINATURAS)["ignoradas"]


def _conta(a):
    return {"id": a.get("id"), "nome": a.get("name") or a.get("number") or "Conta",
            "cartao": a.get("type") == "CREDIT", "saldo": float(a.get("balance") or 0)}


def _investimento(i):
    """O banco manda o nome jurídico ('CDB - NU FINANCEIRA S.A. - ...'): fica só o essencial."""
    partes = (i.get("name") or "Investimento").split(" - ")
    nome = f"{partes[0]} · {partes[1]}" if len(partes) > 1 else partes[0]
    return {"id": i.get("id"), "nome": nome, "tipo": i.get("subtype") or i.get("type") or "",
            "saldo": float(i.get("balance") or 0), "data": i.get("date")}


def _investimentos(instantaneo):
    """Posições resgatadas continuam vindo com saldo zero: contam à parte, não poluem a lista."""
    todos = [_investimento(i) for i in instantaneo.get("investimentos", [])]
    ativos = sorted((i for i in todos if i["saldo"] > 0), key=lambda i: -i["saldo"])
    return ativos, len(todos) - len(ativos)


def _nomes_de_categorias(instantaneo, transacoes):
    renomeadas = fin.carregar_regras(ARQUIVO_REGRAS)["renomeadas"]
    return sorted((set(instantaneo.get("categorias", [])) - set(renomeadas))
                  | {t["categoria"] for t in transacoes} | {fin.INTERNO}
                  | set(fin.carregar_criadas(ARQUIVO_CATEGORIAS)))


def painel(_consulta):
    transacoes = _transacoes()
    hoje = date.today()
    instantaneo = historico.carregar_instantaneo(ARQUIVO_HISTORICO)
    contas = instantaneo.get("contas", [])
    em_conta, fatura = fin.resumo_contas(contas)
    orcamento = fin.situacao_orcamento(transacoes, fin.carregar_orcamento(ARQUIVO_ORCAMENTO), hoje)
    ignoradas = _ignoradas()
    assinaturas = fin.detectar_assinaturas(transacoes, hoje, ignoradas)
    abertas = fin.parcelas_abertas(transacoes, hoje)
    faturas = sorted(instantaneo.get("faturas", []), key=lambda f: f["vencimento"] or "", reverse=True)
    investimentos, encerrados = _investimentos(instantaneo)
    return {
        "hoje": hoje.isoformat(),
        "investimentos": investimentos,
        "investimentos_encerrados": encerrados,
        "investido": sum(i["saldo"] for i in investimentos),
        "investimentos_status": instantaneo.get("investimentos_status"),
        "configurado": _configurado(),
        "atualizado_em": instantaneo.get("atualizado_em"),
        "banco_lido_em": instantaneo.get("banco_lido_em"),
        "proxima_leitura": instantaneo.get("proxima_leitura"),
        "tem_contas": bool(contas),
        "em_conta": em_conta,
        "fatura": fatura,
        "contas": [_conta(a) for a in contas],
        "cartao": fin.resumo_cartao(contas),
        "faturas": faturas,
        "mensal": fin.resumo_mensal(transacoes),
        "orcamento": orcamento,
        "alerta": fin.texto_alerta(orcamento),
        "assinaturas": assinaturas,
        "custo_assinaturas": fin.custo_assinaturas(assinaturas),
        "ignoradas": len(ignoradas),
        "parcelas": abertas,
        "compromisso": [{"mes": m, "valor": v} for m, v in fin.compromisso_por_mes(abertas)],
        "previsao": fin.previsao_mes(transacoes, hoje),
        "proximo_mes": fin.compromissos_proximo_mes(abertas, assinaturas, hoje),
        "nomes_contas": sorted({t["conta"] for t in transacoes}),
        "categorias": _nomes_de_categorias(instantaneo, transacoes),
        "periodos": fin.PERIODOS,
    }


def _valor(consulta, chave):
    try:
        return fin.ler_valor(consulta.get(chave), aceita_zero=True)
    except ValueError as e:
        raise ErroApi(400, "Digite um valor válido, como 150,00.") from e


def _opcao(consulta, chave, opcoes):
    valor = consulta.get(chave) or None
    if valor is not None and valor not in opcoes:
        raise ErroApi(400, "Filtro inválido.")
    return valor


def extrato(consulta):
    periodo = consulta.get("periodo") or fin.PERIODOS[0]
    if periodo not in fin.PERIODOS:
        raise ErroApi(400, "Período inválido.")
    transacoes = fin.filtrar(_transacoes(), periodo, conta=consulta.get("conta"),
                             busca=consulta.get("busca", ""), de=consulta.get("de"),
                             ate=consulta.get("ate"))
    transacoes = fin.filtrar_detalhes(
        transacoes, tipo=_opcao(consulta, "tipo", fin.TIPOS),
        situacao=_opcao(consulta, "situacao", fin.SITUACOES), minimo=_valor(consulta, "minimo"),
        maximo=_valor(consulta, "maximo"), sem_internas=consulta.get("sem_internas") == "1")
    _, total_categorias, por_categoria = fin.totais(transacoes)
    disponiveis = sorted({t["categoria"] for t in transacoes})
    categoria = consulta.get("categoria")
    if categoria:
        transacoes = [t for t in transacoes if t["categoria"] == categoria]
    entradas, saidas, _ = fin.totais(transacoes)
    return {"entradas": entradas, "saidas": saidas, "resultado": entradas - saidas,
            "total_categorias": total_categorias, "categorias_disponiveis": disponiveis,
            "por_categoria": [{"categoria": c, "total": v} for c, v in por_categoria],
            "transacoes": [{**t, "corrigida": t["categoria"] != t["categoria_original"]}
                           for t in transacoes]}


def identificar(_consulta):
    return {"app": "finan", "pasta": str(PASTA)}


def comparacao(consulta):
    mes = consulta.get("mes", "")
    if not re.fullmatch(r"\d{4}-\d{2}", mes):
        raise ErroApi(400, "Mês inválido.")
    return {"mes": mes, "anterior": fin.mes_anterior(mes), "linhas": [
        {"categoria": c, "atual": a, "anterior": b, "diferenca": d}
        for c, a, b, d in fin.comparar_categorias(_transacoes(), mes)]}


def comparar_meses(consulta):
    """Tudo de uma vez: as três visões da página usam esta mesma resposta."""
    primeiro, segundo = consulta.get("primeiro", ""), consulta.get("segundo", "")
    if primeiro == segundo:
        raise ErroApi(400, "Escolha dois meses diferentes.")
    transacoes = _transacoes()
    hoje = date.today()
    try:
        resultado = comparativo.comparar(transacoes, primeiro, segundo, hoje)
    except ValueError as e:
        raise ErroApi(400, "Escolha meses com movimentações.") from e
    analise = inteligencia.analisar(transacoes, resultado, hoje, _ignoradas())
    return {**resultado, "analise": analise}


def visao_categorias(consulta):
    periodo = consulta.get("periodo") or fin.PERIODOS[0]
    if periodo not in fin.PERIODOS:
        raise ErroApi(400, "Período inválido.")
    return categorias.visao(_transacoes(), fin.carregar_regras(ARQUIVO_REGRAS),
                            fin.carregar_orcamento(ARQUIVO_ORCAMENTO),
                            fin.carregar_criadas(ARQUIVO_CATEGORIAS), periodo, date.today())


def _alterar_categorias(alteracao):
    """Carrega e grava junto regras, limites e categorias criadas, uma alteração por vez."""
    with gravando:
        regras = fin.carregar_regras(ARQUIVO_REGRAS)
        orcamento = fin.carregar_orcamento(ARQUIVO_ORCAMENTO)
        criadas = fin.carregar_criadas(ARQUIVO_CATEGORIAS)
        try:
            alteracao(regras, orcamento, criadas)
        except ValueError as e:
            raise ErroApi(400, str(e)) from e
        fin.gravar_json(regras, ARQUIVO_REGRAS)
        fin.gravar_json(orcamento, ARQUIVO_ORCAMENTO)
        fin.gravar_json({"criadas": criadas}, ARQUIVO_CATEGORIAS)
    return {}


def criar_categoria(corpo):
    def alteracao(_regras, _orcamento, criadas):
        nome = categorias.validar_nome(corpo.get("nome"))
        if nome in categorias.nomes_ativos(_transacoes(), criadas):
            raise ValueError("Já existe uma categoria com este nome.")
        criadas.append(nome)
    return _alterar_categorias(alteracao)


def renomear_categoria(corpo):
    return _alterar_categorias(lambda regras, orcamento, criadas: categorias.renomear(
        _transacoes(), regras, orcamento, criadas, corpo.get("origem"), corpo.get("destino")))


def excluir_categoria(corpo):
    return _alterar_categorias(lambda regras, orcamento, criadas: categorias.excluir(
        _transacoes(), regras, orcamento, criadas, corpo.get("nome")))


def desfazer_renomeacao(corpo):
    def alteracao(regras, _orcamento, _criadas):
        if regras["renomeadas"].pop(corpo.get("origem"), None) is None:
            raise ValueError("Esta alteração não existe mais.")
    return _alterar_categorias(alteracao)


def remover_regra_salva(corpo):
    return _alterar_categorias(lambda regras, _orcamento, _criadas: categorias.remover_regra_salva(
        regras, corpo.get("tipo"), corpo.get("chave")))


def atualizar(_corpo):
    if not _configurado():
        raise ErroApi(400, "Preencha o arquivo finan-servidor/dados/.env e reinicie o servidor.")
    if not sincronizando.acquire(blocking=False):
        raise ErroApi(409, "Já existe uma atualização em andamento.")
    try:
        return {"aviso": pluggy.sincronizar(CLIENT_ID, CLIENT_SECRET, ITEM_ID, ARQUIVO_HISTORICO)}
    except (requests.RequestException, KeyError) as e:
        raise ErroApi(502, pluggy.mensagem_erro(e)) from e
    finally:
        sincronizando.release()


def _transacao(identificador):
    for t in _transacoes():
        if t["id"] == identificador:
            return t
    raise ErroApi(404, "Transação não encontrada.")


def salvar_regra(corpo):
    categoria = str(corpo.get("categoria") or "").strip()
    if not categoria:
        raise ErroApi(400, "Escolha ou digite uma categoria.")
    with gravando:
        regras = fin.carregar_regras(ARQUIVO_REGRAS)
        fin.definir_regra(regras, _transacao(corpo.get("id")), categoria, bool(corpo.get("todas")))
        fin.gravar_json(regras, ARQUIVO_REGRAS)
    return {}


def remover_regra(corpo):
    with gravando:
        regras = fin.carregar_regras(ARQUIVO_REGRAS)
        fin.remover_regra(regras, _transacao(corpo.get("id")))
        fin.gravar_json(regras, ARQUIVO_REGRAS)
    return {}


def salvar_limite(corpo):
    categoria = str(corpo.get("categoria") or "").strip()
    try:
        valor = fin.ler_valor(str(corpo.get("valor") or ""))
    except ValueError as e:
        raise ErroApi(400, "Digite um valor maior que zero, como 800,00.") from e
    if not categoria:
        raise ErroApi(400, "Categoria inválida.")
    with gravando:
        orcamento = fin.carregar_orcamento(ARQUIVO_ORCAMENTO)
        if valor is None:
            orcamento.pop(categoria, None)
        else:
            orcamento[categoria] = valor
        fin.gravar_json(orcamento, ARQUIVO_ORCAMENTO)
    return {}


def ignorar_assinatura(corpo):
    chave = str(corpo.get("chave") or "")
    with gravando:
        chaves = _ignoradas()
        if chave and chave not in chaves:
            fin.gravar_json({"ignoradas": chaves + [chave]}, ARQUIVO_ASSINATURAS)
    return {}


def restaurar_assinaturas(_corpo):
    with gravando:
        fin.gravar_json({"ignoradas": []}, ARQUIVO_ASSINATURAS)
    return {}


def planilha():
    hoje = date.today()
    saida = io.BytesIO()
    exportar.gerar_planilha(saida, _transacoes(), fin.carregar_orcamento(ARQUIVO_ORCAMENTO),
                            _ignoradas(), hoje)
    return saida.getvalue(), f"financeiro_{hoje.isoformat()}.xlsx"


LEITURAS = {"/servidor": identificar, "/painel": painel, "/extrato": extrato,
            "/comparacao": comparacao, "/comparar": comparar_meses,
            "/categorias": visao_categorias}
ESCRITAS = {"/atualizar": atualizar, "/regra": salvar_regra, "/regra/remover": remover_regra,
            "/limite": salvar_limite, "/assinaturas/ignorar": ignorar_assinatura,
            "/assinaturas/restaurar": restaurar_assinaturas,
            "/categorias/criar": criar_categoria, "/categorias/renomear": renomear_categoria,
            "/categorias/excluir": excluir_categoria,
            "/categorias/desfazer": desfazer_renomeacao,
            "/categorias/regra/remover": remover_regra_salva}


class Servidor(ThreadingHTTPServer):
    allow_reuse_address = False
    daemon_threads = True


class Manipulador(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".html": "text/html; charset=utf-8",
        ".js": "text/javascript; charset=utf-8",
        ".css": "text/css; charset=utf-8",
        ".svg": "image/svg+xml",
        ".woff2": "font/woff2",
    }

    def _json(self, status, dados):
        corpo = json.dumps(dados, ensure_ascii=False).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(corpo)))
        self.end_headers()
        self.wfile.write(corpo)

    def _autorizado(self):
        """No modo nuvem, só entra quem envia o token. Localmente, não há token."""
        if not NUVEM:
            return True
        enviado = self.headers.get("Authorization", "")
        return hmac.compare_digest(enviado, f"Bearer {TOKEN}")

    def _origem_permitida(self):
        """Um site aberto no navegador não pode ler nem alterar os dados locais."""
        if NUVEM:
            return self._autorizado()
        origem = self.headers.get("Origin")
        return bool(LOCAL.match(self.headers.get("Host", ""))
                    and (origem is None or ORIGEM_LOCAL.match(origem)))

    def _responder(self, funcao, *argumentos):
        try:
            dados = funcao(*argumentos)
        except ErroApi as e:
            self._json(e.status, {"erro": e.mensagem})
        except OSError as e:
            self._json(500, {"erro": f"Não foi possível acessar os dados: {e}"})
        except Exception:
            traceback.print_exc()
            self._json(500, {"erro": "Erro interno no servidor do Finan."})
        else:
            self._json(200, dados)

    def do_GET(self):
        partes = urlsplit(self.path)
        # Na nuvem a página do app é pública; só a API exige o token.
        if (partes.path.startswith(PREFIXO) or not NUVEM) and not self._origem_permitida():
            if NUVEM:
                self._json(401, {"erro": "Acesso negado."})
            else:
                self._json(403, {"erro": "Origem não permitida."})
            return
        if partes.path == f"{PREFIXO}/exportar":
            self._exportar()
        elif partes.path.startswith(PREFIXO):
            funcao = LEITURAS.get(partes.path[len(PREFIXO):])
            if funcao is None:
                self._json(404, {"erro": "Endereço não encontrado."})
                return
            consulta = {c: v[0] for c, v in parse_qs(partes.query).items()}
            self._responder(funcao, consulta)
        else:
            self._estatico(partes.path)

    def do_POST(self):
        funcao = ESCRITAS.get(urlsplit(self.path).path[len(PREFIXO):])
        if NUVEM and not self._autorizado():
            self._json(401, {"erro": "Acesso negado."})
        elif not self._origem_permitida() or "application/json" not in self.headers.get("Content-Type", ""):
            self._json(403, {"erro": "Origem não permitida."})
        elif funcao is None:
            self._json(404, {"erro": "Endereço não encontrado."})
        else:
            try:
                tamanho = int(self.headers.get("Content-Length") or 0)
                corpo = json.loads(self.rfile.read(tamanho) or "{}")
            except ValueError:
                corpo = None
            if isinstance(corpo, dict):
                self._responder(funcao, corpo)
            else:
                self._json(400, {"erro": "Pedido inválido."})

    def _exportar(self):
        try:
            conteudo, nome = planilha()
        except Exception:
            traceback.print_exc()
            self._json(500, {"erro": "Não foi possível gerar a planilha."})
            return
        self.send_response(200)
        self.send_header("Content-Type", XLSX)
        self.send_header("Content-Disposition", f'attachment; filename="{nome}"')
        self.send_header("Content-Length", str(len(conteudo)))
        self.end_headers()
        self.wfile.write(conteudo)

    def _estatico(self, caminho):
        if not (DIST / "index.html").is_file():
            self._json(404, {"erro": "Sistema não compilado: rode npm run build."})
            return
        if not Path(self.translate_path(caminho)).is_file():
            self.path = "/index.html"  # as rotas são resolvidas pelo React
        super().do_GET()

    def end_headers(self):
        if "/assets/" not in self.path:
            self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, formato, *args):
        pass


def finan_em_execucao():
    """Pergunta a quem ocupa a porta se é o Finan, sem passar por proxy."""
    abridor = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with abridor.open(f"http://{HOST}:{PORTA}{PREFIXO}/servidor", timeout=3) as resposta:
            return json.load(resposta)
    except (OSError, ValueError):
        return None


def porta_ocupada():
    """Abre o Finan se ele já roda desta pasta; outra pasta usaria outros dados."""
    outro = finan_em_execucao()
    if outro and outro.get("pasta") == str(PASTA):
        webbrowser.open(f"http://{HOST}:{PORTA}/finan")
        print("O Finan já estava aberto: abri o navegador.")
        return 0
    if outro:
        print(f"O Finan já está aberto a partir de outra pasta:\n{outro.get('pasta')}\n"
              "Feche aquela janela e abra de novo.")
    else:
        print(f"A porta {PORTA} está em uso por outro programa ou por uma versão antiga do Finan.\n"
              "Feche esse programa e abra de novo.")
    return 1


def principal():
    if not NUVEM and HOST not in ("127.0.0.1", "localhost"):
        print("Para expor o Finan em outro endereço é obrigatório definir FINAN_TOKEN.")
        return 1
    DADOS.mkdir(exist_ok=True)
    try:
        servidor = Servidor((HOST, PORTA), partial(Manipulador, directory=str(DIST)))
    except OSError:
        return porta_ocupada()
    print(f"Finan em execução: http://{HOST}:{PORTA}/finan (feche esta janela para encerrar)")
    if (DIST / "index.html").is_file() and "--sem-navegador" not in sys.argv and not NUVEM:
        threading.Timer(0.3, webbrowser.open, args=(f"http://{HOST}:{PORTA}/finan",)).start()
    try:
        servidor.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        servidor.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(principal())
