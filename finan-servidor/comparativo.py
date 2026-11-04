"""Comparação entre dois meses: um cálculo só para gráficos, indicadores e análise.

Os totais vêm de financeiro.py, para os números baterem com os do resto do sistema.
Diferença é sempre segundo mês menos primeiro mês, em qualquer ordem cronológica.
"""
import calendar
import financeiro as fin

TOLERANCIA = 0.005  # menos de meio centavo é resíduo da soma, não diferença de verdade
MESES_EVOLUCAO = 12
ITENS_RANKING = 5
AUMENTOU, DIMINUIU, IGUAL = "Aumentou", "Diminuiu", "Permaneceu igual"
NOVA, SEM_MOVIMENTO = "Nova categoria", "Sem movimentação"
NOVO_GASTO = "Novo gasto"


def quase_zero(valor):
    return abs(valor) < TOLERANCIA


def comparar_valores(a, b, novo=None):
    """Diferença e variação. Sem base positiva não há percentual: mostra o rótulo, se houver.

    Base negativa só acontece no saldo, e ali o percentual da fórmula inverteria o sentido.
    """
    linha = {"a": a, "b": b, "diferenca": b - a, "percentual": None, "rotulo": None}
    if quase_zero(a) and quase_zero(b):
        linha["rotulo"] = SEM_MOVIMENTO
    elif quase_zero(a):
        linha["rotulo"] = novo
    elif a > 0:
        linha["percentual"] = (b - a) / a * 100
    return linha


def situacao(a, b, teve_gasto_antes):
    if quase_zero(a) and quase_zero(b):
        return SEM_MOVIMENTO
    if quase_zero(a):
        return AUMENTOU if teve_gasto_antes else NOVA
    if quase_zero(b - a):
        return IGUAL
    return AUMENTOU if b > a else DIMINUIU


def _linhas_categorias(gastos, a, b):
    """Uma linha para cada categoria com gasto no histórico; as maiores vêm primeiro."""
    linhas = []
    for categoria, valores in gastos:
        va, vb = valores.get(a, 0), valores.get(b, 0)
        anteriores = [m for m in valores if m < b and m != a]
        outros = [m for m in valores if m not in (a, b)]
        # Quem só teve gasto no segundo mês "já teve gastos antes": não vale citar mês posterior.
        referencia = anteriores if quase_zero(va) else outros
        linhas.append({
            "categoria": categoria, **comparar_valores(va, vb, NOVO_GASTO),
            "situacao": situacao(va, vb, bool(anteriores)),
            "ultimo_outro_mes": max(referencia, default=None),
        })
    return sorted(linhas, key=lambda l: (-max(l["a"], l["b"]), l["categoria"]))


def _rankings(linhas):
    """Sem base no primeiro mês não há percentual para ordenar: esses casos ficam em novas."""
    com_percentual = [l for l in linhas if l["percentual"] is not None]
    aumentos = [l for l in com_percentual if l["diferenca"] >= TOLERANCIA]
    reducoes = [l for l in com_percentual if l["diferenca"] <= -TOLERANCIA]
    aumentos.sort(key=lambda l: (-l["percentual"], -l["diferenca"]))
    reducoes.sort(key=lambda l: (l["percentual"], l["diferenca"]))
    return aumentos[:ITENS_RANKING], reducoes[:ITENS_RANKING]


def _categorias_de_um_periodo(linhas):
    """Separa a categoria inédita da que só não teve lançamento em um dos meses."""
    resultado = []
    for l in linhas:
        if quase_zero(l["a"]) == quase_zero(l["b"]):
            continue
        so_no_primeiro = quase_zero(l["b"])
        if so_no_primeiro:
            tipo = "so_primeiro"
        else:
            tipo = "nova" if l["situacao"] == NOVA else "retomada"
        resultado.append({"categoria": l["categoria"], "tipo": tipo,
                          "valor": l["a"] if so_no_primeiro else l["b"],
                          "ultimo_outro_mes": l["ultimo_outro_mes"]})
    return resultado


def _evolucao(mensal, a, b):
    """Do primeiro ao último mês comparado, completando com vizinhos até 12 meses."""
    meses = sorted(mensal)
    inicio, fim = meses.index(min(a, b)), meses.index(max(a, b))
    while fim - inicio + 1 < MESES_EVOLUCAO and (inicio > 0 or fim < len(meses) - 1):
        inicio = max(inicio - 1, 0)
        if fim - inicio + 1 < MESES_EVOLUCAO:
            fim = min(fim + 1, len(meses) - 1)
    return [{"mes": m, "saidas": mensal[m]["saidas"]} for m in meses[inicio:fim + 1]]


def _mes_em_andamento(transacoes, mensal, a, b, hoje):
    """Compara o mês corrente com o mesmo número de dias do outro mês."""
    atual = hoje.isoformat()[:7]
    if atual not in (a, b):
        return None
    outro = b if atual == a else a
    trecho = [t for t in transacoes if t["data"][:7] == outro and int(t["data"][8:10]) <= hoje.day]
    entradas, saidas, _ = fin.totais(trecho)
    ano, numero = map(int, atual.split("-"))
    return {"mes": atual, "outro": outro, "dia": hoje.day,
            "dias_no_mes": calendar.monthrange(ano, numero)[1],
            "receitas": mensal[atual]["entradas"], "despesas": mensal[atual]["saidas"],
            "receitas_outro": entradas, "despesas_outro": saidas}


def resumo_e_categorias(transacoes, a, b):
    """Totais e linhas por categoria; mês sem movimento conta como zero."""
    mensal = {m["mes"]: m for m in fin.resumo_mensal(transacoes)}
    vazio = {"entradas": 0, "saidas": 0, "resultado": 0}
    ma, mb = mensal.get(a, vazio), mensal.get(b, vazio)
    return {
        "resumo": {
            "receitas": comparar_valores(ma["entradas"], mb["entradas"], "Nova receita"),
            "despesas": comparar_valores(ma["saidas"], mb["saidas"], NOVO_GASTO),
            "saldo": comparar_valores(ma["resultado"], mb["resultado"]),
        },
        "categorias": _linhas_categorias(fin.gastos_por_mes(transacoes)[1], a, b),
    }


def comparar(transacoes, a, b, hoje):
    """Resumo, categorias e rankings. Lança ValueError se um dos meses não tiver movimento."""
    mensal = {m["mes"]: m for m in fin.resumo_mensal(transacoes)}
    if a not in mensal or b not in mensal:
        raise ValueError("mês sem movimentações")
    totais = resumo_e_categorias(transacoes, a, b)
    linhas = totais["categorias"]
    aumentos, reducoes = _rankings(linhas)
    return {
        "primeiro": a,
        "segundo": b,
        **totais,
        "aumentos": aumentos,
        "reducoes": reducoes,
        "um_periodo": _categorias_de_um_periodo(linhas),
        "evolucao": _evolucao(mensal, a, b),
        "em_andamento": _mes_em_andamento(transacoes, mensal, a, b, hoje),
    }
