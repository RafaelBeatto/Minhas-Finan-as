"""Inteligência financeira local: estatística e regras sobre o histórico, sem serviços externos.

Só observa os dados: nunca grava nada, nunca atribui causa a um gasto e nunca conclui sem
evidência. Cada resultado diz de que tipo é, para a interface separar fato de inferência.
O mês corrente fica fora das estatísticas, porque ainda não terminou.
"""
import calendar
import math
import statistics
from dataclasses import dataclass, replace
from datetime import date
import comparativo
import financeiro as fin

CONFIRMADO, PADRAO, TENDENCIA = "confirmado", "padrao", "tendencia"
ESTIMATIVA, INSUFICIENTE = "estimativa", "insuficiente"

MINIMO_REAIS = 10  # abaixo disso uma mudança não merece menção, seja qual for a renda
PARCELA_RELEVANTE = 0.03  # uma mudança relevante vale ao menos 3% do gasto mensal típico
DIA_INICIO_PARCIAL = 10  # histórico que começa depois disso tem o primeiro mês incompleto

MESES_TENDENCIA = 6
MINIMO_MESES_TENDENCIA = 3
CONCORDANCIA_TENDENCIA = 0.6  # Kendall: 1 é sempre na mesma direção, 0 é sem direção
VARIACAO_TENDENCIA = 0.2
DISPERSAO_ESTAVEL = 0.25

MINIMO_MESES_BASE = 4  # para dizer o que é habitual numa categoria
LIMITE_MAD = 5.19  # z robusto de 3,5 expresso em desvios absolutos da mediana
FATOR_INCOMUM = 1.5
MESES_RECENTES = 3
MINIMO_MESES_HABITO = 6
VARIACAO_HABITO = 0.3
ESPALHAMENTO_HABITO = 0.4

MINIMO_DIAS_PADRAO = 8
MINIMO_MESES_PADRAO = 3
SIGNIFICANCIA = 0.01  # rígida porque cada categoria é testada mais de uma vez
FATIA_FIM_DE_SEMANA = 0.5
FATIA_PERIODO_MES = 0.6
DIA_FIM_INICIO_MES = 10
DIA_COMECO_FIM_MES = 21
PRESENCA_RECORRENTE = 0.8
MINIMO_DIAS_POR_MES = 2

MINIMO_MESES_PREVISAO = 4
PRESENCA_PREVISAO = 0.75
DISPERSAO_PREVISAO = 0.75
CATEGORIAS_PREVISAO = 3

MAXIMO_ALERTAS = 5
MAXIMO_PADROES = 6
MAXIMO_ROTINAS = 2
MAXIMO_POR_TENDENCIA = 5
FATIA_ATENCAO = 0.15
FATIA_COMPRA_UNICA = 0.3
FATIA_CONCENTRACAO = 0.5
MINIMO_DIAS_HABITO_NOVO = 3
MINIMO_COMPRAS_CATEGORIA = 8
FATOR_COMPRA_INCOMUM = 3
MINIMO_DIAS_FREQUENTE = 5
MINIMO_MESES_RESULTADO = 3
SALDO_QUEDA = 0.25

brl = fin.formatar_brl
nome = fin.nome_mes


@dataclass
class Base:
    """O que todas as análises consultam, calculado uma vez por pedido."""
    hoje: date
    compras: list          # despesas individuais, sem movimentação interna
    habituais: list        # compras que dizem algo sobre comportamento
    gastos: dict           # categoria -> {mês: valor}
    mensal: dict           # mês -> entradas, saídas e resultado
    fechados: list         # meses completos, em ordem
    relevante: float       # menor diferença em reais que merece menção
    assinaturas: list      # cobranças recorrentes detectadas no histórico


def _percentual(valor):
    texto = f"{abs(valor):.1f}".replace(".", ",").removesuffix(",0")
    return f"{texto}%"


def _com(categoria):
    return "sem categoria" if categoria == fin.SEM_CATEGORIA else f"com {categoria}"


def _lista(itens):
    return ", ".join(itens[:-1]) + f" e {itens[-1]}" if len(itens) > 1 else "".join(itens)


def _data_br(data):
    return fin.formatar_data(data)


def _intervalo(meses):
    return nome(meses[0]) if len(meses) == 1 else f"{nome(meses[0])} a {nome(meses[-1])}"


def montar_base(transacoes, hoje, ignoradas=()):
    atual = hoje.isoformat()[:7]
    mensal = {m["mes"]: m for m in fin.resumo_mensal(transacoes)}
    compras = [{"mes": t["data"][:7], "data": t["data"][:10],
                "dia": (t["data_compra"] or t["data"])[:10],
                "valor": -t["valor"], "categoria": t["categoria"], "descricao": t["descricao"],
                "chave": t["chave"], "parcelada": t["parcelas_total"] > 1}
               for t in transacoes if not t["interno"] and t["valor"] < 0]
    assinaturas = fin.detectar_assinaturas(transacoes, hoje, ignoradas)
    recorrentes = {a["chave"] for a in assinaturas}
    fechados = sorted(m for m in mensal if m < atual)
    # A carga pode começar no meio de um mês: esse mês pareceria barato sem ter sido.
    inicio = min((t["data"] for t in transacoes), default="")
    if fechados and inicio[:7] == fechados[0] and int(inicio[8:10]) > DIA_INICIO_PARCIAL:
        fechados = fechados[1:]
    tipico = statistics.median(mensal[m]["saidas"] for m in fechados) if fechados else 0
    return Base(hoje, compras,
                [c for c in compras if not c["parcelada"] and c["chave"] not in recorrentes],
                dict(fin.gastos_por_mes(transacoes)[1]), mensal, fechados,
                max(MINIMO_REAIS, tipico * PARCELA_RELEVANTE), assinaturas)


def _serie(base, categoria, meses):
    valores = base.gastos.get(categoria, {})
    return [valores.get(m, 0) for m in meses]


def _posicoes(meses):
    """Mês sem nenhuma transação fica fora da série, mas a distância entre os outros é real."""
    return [int(m[:4]) * 12 + int(m[5:7]) for m in meses]


def direcao_estatistica(valores, posicoes=None):
    """Concordância de Kendall e inclinação de Theil-Sen: uma compra isolada não as distorce."""
    posicoes = posicoes or range(len(valores))
    pares = [(i, j) for i in range(len(valores)) for j in range(i + 1, len(valores))]
    sinais = sum((valores[j] > valores[i]) - (valores[j] < valores[i]) for i, j in pares)
    inclinacao = statistics.median((valores[j] - valores[i]) / (posicoes[j] - posicoes[i])
                                   for i, j in pares)
    return sinais / len(pares), inclinacao


def classificar_serie(valores, relevante, posicoes=None):
    """Devolve alta, queda, estavel ou None. Exige ao menos três meses de série."""
    if len(valores) < MINIMO_MESES_TENDENCIA or not any(valores):
        return None
    posicoes = posicoes or range(len(valores))
    concordancia, inclinacao = direcao_estatistica(valores, posicoes)
    media = statistics.mean(valores)
    variacao = inclinacao * (posicoes[-1] - posicoes[0])
    ativos = sum(v > 0 for v in valores)
    if (abs(concordancia) >= CONCORDANCIA_TENDENCIA and abs(variacao) >= relevante
            and abs(variacao) / media >= VARIACAO_TENDENCIA):
        if variacao > 0 and ativos >= MINIMO_MESES_TENDENCIA:
            return "alta"
        if variacao < 0 and ativos >= 2:
            return "queda"
    if (ativos == len(valores) and media >= relevante
            and statistics.pstdev(valores) / media <= DISPERSAO_ESTAVEL):
        return "estavel"
    return None


def _altas_seguidas(valores):
    altas = 0
    for anterior, seguinte in zip(reversed(valores[:-1]), reversed(valores[1:])):
        if seguinte <= anterior:
            break
        altas += 1
    return altas


def _texto_tendencia(assunto, valores, meses, direcao):
    verbo = "vêm aumentando" if direcao == "alta" else "vêm diminuindo"
    texto = (f"{assunto} {verbo}: de {brl(valores[0])} em {nome(meses[0])} "
             f"para {brl(valores[-1])} em {nome(meses[-1])}.")
    altas = _altas_seguidas(valores)
    if direcao == "alta" and altas >= 2:
        texto += f" Foram {altas} altas seguidas."
    return texto


def _item_tendencia(assunto, valores, meses, direcao, categoria=None, subir_e_bom=False):
    posicoes = _posicoes(meses)
    concordancia, inclinacao = direcao_estatistica(valores, posicoes)
    return {
        "tipo": TENDENCIA, "direcao": direcao, "categoria": categoria,
        "favoravel": (direcao == "alta") == subir_e_bom,
        "titulo": categoria or assunto,
        "texto": _texto_tendencia(assunto, valores, meses, direcao),
        "motivo": (f"{len(valores)} meses fechados ({_intervalo(meses)}), concordância de "
                   f"{_percentual(abs(concordancia) * 100)} na direção e variação de cerca de "
                   f"{brl(abs(inclinacao))} por mês."),
        "peso": abs(inclinacao) * (posicoes[-1] - posicoes[0]),
    }


def tendencias(base, mudancas=()):
    """Quem mudou de patamar e parou ali já aparece como mudança de hábito."""
    meses = base.fechados[-MESES_TENDENCIA:]
    grupos = {"meses": len(meses), "geral": [], "alta": [], "queda": [], "estaveis": []}
    if len(meses) < MINIMO_MESES_TENDENCIA:
        return grupos
    posicoes = _posicoes(meses)
    for rotulo, campo in (("Suas despesas totais", "saidas"), ("Suas receitas", "entradas")):
        valores = [base.mensal[m][campo] for m in meses]
        direcao = classificar_serie(valores, base.relevante, posicoes)
        if direcao in ("alta", "queda"):
            grupos["geral"].append(_item_tendencia(rotulo, valores, meses, direcao,
                                                   subir_e_bom=campo == "entradas"))
    for categoria in base.gastos:
        if categoria in mudancas:
            continue
        valores = _serie(base, categoria, meses)
        direcao = classificar_serie(valores, base.relevante, posicoes)
        if direcao in ("alta", "queda"):
            grupos[direcao].append(_item_tendencia(f"Seus gastos {_com(categoria)}", valores, meses,
                                                   direcao, categoria))
        elif direcao == "estavel":
            grupos["estaveis"].append({"categoria": categoria, "media": statistics.mean(valores)})
    for chave in ("alta", "queda"):
        grupos[chave] = sorted(grupos[chave], key=lambda i: -i["peso"])[:MAXIMO_POR_TENDENCIA]
    grupos["estaveis"].sort(key=lambda e: -e["media"])
    return grupos


def _habitual(valores):
    mediana = statistics.median(valores)
    return mediana, statistics.median(abs(v - mediana) for v in valores)


def fora_do_padrao(base, categoria, mes):
    """Compara o gasto do mês com os meses fechados anteriores, pela mediana.

    Mês em andamento pode entrar: o gasto só cresce, então ultrapassar já é definitivo.
    """
    anteriores = [m for m in base.fechados if m < mes][-12:]
    if len(anteriores) < MINIMO_MESES_BASE:
        return None
    valor = base.gastos.get(categoria, {}).get(mes, 0)
    historico = _serie(base, categoria, anteriores)
    mediana, desvio = _habitual(historico)
    ativos = sum(v > 0 for v in historico)
    if valor - mediana < base.relevante:
        return None
    resultado = {"categoria": categoria, "mes": mes, "valor": valor, "mediana": mediana,
                 "meses": anteriores, "ativos": ativos, "excesso": valor - mediana}
    if ativos <= 1:
        return {**resultado, "tipo": "incomum"}
    if valor >= max(mediana + LIMITE_MAD * desvio, mediana * FATOR_INCOMUM):
        return {**resultado, "tipo": "acima"}
    return None


def _alerta_fora_do_padrao(achado, em_andamento):
    mes, categoria = nome(achado["mes"]), achado["categoria"]
    parcial = "até agora, " if em_andamento else ""
    periodo = _intervalo(achado["meses"])
    if achado["tipo"] == "incomum":
        return {"titulo": f"{categoria} costuma não ter gastos",
                "texto": f"Em {mes}, {parcial}foram {brl(achado['valor'])} {_com(categoria)}.",
                "motivo": f"Apareceu em {achado['ativos']} de {len(achado['meses'])} meses "
                          f"fechados ({periodo}).",
                "peso": achado["excesso"]}
    return {"titulo": f"{categoria} acima do habitual",
            "texto": f"Em {mes}, {parcial}foram {brl(achado['valor'])} {_com(categoria)}, "
                     f"contra {brl(achado['mediana'])} em um mês típico.",
            "motivo": f"Mediana de {len(achado['meses'])} meses fechados ({periodo}); o valor "
                      "ultrapassa bastante a variação normal da categoria.",
            "peso": achado["excesso"]}


def _alerta_saldo(comparacao, base):
    if comparacao["em_andamento"]:
        return None
    saldo = comparacao["resumo"]["saldo"]
    # Queda é do mês mais antigo para o mais novo, em qualquer ordem de seleção.
    antigo, novo = (saldo["a"], comparacao["primeiro"]), (saldo["b"], comparacao["segundo"])
    if antigo[1] > novo[1]:
        antigo, novo = novo, antigo
    queda = antigo[0] - novo[0]
    if queda < max(base.relevante, abs(antigo[0]) * SALDO_QUEDA):
        return None
    negativo = " As despesas superaram as receitas." if novo[0] < 0 else ""
    return {"titulo": "Saldo mensal em queda",
            "texto": f"O saldo foi de {brl(antigo[0])} em {nome(antigo[1])} para "
                     f"{brl(novo[0])} em {nome(novo[1])}.{negativo}",
            "motivo": f"Queda de {brl(queda)} entre os dois meses escolhidos.", "peso": queda}


def _alertas_assinatura(base, alvo):
    alertas = []
    for a in base.assinaturas:
        if a["ativa"] and a["aumento"] and a["ultima"][:7] == alvo:
            alertas.append({
                "titulo": f"{a['descricao']} acima do habitual",
                "texto": f"A cobrança de {_data_br(a['ultima'])} foi de {brl(a['valor'])}, "
                         f"{brl(a['aumento'])} a mais que a anterior.",
                "motivo": f"Cobrança recorrente vista em {a['meses']} meses.",
                "peso": a["aumento"]})
    return alertas


def alertas(comparacao, base, grupos):
    """Olha o mais recente dos dois meses e só fica com os alertas de maior valor."""
    alvo = max(comparacao["primeiro"], comparacao["segundo"])
    em_andamento = alvo == base.hoje.isoformat()[:7]
    achados = [fora_do_padrao(base, c, alvo) for c in base.gastos]
    lista = [_alerta_fora_do_padrao(a, em_andamento) for a in achados if a]
    lista += _alertas_assinatura(base, alvo)
    saldo = _alerta_saldo(comparacao, base)
    if saldo:
        lista.append(saldo)
    for item in grupos["geral"]:
        if item["titulo"] == "Suas despesas totais" and item["direcao"] == "alta":
            lista.append({"titulo": "Despesas totais crescendo", "texto": item["texto"],
                          "motivo": item["motivo"], "peso": item["peso"]})
    return sorted(lista, key=lambda a: -a["peso"])[:MAXIMO_ALERTAS]


def _cauda_binomial(acertos, total, chance):
    """Chance de ver tantos acertos, ou mais, se o gasto caísse em qualquer dia ao acaso."""
    return sum(math.comb(total, k) * chance ** k * (1 - chance) ** (total - k)
               for k in range(acertos, total + 1))


def _por_categoria(compras):
    grupos = {}
    for c in compras:
        grupos.setdefault(c["categoria"], []).append(c)
    return grupos


def _padrao_fim_de_semana(categoria, compras):
    dias = {c["dia"] for c in compras}
    fim_de_semana = {d for d in dias if date.fromisoformat(d).weekday() >= 5}
    fatia = len(fim_de_semana) / len(dias)
    if fatia < FATIA_FIM_DE_SEMANA or _cauda_binomial(len(fim_de_semana), len(dias),
                                                      2 / 7) >= SIGNIFICANCIA:
        return None
    return {"tipo": PADRAO, "titulo": "Padrão de consumo",
            "texto": f"Você costuma gastar mais {_com(categoria)} nos finais de semana.",
            "motivo": f"{len(fim_de_semana)} de {len(dias)} dias com gasto caíram em sábado ou "
                      f"domingo ({_percentual(fatia * 100)}); ao acaso seriam cerca de 29%.",
            "peso": fatia}


def _padrao_periodo_mes(categoria, compras):
    meses = {c["mes"] for c in compras}
    dias = {c["dia"] for c in compras}
    periodos = (("no início de cada mês", lambda d: d <= DIA_FIM_INICIO_MES, 10 / 30.4),
                ("no fim de cada mês", lambda d: d >= DIA_COMECO_FIM_MES, 10.4 / 30.4))
    for rotulo, pertence, chance in periodos:
        dentro = {d for d in dias if pertence(int(d[8:10]))}
        meses_dentro = {d[:7] for d in dentro}
        fatia = len(dentro) / len(dias)
        if (fatia >= FATIA_PERIODO_MES and len(meses_dentro) >= MINIMO_MESES_PADRAO
                and len(meses_dentro) >= len(meses) * FATIA_PERIODO_MES
                and _cauda_binomial(len(dentro), len(dias), chance) < SIGNIFICANCIA):
            return {"tipo": PADRAO, "titulo": "Comportamento recorrente",
                    "texto": f"Você apresenta gastos frequentes {_com(categoria)} {rotulo}.",
                    "motivo": f"{len(dentro)} de {len(dias)} dias com gasto, presentes em "
                              f"{len(meses_dentro)} de {len(meses)} meses com essa categoria.",
                    "peso": fatia}
    return None


def _padrao_frequencia(base, categoria, compras):
    fechadas = [c for c in compras if c["mes"] in base.fechados]
    meses = {c["mes"] for c in fechadas}
    if not base.fechados or len(meses) < max(MINIMO_MESES_PADRAO,
                                             len(base.fechados) * PRESENCA_RECORRENTE):
        return None
    por_mes = len({c["dia"] for c in fechadas}) / len(base.fechados)
    if por_mes < MINIMO_DIAS_POR_MES:
        return None
    media = f"{por_mes:.1f}".replace(".", ",")
    return {"tipo": PADRAO, "titulo": "Comportamento recorrente",
            "texto": f"Gastos {_com(categoria)} fazem parte da sua rotina: em média "
                     f"{media} dias por mês.",
            "motivo": f"Presente em {len(meses)} de {len(base.fechados)} meses fechados.",
            "peso": por_mes / 31}


def _mudanca_habito(base, categoria):
    """Mudança de patamar: os meses recentes destoam do histórico e se parecem entre si.

    Quando eles ainda variam muito o movimento é gradual, e isso é tendência.
    """
    recentes_m = base.fechados[-MESES_RECENTES:]
    anteriores_m = base.fechados[:-MESES_RECENTES][-6:]
    recentes = _serie(base, categoria, recentes_m)
    mediana = statistics.median(_serie(base, categoria, anteriores_m))
    media = statistics.mean(recentes)
    diferenca = media - mediana
    if (mediana <= 0 or abs(diferenca) < base.relevante
            or abs(diferenca) / mediana < VARIACAO_HABITO):
        return None
    if not (all(v > mediana for v in recentes) or all(v < mediana for v in recentes)):
        return None
    if max(recentes) - min(recentes) > abs(diferenca) * ESPALHAMENTO_HABITO:
        return None
    reducao = diferenca < 0
    return {"tipo": PADRAO, "titulo": "Economia" if reducao else "Mudança de hábito",
            "categoria": categoria, "diferenca": diferenca, "media": media, "mediana": mediana,
            "periodo": _intervalo(recentes_m),
            "texto": f"Nos últimos {MESES_RECENTES} meses, seus gastos {_com(categoria)} "
                     f"{'diminuíram' if reducao else 'aumentaram'} em relação ao seu histórico: "
                     f"{brl(media)} por mês, contra {brl(mediana)} antes.",
            "motivo": f"Os {MESES_RECENTES} meses ({_intervalo(recentes_m)}) ficaram "
                      f"{'abaixo' if reducao else 'acima'} da mediana de "
                      f"{_intervalo(anteriores_m)}.",
            "peso": abs(diferenca) / mediana}


def mudancas_de_habito(base):
    if len(base.fechados) < MINIMO_MESES_HABITO:
        return []
    achadas = (_mudanca_habito(base, c) for c in base.gastos)
    return sorted((h for h in achadas if h), key=lambda h: -abs(h["diferenca"]))


def padroes(base, habitos):
    achados, comportamento = [], []
    for categoria, compras in _por_categoria(base.habituais).items():
        dias = {c["dia"] for c in compras}
        if len(dias) >= MINIMO_DIAS_PADRAO and len({c["mes"] for c in compras}) >= MINIMO_MESES_PADRAO:
            achados += [_padrao_fim_de_semana(categoria, compras),
                        _padrao_periodo_mes(categoria, compras)]
        comportamento.append(_padrao_frequencia(base, categoria, compras))
    achados = sorted((a for a in achados if a), key=lambda a: -a["peso"])
    frequentes = sorted((c for c in comportamento if c), key=lambda c: -c["peso"])
    return (habitos + achados + frequentes[:MAXIMO_ROTINAS])[:MAXIMO_PADROES]


def _estimar(valores, relevante, posicoes=None, alvo=None):
    """Mediana dos meses recentes; com tendência firme, a reta robusta prolongada um mês."""
    if len(valores) < MINIMO_MESES_PREVISAO:
        return None
    presenca = sum(v > 0 for v in valores) / len(valores)
    mediana, desvio = _habitual(valores)
    if presenca < PRESENCA_PREVISAO or mediana <= 0 or desvio / mediana > DISPERSAO_PREVISAO:
        return None
    margem = desvio * 1.4826
    posicoes = posicoes or list(range(len(valores)))
    alvo = posicoes[-1] + 1 if alvo is None else alvo
    if classificar_serie(valores, relevante, posicoes) in ("alta", "queda"):
        _, inclinacao = direcao_estatistica(valores, posicoes)
        origem = statistics.median(v - inclinacao * p for p, v in zip(posicoes, valores))
        return max(origem + inclinacao * alvo, 0), margem, "tendência dos meses recentes"
    return mediana, margem, "mediana dos meses recentes"


def _previsao_mes_atual(transacoes, base):
    hoje = base.hoje
    dias = calendar.monthrange(hoje.year, hoje.month)[1]
    previsao = fin.previsao_mes(transacoes, hoje)
    if previsao["projecao"] is None or previsao["gasto"] <= 0 or hoje.day >= dias:
        return None
    return {"tipo": ESTIMATIVA, "titulo": f"Fechamento de {nome(hoje.isoformat()[:7])}",
            "texto": f"Mantendo o ritmo atual, as despesas do mês poderão chegar a "
                     f"aproximadamente {brl(round(previsao['projecao']))}.",
            "motivo": f"{brl(previsao['gasto'])} em {hoje.day} de {dias} dias transcorridos. "
                      "Contas que caem uma vez por mês podem distorcer esse ritmo."}


def previsoes(transacoes, base):
    lista = []
    atual = _previsao_mes_atual(transacoes, base)
    if atual:
        lista.append(atual)
    meses = base.fechados[-MESES_TENDENCIA:]
    mes = fin.somar_meses(base.hoje.isoformat()[:7], 1)
    if not meses:
        return lista
    posicoes, destino = _posicoes(meses), _posicoes([mes])[0]
    total = _estimar([base.mensal[m]["saidas"] for m in meses], base.relevante, posicoes, destino)
    if total:
        contratado = fin.compromissos_proximo_mes(fin.parcelas_abertas(transacoes, base.hoje),
                                                  base.assinaturas, base.hoje)["total"]
        lista.append(_item_previsao(f"Despesas totais em {nome(mes)}", "sua despesa total",
                                    total, meses, contratado))
    categorias = []
    for categoria in base.gastos:
        estimativa = _estimar(_serie(base, categoria, meses), base.relevante, posicoes, destino)
        if estimativa and estimativa[0] >= base.relevante:
            categorias.append((estimativa[0], categoria, estimativa))
    for _, categoria, estimativa in sorted(categorias, key=lambda c: -c[0])[:CATEGORIAS_PREVISAO]:
        lista.append(_item_previsao(f"{categoria} em {nome(mes)}",
                                    f"sua despesa {_com(categoria)}", estimativa, meses, 0))
    return lista


def _item_previsao(titulo, assunto, estimativa, meses, contratado):
    valor, margem, metodo = estimativa
    faixa = f"{brl(round(max(valor - margem, 0)))} a {brl(round(valor + margem))}"
    motivo = f"Baseado em {metodo}, {len(meses)} meses fechados ({_intervalo(meses)})."
    if contratado:
        motivo += f" Parcelas e assinaturas já somam {brl(contratado)} nesse mês."
    return {"tipo": ESTIMATIVA, "titulo": titulo,
            "texto": f"Considerando seu histórico, {assunto} poderá chegar a aproximadamente "
                     f"{brl(round(valor))} no próximo mês (faixa provável: {faixa}).",
            "motivo": motivo}


def _variacao_texto(linha):
    if linha["percentual"] is None:
        return brl(abs(linha["diferenca"]))
    return f"{brl(abs(linha['diferenca']))} ({_percentual(linha['percentual'])})"


def _movimento(linha):
    if comparativo.quase_zero(linha["diferenca"]):
        return f"ficaram em {brl(linha['b'])}"
    verbo = "subiram" if linha["diferenca"] > 0 else "caíram"
    return f"{verbo} {_variacao_texto(linha)}, para {brl(linha['b'])}"


def _compras_do_mes(base, categoria, mes):
    return [c for c in base.compras if c["categoria"] == categoria and c["mes"] == mes]


def _explicar_variacao(base, comparacao, linha):
    """Decompõe a variação em quantidade e valor médio e aponta o estabelecimento que pesou."""
    categoria = linha["categoria"]
    no_a = _compras_do_mes(base, categoria, comparacao["primeiro"])
    no_b = _compras_do_mes(base, categoria, comparacao["segundo"])
    partes = []
    if no_a and no_b:
        medio_a, medio_b = linha["a"] / len(no_a), linha["b"] / len(no_b)
        pela_quantidade = (len(no_b) - len(no_a)) * medio_a
        pelo_valor = (medio_b - medio_a) * len(no_b)
        peso = "a quantidade" if abs(pela_quantidade) >= abs(pelo_valor) else "o valor médio"
        partes.append(f"Em {categoria}, foram de {len(no_a)} para {len(no_b)} compras e o valor "
                      f"médio de {brl(medio_a)} para {brl(medio_b)}: o que mais pesou foi {peso}.")
    por_loja = {}
    for sinal, compras in ((-1, no_a), (1, no_b)):
        for c in compras:
            loja = por_loja.setdefault(c["chave"], {"descricao": c["descricao"], "diferenca": 0})
            loja["diferenca"] += sinal * c["valor"]
    if por_loja:
        direcao = 1 if linha["diferenca"] > 0 else -1
        loja = max(por_loja.values(), key=lambda l: l["diferenca"] * direcao)
        if loja["diferenca"] * direcao >= abs(linha["diferenca"]) * FATIA_CONCENTRACAO:
            partes.append(f"A maior parte dessa variação está em “{loja['descricao']}” "
                          f"({_com_sinal(loja['diferenca'])}).")
    return " ".join(partes)


def _com_sinal(valor):
    return f"{'+' if valor > 0 else '-'}{brl(abs(valor))}"


def _motores(comparacao):
    despesas = comparacao["resumo"]["despesas"]["diferenca"]
    if comparativo.quase_zero(despesas):
        return "", None
    direcao = 1 if despesas > 0 else -1
    linhas = sorted(comparacao["categorias"], key=lambda l: -l["diferenca"] * direcao)
    a_favor = [l for l in linhas if l["diferenca"] * direcao >= comparativo.TOLERANCIA][:3]
    contra = [l for l in reversed(linhas) if l["diferenca"] * direcao <= -comparativo.TOLERANCIA]
    if not a_favor:
        return "", None
    lista = _lista([f"{l['categoria']} ({_com_sinal(l['diferenca'])})" for l in a_favor])
    texto = f"A {'alta' if direcao > 0 else 'queda'} nas despesas vem principalmente de {lista}."
    if contra:
        texto += (f" No sentido contrário, {contra[0]['categoria']} variou "
                  f"{_com_sinal(contra[0]['diferenca'])}.")
    return texto, a_favor[0]


def _compra_dominante(base, comparacao):
    segundo = comparacao["segundo"]
    do_mes = [c for c in base.habituais if c["mes"] == segundo]  # conta fixa não é novidade
    total = comparacao["resumo"]["despesas"]["b"]
    if not do_mes or total <= 0:
        return ""
    maior = max(do_mes, key=lambda c: c["valor"])
    if maior["valor"] < total * FATIA_COMPRA_UNICA:
        return ""
    return (f"Sozinha, “{maior['descricao']}” ({brl(maior['valor'])} em {_data_br(maior['dia'])}) "
            f"representa {_percentual(maior['valor'] / total * 100)} das despesas de {nome(segundo)}.")


def _dias_de_compra(compras, mes):
    """Parcela de compra antiga cai no mês, mas não é um dia em que você comprou algo."""
    return {c["dia"] for c in compras if c["mes"] == mes and c["dia"][:7] == mes}


def _ritmo(base, comparacao):
    a, b = comparacao["primeiro"], comparacao["segundo"]
    dias_a, dias_b = len(_dias_de_compra(base.compras, a)), len(_dias_de_compra(base.compras, b))
    if not dias_a or abs(dias_b - dias_a) / dias_a < VARIACAO_HABITO:
        return ""
    return f"Você teve gastos em {dias_a} dias em {nome(a)} e em {dias_b} dias em {nome(b)}."


def leitura(base, comparacao):
    """Texto corrido do período: o que mudou, de onde veio e o quanto veio de uma compra só."""
    a, b = nome(comparacao["primeiro"]), nome(comparacao["segundo"])
    resumo = comparacao["resumo"]
    parcial = comparacao["em_andamento"]
    inicio = f"Até o dia {parcial['dia']} de cada mês, de" if parcial else "De"
    textos = [f"{inicio} {a} para {b}, as despesas {_movimento(resumo['despesas'])}; as receitas "
              f"{_movimento(resumo['receitas'])}. O saldo foi de {brl(resumo['saldo']['a'])} "
              f"para {brl(resumo['saldo']['b'])}."]
    motor, principal = _motores(comparacao)
    if motor:
        textos.append(motor)
    if principal:
        textos.append(_explicar_variacao(base, comparacao, principal))
    textos += [_ritmo(base, comparacao), _compra_dominante(base, comparacao)]
    return [t for t in textos if t]


def _categoria_novo_habito(base, comparacao, linha):
    segundo = comparacao["segundo"]
    dias = _dias_de_compra(_compras_do_mes(base, linha["categoria"], segundo), segundo)
    if len(dias) < MINIMO_DIAS_HABITO_NOVO:
        return None
    return {"tipo": CONFIRMADO, "titulo": "Novo hábito de consumo",
            "texto": f"{linha['categoria']} apareceu em {len(dias)} dias de "
                     f"{nome(comparacao['segundo'])}, somando {brl(linha['b'])}, sem nenhum gasto "
                     f"em {nome(comparacao['primeiro'])}."}


def destaques(base, comparacao):
    """Os fatos da comparação, sem repetir o que é só ruído de centavos."""
    a = nome(comparacao["primeiro"])
    total = comparacao["resumo"]["despesas"]["b"]
    linhas = comparacao["categorias"]
    # Fato confirmado só precisa do piso absoluto: a régua proporcional é para inferências.
    relevantes = [l for l in linhas if abs(l["diferenca"]) >= MINIMO_REAIS]
    subiram = [l for l in relevantes if l["diferenca"] > 0]
    itens = []
    com_base = [l for l in subiram if l["percentual"] is not None]
    maior_pct = max(com_base, key=lambda l: l["percentual"], default=None)
    maior_abs = max(subiram, key=lambda l: l["diferenca"], default=None)
    if maior_pct:
        texto = (f"Seus gastos {_com(maior_pct['categoria'])} aumentaram "
                 f"{_percentual(maior_pct['percentual'])} em relação a {a}. Você gastou "
                 f"{brl(maior_pct['diferenca'])} a mais nessa categoria.")
        if maior_pct is maior_abs:
            texto += " Foi também o maior aumento absoluto do período."
        itens.append({"tipo": CONFIRMADO, "titulo": "Maior aumento", "texto": texto})
    if maior_abs and maior_abs is not maior_pct:
        itens.append({"tipo": CONFIRMADO, "titulo": "Maior aumento absoluto",
                      "texto": f"{maior_abs['categoria']} foi a categoria com maior aumento "
                               f"absoluto neste período: {_com_sinal(maior_abs['diferenca'])}."})
    cairam = [l for l in relevantes if l["diferenca"] < 0]
    maior_queda = min(cairam, key=lambda l: l["diferenca"], default=None)
    if maior_queda:
        itens.append({"tipo": CONFIRMADO, "titulo": "Maior redução",
                      "texto": f"Seus gastos {_com(maior_queda['categoria'])} diminuíram "
                               f"{_percentual(maior_queda['percentual'])}, representando uma "
                               f"redução de {brl(-maior_queda['diferenca'])}."})
    if not comparacao["em_andamento"] and total > 0:
        atencao = [l for l in subiram if l["b"] / total >= FATIA_ATENCAO and l is not maior_abs]
        for l in atencao[:2]:
            itens.append({"tipo": CONFIRMADO, "titulo": "Merece atenção",
                          "texto": f"{l['categoria']} subiu {_com_sinal(l['diferenca'])} e já "
                                   f"representa {_percentual(l['b'] / total * 100)} das despesas "
                                   f"de {nome(comparacao['segundo'])}."})
    for linha in subiram:
        if linha["percentual"] is None:
            habito = _categoria_novo_habito(base, comparacao, linha)
            if habito:
                itens.append(habito)
    parcial = comparacao["em_andamento"]
    if parcial:
        for item in itens:
            item["texto"] += f" Considerando até o dia {parcial['dia']} nos dois meses."
    return itens


def _descoberta(tipo, titulo, explicacao, valores, periodo, motivo):
    return {"tipo": tipo, "titulo": titulo, "explicacao": explicacao, "periodo": periodo,
            "motivo": motivo, "valores": [{"rotulo": r, "texto": t} for r, t in valores]}


def _extremos_recentes(base):
    """Categoria que mais cresceu e a que mais caiu, entre metades iguais dos meses recentes."""
    if len(base.fechados) < MINIMO_MESES_BASE:
        return []
    metade = min(MESES_RECENTES, len(base.fechados) // 2)
    recentes_m, antes_m = base.fechados[-metade:], base.fechados[-2 * metade:-metade]
    variacoes = []
    for categoria in base.gastos:
        serie_depois = _serie(base, categoria, recentes_m)
        serie_antes = _serie(base, categoria, antes_m)
        depois, antes = statistics.mean(serie_depois), statistics.mean(serie_antes)
        # Uma compra única sozinha em um dos lados pareceria mudança sem ser.
        lado = serie_depois if depois > antes else serie_antes
        if sum(v > 0 for v in lado) < 2:
            continue
        if abs(depois - antes) >= base.relevante and antes > 0:
            if abs(depois - antes) / antes >= VARIACAO_TENDENCIA:
                variacoes.append((depois - antes, categoria, antes, depois))
    if not variacoes:
        return []
    periodo = f"{_intervalo(antes_m)} contra {_intervalo(recentes_m)}"
    motivo = f"Maior diferença entre as médias mensais de dois períodos de {metade} meses."
    resultado = []
    maior = max(variacoes)
    if maior[0] > 0:
        resultado.append(_descoberta_extremo("Categoria com maior crescimento", "aumentou", maior,
                                             periodo, motivo))
    menor = min(variacoes)
    if menor[0] < 0:
        resultado.append(_descoberta_extremo("Categoria com maior redução", "diminuiu", menor,
                                             periodo, motivo))
    return resultado


def _descoberta_extremo(titulo, verbo, variacao, periodo, motivo):
    diferenca, categoria, antes, depois = variacao
    return _descoberta(CONFIRMADO, titulo,
                       f"A média mensal {_com(categoria)} {verbo} {brl(abs(diferenca))}.",
                       [("Antes", f"{brl(antes)} por mês"), ("Depois", f"{brl(depois)} por mês")],
                       periodo, motivo)


def _maior_despesa(base):
    if not base.compras:
        return None
    maior = max(base.compras, key=lambda c: c["valor"])
    meses = sorted(base.mensal)
    return _descoberta(CONFIRMADO, "Maior despesa individual",
                       f"“{maior['descricao']}”, em {maior['categoria']}.",
                       [("Valor", brl(maior["valor"])), ("Data", _data_br(maior["dia"]))],
                       _intervalo(meses),
                       f"Maior valor único entre {len(base.compras)} despesas registradas.")


def _categoria_frequente(base):
    dias = {c: len({x["dia"] for x in compras})
            for c, compras in _por_categoria(base.compras).items()}
    if not dias or max(dias.values()) < MINIMO_DIAS_FREQUENTE:
        return None
    categoria = max(dias, key=dias.get)
    return _descoberta(CONFIRMADO, "Categoria mais frequente",
                       f"{categoria} é a categoria que aparece em mais dias.",
                       [("Dias com gasto", str(dias[categoria]))], _intervalo(sorted(base.mensal)),
                       "Contagem de dias distintos com gasto em cada categoria.")


def _melhor_resultado(base):
    if len(base.fechados) < MINIMO_MESES_RESULTADO:
        return None
    mes = max(base.fechados, key=lambda m: base.mensal[m]["resultado"])
    dados = base.mensal[mes]
    return _descoberta(CONFIRMADO, "Melhor resultado mensal",
                       f"{nome(mes)} teve o maior saldo entre os meses fechados.",
                       [("Saldo", brl(dados["resultado"])), ("Receitas", brl(dados["entradas"])),
                        ("Despesas", brl(dados["saidas"]))],
                       _intervalo(base.fechados),
                       f"Comparação do saldo de {len(base.fechados)} meses fechados.")


def _compra_fora_do_padrao(base):
    """Compra muito maior que as demais da categoria, pela distância entre quartis."""
    melhor = None
    for categoria, compras in _por_categoria(base.habituais).items():
        if len(compras) < MINIMO_COMPRAS_CATEGORIA:
            continue
        valores = [c["valor"] for c in compras]
        q1, mediana, q3 = statistics.quantiles(valores, n=4)
        limite = max(q3 + 3 * (q3 - q1), mediana * FATOR_COMPRA_INCOMUM)
        maior = max(compras, key=lambda c: c["valor"])
        if maior["valor"] > limite and maior["valor"] - mediana >= base.relevante:
            razao = maior["valor"] / mediana
            if melhor is None or razao > melhor[0]:
                melhor = (razao, categoria, maior, mediana, len(compras))
    if melhor is None:
        return None
    razao, categoria, compra, mediana, total = melhor
    return _descoberta(PADRAO, "Despesa fora do padrão",
                       f"“{compra['descricao']}” ficou muito acima do normal para {categoria}.",
                       [("Valor", brl(compra["valor"])), ("Compra típica", brl(mediana)),
                        ("Data", _data_br(compra["dia"]))],
                       _intervalo(sorted({c["mes"] for c in base.habituais})),
                       f"Mais de {math.floor(razao)} vezes a compra típica, entre {total} "
                       "compras da categoria.")


def _mes_fora_do_padrao(base):
    achados = [fora_do_padrao(base, c, m) for c in base.gastos for m in base.fechados]
    achados = [a for a in achados if a and a["tipo"] == "acima"]
    if not achados:
        return None
    a = max(achados, key=lambda x: x["excesso"])
    return _descoberta(PADRAO, "Despesa fora do padrão",
                       f"{a['categoria']} em {nome(a['mes'])} ficou muito acima do habitual.",
                       [("No mês", brl(a["valor"])), ("Mês típico", brl(a["mediana"]))],
                       _intervalo(a["meses"] + [a["mes"]]),
                       f"Comparado com a mediana de {len(a['meses'])} meses fechados anteriores.")


def _descoberta_habito(habitos):
    if not habitos:
        return None
    h = habitos[0]
    return _descoberta(PADRAO, "Mudança de comportamento", h["texto"],
                       [("Recente", f"{brl(h['media'])} por mês"),
                        ("Antes", f"{brl(h['mediana'])} por mês")], h["periodo"], h["motivo"])


def _descoberta_tendencia(grupos):
    itens = grupos["alta"] + grupos["queda"]
    if not itens:
        return None
    item = max(itens, key=lambda i: i["peso"])
    return _descoberta(TENDENCIA, "Tendência de consumo", item["texto"],
                       [("Variação no período", brl(item["peso"]))],
                       f"Últimos {grupos['meses']} meses fechados", item["motivo"])


def descobertas(base, grupos, habitos):
    candidatas = [*_extremos_recentes(base), _maior_despesa(base), _categoria_frequente(base),
                  _melhor_resultado(base), _compra_fora_do_padrao(base) or _mes_fora_do_padrao(base),
                  _descoberta_habito(habitos), _descoberta_tendencia(grupos)]
    return [c for c in candidatas if c]


def _limitacoes(base, comparacao):
    fechados = len(base.fechados)
    avisos = []
    if fechados < MINIMO_MESES_TENDENCIA:
        avisos.append(f"Tendências precisam de ao menos {MINIMO_MESES_TENDENCIA} meses fechados; "
                      f"há {fechados}.")
    if fechados < MINIMO_MESES_PREVISAO:
        avisos.append(f"Previsões e comparação com o habitual precisam de ao menos "
                      f"{MINIMO_MESES_PREVISAO} meses fechados; há {fechados}.")
    if fechados < MINIMO_MESES_HABITO:
        avisos.append(f"Mudanças de hábito precisam de ao menos {MINIMO_MESES_HABITO} meses "
                      f"fechados; há {fechados}.")
    alvo = comparacao["em_andamento"]
    if alvo:
        avisos.append(f"{nome(alvo['mes'])} ainda está em andamento e fica fora das estatísticas "
                      "do histórico.")
    return [{"tipo": INSUFICIENTE, "texto": a} for a in avisos]


def _mesmos_dias(transacoes, comparacao, base):
    """Com mês em andamento, os fatos comparam o mesmo número de dias nos dois meses."""
    parcial = comparacao["em_andamento"]
    if not parcial:
        return comparacao, base
    outro, dia = parcial["outro"], parcial["dia"]
    depois = lambda mes, data: mes == outro and int(data[8:10]) > dia
    trecho = [t for t in transacoes if not depois(t["data"][:7], t["data"])]
    totais = comparativo.resumo_e_categorias(trecho, comparacao["primeiro"], comparacao["segundo"])
    return ({**comparacao, **totais},
            replace(base, compras=[c for c in base.compras if not depois(c["mes"], c["data"])],
                    habituais=[c for c in base.habituais if not depois(c["mes"], c["data"])]))


def analisar(transacoes, comparacao, hoje, ignoradas=()):
    base = montar_base(transacoes, hoje, ignoradas)
    habitos = mudancas_de_habito(base)
    grupos = tendencias(base, {h["categoria"] for h in habitos})
    meses = sorted(base.mensal)
    justa, base_justa = _mesmos_dias(transacoes, comparacao, base)
    return {
        "base": {"meses_fechados": len(base.fechados), "despesas": len(base.compras),
                 "periodo": _intervalo(meses) if meses else ""},
        "leitura": leitura(base_justa, justa),
        "destaques": destaques(base_justa, justa),
        "alertas": alertas(comparacao, base, grupos),
        "padroes": padroes(base, habitos),
        "tendencias": grupos,
        "previsoes": previsoes(transacoes, base),
        "descobertas": descobertas(base, grupos, habitos),
        "limitacoes": _limitacoes(base, comparacao),
    }
