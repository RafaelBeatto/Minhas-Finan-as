"""Gera a planilha Excel com o extrato completo e os resumos do app."""
from datetime import date
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
import financeiro as fin

REAIS = '"R$" #,##0.00;[Red]-"R$" #,##0.00'
DATA = "dd/mm/yyyy"
PORCENTO = "0%"
CABECALHO = PatternFill("solid", fgColor="252C3E")


def _data(texto):
    return date.fromisoformat(texto[:10]) if texto else None


def _aba(planilha, titulo, colunas, linhas):
    """colunas: (título, largura, formato). Cada linha traz os valores na mesma ordem."""
    aba = planilha.create_sheet(titulo)
    for indice, (nome, largura, _formato) in enumerate(colunas, 1):
        celula = aba.cell(row=1, column=indice, value=nome)
        celula.font = Font(bold=True, color="FFFFFF")
        celula.fill = CABECALHO
        celula.alignment = Alignment(vertical="center")
        aba.column_dimensions[get_column_letter(indice)].width = largura
    for numero, linha in enumerate(linhas, 2):
        for indice, valor in enumerate(linha, 1):
            celula = aba.cell(row=numero, column=indice, value=valor)
            if isinstance(valor, str):
                # Descrição vem do banco: texto iniciado por "=" não pode virar fórmula.
                celula.data_type = "s"
            if colunas[indice - 1][2]:
                celula.number_format = colunas[indice - 1][2]
    aba.freeze_panes = "A2"
    if linhas:
        aba.auto_filter.ref = aba.dimensions
    return aba


def _extrato(planilha, transacoes):
    ordenadas = sorted(transacoes, key=lambda t: t["data"], reverse=True)
    _aba(planilha, "Extrato", (("Data", 12, DATA), ("Descrição", 44, None), ("Categoria", 24, None),
                               ("Conta", 20, None), ("Valor", 14, REAIS),
                               ("Conta nos totais", 16, None), ("Pendente", 10, None),
                               ("Parcela", 10, None)),
         [(_data(t["data"]), t["descricao"], t["categoria"], t["conta"], t["valor"],
           "Não" if t["interno"] else "Sim", "Sim" if t["pendente"] else "Não",
           f'{t["parcela"]}/{t["parcelas_total"]}' if t["parcelas_total"] > 1 else "")
          for t in ordenadas])


def _meses(planilha, transacoes):
    _aba(planilha, "Meses", (("Mês", 12, None), ("Entradas", 14, REAIS), ("Saídas", 14, REAIS),
                             ("Resultado", 14, REAIS), ("Saídas x mês anterior", 22, REAIS)),
         [(fin.nome_mes(m["mes"]), m["entradas"], m["saidas"], m["resultado"], m["variacao"])
          for m in fin.resumo_mensal(transacoes)])


def _categorias(planilha, transacoes):
    meses, gastos = fin.gastos_por_mes(transacoes)
    colunas = [("Categoria", 28, None)] + [(fin.nome_mes(m), 13, REAIS) for m in meses]
    colunas.append(("Total", 14, REAIS))
    linhas = [(categoria, *[valores.get(m, 0) for m in meses], sum(valores.values()))
              for categoria, valores in gastos]
    _aba(planilha, "Categorias", colunas, linhas)


def _orcamento(planilha, transacoes, orcamento, hoje):
    _aba(planilha, "Orçamento", (("Categoria", 28, None), ("Limite", 14, REAIS), ("Gasto no mês", 14, REAIS),
                                 ("Resta", 14, REAIS), ("Uso", 8, PORCENTO), ("Média 3 meses", 15, REAIS)),
         [(l["categoria"], l["limite"], l["gasto"], l["restante"], l["uso"], l["media"])
          for l in fin.situacao_orcamento(transacoes, orcamento, hoje)])


def _assinaturas(planilha, transacoes, ignoradas, hoje):
    _aba(planilha, "Assinaturas", (("Cobrança", 36, None), ("Categoria", 24, None), ("Valor", 14, REAIS),
                                   ("Última", 12, DATA), ("Próxima", 12, DATA), ("Situação", 22, None)),
         [(a["descricao"], a["categoria"], a["valor"], _data(a["ultima"]),
           _data(a["proxima"]) if a["ativa"] else None,
           "Ativa" if a["ativa"] else "Sem cobrança recente")
          for a in fin.detectar_assinaturas(transacoes, hoje, ignoradas)])


def _parcelas(planilha, transacoes, hoje):
    _aba(planilha, "Parcelas", (("Compra", 36, None), ("Parcela", 10, None), ("Valor", 14, REAIS),
                                ("Falta pagar", 14, REAIS), ("Termina", 12, None)),
         [(a["descricao"], f'{a["parcela"]}/{a["total"]}', a["valor"], a["restante"],
           fin.nome_mes(a["fim"])) for a in fin.parcelas_abertas(transacoes, hoje)])


def gerar_planilha(caminho, transacoes, orcamento, ignoradas, hoje):
    planilha = Workbook()
    planilha.remove(planilha.active)
    _extrato(planilha, transacoes)
    _meses(planilha, transacoes)
    _categorias(planilha, transacoes)
    _orcamento(planilha, transacoes, orcamento, hoje)
    _assinaturas(planilha, transacoes, ignoradas, hoje)
    _parcelas(planilha, transacoes, hoje)
    planilha.save(caminho)
