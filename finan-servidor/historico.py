"""Guarda as transações num banco SQLite local para o histórico não depender da Pluggy."""
import json
import sqlite3
from contextlib import closing

CRIAR_TABELA = """
CREATE TABLE IF NOT EXISTS transacoes (
    id TEXT PRIMARY KEY,
    conta_id TEXT NOT NULL,
    conta TEXT NOT NULL,
    data TEXT NOT NULL,
    descricao TEXT NOT NULL,
    chave TEXT NOT NULL,
    categoria_original TEXT NOT NULL,
    valor REAL NOT NULL,
    interno_original INTEGER NOT NULL,
    pendente INTEGER NOT NULL
)
"""
CRIAR_INSTANTANEO = """
CREATE TABLE IF NOT EXISTS instantaneo (chave TEXT PRIMARY KEY, valor TEXT NOT NULL)
"""
CRIAR_SALDOS = """
CREATE TABLE IF NOT EXISTS saldos_investimento (
    data TEXT NOT NULL, investimento_id TEXT NOT NULL, saldo REAL NOT NULL,
    PRIMARY KEY (data, investimento_id)
)
"""
CRIAR_MOVIMENTOS = """
CREATE TABLE IF NOT EXISTS movimentos_investimento (
    id TEXT PRIMARY KEY, investimento_id TEXT NOT NULL, data TEXT NOT NULL, valor REAL NOT NULL
)
"""
COLUNAS_CARTAO = {"parcela": "INTEGER", "parcelas_total": "INTEGER",
                  "data_compra": "TEXT", "mes_fatura": "TEXT"}
COLUNAS = ("id", "conta_id", "conta", "data", "descricao", "chave", "categoria_original",
           "valor", "interno_original", "pendente", *COLUNAS_CARTAO)


def _abrir(caminho):
    conexao = sqlite3.connect(caminho)
    conexao.row_factory = sqlite3.Row
    conexao.execute(CRIAR_TABELA)
    conexao.execute(CRIAR_INSTANTANEO)
    conexao.execute(CRIAR_SALDOS)
    conexao.execute(CRIAR_MOVIMENTOS)
    existentes = {c["name"] for c in conexao.execute("PRAGMA table_info(transacoes)")}
    for coluna, tipo in COLUNAS_CARTAO.items():
        if coluna not in existentes:
            conexao.execute(f"ALTER TABLE transacoes ADD COLUMN {coluna} {tipo}")
    return conexao


def tem_dados(caminho, conta_id):
    """Linhas sem dados de cartão vêm de versão antiga e pedem uma carga completa."""
    with closing(_abrir(caminho)) as conexao:
        total, antigas = conexao.execute(
            "SELECT COUNT(*), COUNT(*) - COUNT(parcelas_total) FROM transacoes WHERE conta_id = ?",
            (conta_id,)).fetchone()
    return total > 0 and antigas == 0


def salvar(caminho, conta_id, inicio, transacoes):
    """Atualiza o que veio da Pluggy sem nunca apagar transação já confirmada.

    Pendentes saem antes de gravar: quando confirmam podem voltar com outro id ou nem
    voltar, e ficariam duplicadas para sempre.
    """
    linhas = [tuple(conta_id if c == "conta_id" else t[c] for c in COLUNAS) for t in transacoes]
    marcadores = ",".join("?" * len(COLUNAS))
    with closing(_abrir(caminho)) as conexao, conexao:
        conexao.execute("DELETE FROM transacoes WHERE pendente = 1 AND conta_id = ? AND data >= ?",
                        (conta_id, inicio))
        conexao.executemany(
            f"INSERT OR REPLACE INTO transacoes ({','.join(COLUNAS)}) VALUES ({marcadores})", linhas)
        # O que a Pluggy não devolve mais não vai ganhar esses dados: não pede nova carga completa.
        conexao.execute("UPDATE transacoes SET parcelas_total = 0, parcela = 0, data_compra = '', "
                        "mes_fatura = '' WHERE conta_id = ? AND parcelas_total IS NULL", (conta_id,))


def carregar(caminho):
    with closing(_abrir(caminho)) as conexao:
        linhas = conexao.execute("SELECT * FROM transacoes").fetchall()
    return [{
        **dict(linha),
        "categoria": linha["categoria_original"],
        "interno": bool(linha["interno_original"]),
        "interno_original": bool(linha["interno_original"]),
        "pendente": bool(linha["pendente"]),
        "parcela": linha["parcela"] or 0,
        "parcelas_total": linha["parcelas_total"] or 0,
        "data_compra": linha["data_compra"] or "",
        "mes_fatura": linha["mes_fatura"] or "",
    } for linha in linhas]


def salvar_instantaneo(caminho, dados):
    """Guarda contas e faturas da última atualização para abrir sem depender da Pluggy."""
    linhas = [(chave, json.dumps(valor, ensure_ascii=False)) for chave, valor in dados.items()]
    with closing(_abrir(caminho)) as conexao, conexao:
        conexao.executemany("INSERT OR REPLACE INTO instantaneo (chave, valor) VALUES (?, ?)", linhas)


def salvar_saldos(caminho, dia, saldos):
    """Um saldo por caixinha por dia (o último do dia vale): é o que permite medir o rendimento."""
    linhas = [(dia, investimento_id, saldo) for investimento_id, saldo in saldos.items()]
    with closing(_abrir(caminho)) as conexao, conexao:
        conexao.executemany("INSERT OR REPLACE INTO saldos_investimento VALUES (?, ?, ?)", linhas)


def carregar_saldos(caminho):
    with closing(_abrir(caminho)) as conexao:
        return [{"data": l["data"], "investimento_id": l["investimento_id"], "saldo": l["saldo"]}
                for l in conexao.execute("SELECT * FROM saldos_investimento")]


def salvar_movimentos(caminho, movimentos):
    """Aportes (+) e resgates (-) de cada caixinha, para não contá-los como rendimento."""
    linhas = [(m["id"], m["investimento_id"], m["data"], m["valor"]) for m in movimentos]
    with closing(_abrir(caminho)) as conexao, conexao:
        conexao.executemany("INSERT OR REPLACE INTO movimentos_investimento VALUES (?, ?, ?, ?)", linhas)


def carregar_movimentos(caminho):
    with closing(_abrir(caminho)) as conexao:
        return [{"id": l["id"], "investimento_id": l["investimento_id"], "data": l["data"],
                 "valor": l["valor"]}
                for l in conexao.execute("SELECT * FROM movimentos_investimento")]


def carregar_instantaneo(caminho):
    with closing(_abrir(caminho)) as conexao:
        return {l["chave"]: json.loads(l["valor"])
                for l in conexao.execute("SELECT chave, valor FROM instantaneo")}
