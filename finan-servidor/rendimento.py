"""Quanto a caixinha rendeu por semana e por mês.

Rendimento = variação do saldo - aportes líquidos (depósitos - resgates) no período.
O saldo só é conhecido a partir do dia em que o app começou a guardá-lo, então o primeiro
período pode ser parcial.
"""
from datetime import date, timedelta

NOMES_MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")


def _total_por_dia(saldos):
    totais = {}
    for s in saldos:
        totais[s["data"]] = totais.get(s["data"], 0.0) + s["saldo"]
    return totais


def _calcular(totais, movimentos, inicio, fim, rotulo):
    datas = sorted(totais)
    antes = [d for d in datas if d < inicio.isoformat()]
    dentro = [d for d in datas if inicio.isoformat() <= d <= fim.isoformat()]
    if antes:
        base_data, parcial = antes[-1], False
    elif dentro:
        base_data, parcial = dentro[0], True
    else:
        return None
    finais = [d for d in dentro if d > base_data]
    if not finais:
        return None
    fim_data = finais[-1]
    base, final = totais[base_data], totais[fim_data]
    aportes = sum(m["valor"] for m in movimentos if base_data < m["data"] <= fim_data)
    rendeu = final - base - aportes
    return {"rotulo": rotulo, "de": base_data, "ate": fim_data, "saldo_inicial": base,
            "saldo_final": final, "aportes": aportes, "rendimento": rendeu,
            "percentual": rendeu / base if base > 0 else None, "parcial": parcial}


def _semanas(totais, movimentos, hoje, quantidade):
    segunda = hoje - timedelta(days=hoje.weekday())
    saida = []
    for i in range(quantidade):
        inicio = segunda - timedelta(weeks=i)
        fim = min(inicio + timedelta(days=6), hoje)
        rotulo = f"{inicio.day:02d}/{inicio.month:02d} a {(inicio + timedelta(days=6)).day:02d}/" \
                 f"{(inicio + timedelta(days=6)).month:02d}"
        linha = _calcular(totais, movimentos, inicio, fim, rotulo)
        if linha:
            saida.append(linha)
    return saida


def _meses(totais, movimentos, hoje, quantidade):
    saida = []
    ano, mes = hoje.year, hoje.month
    for _ in range(quantidade):
        inicio = date(ano, mes, 1)
        proximo = date(ano + (mes == 12), mes % 12 + 1, 1)
        fim = min(proximo - timedelta(days=1), hoje)
        linha = _calcular(totais, movimentos, inicio, fim, f"{NOMES_MESES[mes - 1]}/{ano}")
        if linha:
            saida.append(linha)
        ano, mes = (ano - 1, 12) if mes == 1 else (ano, mes - 1)
    return saida


def resumo(saldos, movimentos, hoje, semanas=8, meses=6):
    """Mais recente primeiro. Cada item traz 'variacao' em relação ao período anterior."""
    totais = _total_por_dia(saldos)
    resultado = {"semanas": _semanas(totais, movimentos, hoje, semanas),
                 "meses": _meses(totais, movimentos, hoje, meses),
                 "desde": min(totais) if totais else None,
                 "tem_aportes": bool(movimentos)}
    for chave in ("semanas", "meses"):
        linhas = resultado[chave]
        for atual, anterior in zip(linhas, linhas[1:]):
            atual["variacao"] = atual["rendimento"] - anterior["rendimento"]
        if linhas:
            linhas[-1]["variacao"] = None
    return resultado
