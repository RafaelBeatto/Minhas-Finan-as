"""Regras do extrato: sinais, categorias e totais. Sem interface, para poder testar."""
import calendar
import json
import os
import re
import statistics
import unicodedata
from datetime import date, timedelta

SEM_CATEGORIA = "Sem categoria"
INTERNO = "Movimentação interna"
PERIODOS = ("Este mês", "Mês passado", "Últimos 30 dias", "Últimos 90 dias",
            "Últimos 12 meses", "Tudo")
DIAS_POR_PERIODO = {"Últimos 30 dias": 30, "Últimos 90 dias": 90, "Últimos 12 meses": 365}
DIAS_BUSCADOS = 120  # o resto do histórico já está no banco local
DIAS_PRIMEIRA_CARGA = 3650  # a Pluggy devolve o que tiver, mesmo pedindo mais
LIMIAR_ATENCAO = 0.8  # avisa a partir de 80% do limite
DIA_MINIMO_PREVISAO = 5  # antes disso o ritmo do mês ainda não diz nada
MINIMO_MESES_ASSINATURA = 3
VARIACAO_ASSINATURA = 0.2  # reajuste ou câmbio ainda conta como a mesma assinatura
DIAS_ASSINATURA_ATIVA = 45
MESES = ("jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez")

# Não são gasto nem renda: pagar a fatura ou guardar dinheiro só muda o dinheiro de lugar.
CATEGORIAS_INTERNAS = ("credit card payment", "same person transfer", "investments")
TEXTOS_INTERNOS = ("pagamento de fatura", "pagamento da fatura", "pagamento recebido",
                   "aplicacao rdb", "resgate rdb", "dinheiro guardado", "dinheiro resgatado")

# Usado só quando a Pluggy não manda categoria (o enriquecimento depende do plano).
PALAVRAS_CATEGORIA = {
    "Alimentação": ("ifood", "restaurante", "lanchonete", "padaria", "pizzaria", "burger"),
    "Mercado": ("mercado", "supermercado", "atacadao", "assai", "carrefour"),
    "Transporte": ("uber", "99app", "99 pop", "posto", "combustivel", "estacionamento"),
    "Assinaturas": ("netflix", "spotify", "prime video", "disney", "youtube", "icloud"),
    "Saúde": ("farmacia", "drogaria", "droga raia", "drogasil", "hospital", "clinica"),
    "Moradia": ("aluguel", "condominio", "energia", "enel", "sabesp", "internet"),
}


def normalizar_texto(texto):
    sem_acento = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in sem_acento if not unicodedata.combining(c)).lower()


def formatar_brl(valor):
    texto = f"R$ {abs(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"- {texto}" if valor < 0 else texto


def resumo_contas(accounts):
    """Saldo em conta e fatura ficam separados: a fatura é dívida, não dinheiro."""
    em_conta = sum(float(a.get("balance") or 0) for a in accounts if a.get("type") != "CREDIT")
    fatura = sum(float(a.get("balance") or 0) for a in accounts if a.get("type") == "CREDIT")
    return em_conta, fatura


def mapa_categorias(categorias):
    """Traduz cada id de categoria para o nome em português da categoria principal."""
    por_id = {c["id"]: c for c in categorias}
    mapa = {}
    for c in categorias:
        topo = c
        while topo.get("parentId") in por_id:
            topo = por_id[topo["parentId"]]
        mapa[c["id"]] = {
            "nome": topo.get("descriptionTranslated") or topo.get("description") or SEM_CATEGORIA,
            "original": (topo.get("description") or "").lower(),
        }
    return mapa


def valor_na_conta(tx, conta):
    """Valor do ponto de vista do seu bolso: negativo sai, positivo entra.

    No cartão a Pluggy manda a compra positiva (soma na dívida), então o sinal inverte.
    Na conta corrente quem diz a direção é o campo type.
    """
    bruto = tx.get("amountInAccountCurrency")
    if bruto is None:
        bruto = tx.get("amount") or 0
    bruto = float(bruto)
    if conta.get("type") == "CREDIT":
        return -bruto
    if tx.get("type") == "DEBIT":
        return -abs(bruto)
    if tx.get("type") == "CREDIT":
        return abs(bruto)
    return bruto


def categoria_por_palavra(descricao):
    texto = normalizar_texto(descricao)
    for categoria, palavras in PALAVRAS_CATEGORIA.items():
        if any(p in texto for p in palavras):
            return categoria
    return SEM_CATEGORIA


def normalizar_transacao(tx, conta, categorias):
    descricao = tx.get("description") or tx.get("descriptionRaw") or "Sem descrição"
    info = categorias.get(tx.get("categoryId"))
    original = (tx.get("category") or "").lower()
    texto = normalizar_texto(descricao)
    cartao = tx.get("creditCardMetadata") or {}
    interno = (original in CATEGORIAS_INTERNAS
               or (info is not None and info["original"] in CATEGORIAS_INTERNAS)
               or any(t in texto for t in TEXTOS_INTERNOS))
    if interno:
        categoria = INTERNO
    elif info:
        categoria = info["nome"]
    else:
        categoria = tx.get("category") or categoria_por_palavra(descricao)
    return {
        "id": tx.get("id"),
        "parcela": cartao.get("installmentNumber") or 0,
        "parcelas_total": cartao.get("totalInstallments") or 0,
        "data_compra": (cartao.get("purchaseDate") or "")[:10],
        "mes_fatura": _mes_valido(cartao.get("billForecastDate") or cartao.get("billPostDate")),
        "data": (tx.get("date") or "")[:10],
        "descricao": descricao,
        "chave": chave_regra(descricao),
        "conta": conta.get("name") or conta.get("number") or "Conta",
        "categoria": categoria,
        "categoria_original": categoria,
        "valor": valor_na_conta(tx, conta),
        "interno": interno,
        "interno_original": interno,
        "pendente": tx.get("status") == "PENDING",
    }


def _mes_valido(data):
    return data[:7] if re.match(r"\d{4}-\d{2}", data or "") else ""


def chave_regra(descricao):
    """Ignora números e pontuação para a mesma loja cair na mesma regra (ex.: parcela 3/12)."""
    texto = normalizar_texto(descricao)
    return " ".join(re.sub(r"[^a-z]+", " ", texto).split()) or texto


def regras_vazias():
    return {"transacoes": {}, "faixas": {}, "descricoes": {}}


def _ler_json(caminho, vazio):
    try:
        with open(caminho, encoding="utf-8") as arquivo:
            return {**vazio, **json.load(arquivo)}
    except FileNotFoundError:
        return vazio
    except (TypeError, ValueError):
        # Guarda o arquivo estragado em vez de sobrescrever o conteúdo na próxima gravação.
        os.replace(caminho, f"{caminho}.estragado")
        return vazio


def carregar_regras(caminho):
    return _ler_json(caminho, regras_vazias())


def carregar_orcamento(caminho):
    return _ler_json(caminho, {})


def gravar_json(dados, caminho):
    temporario = f"{caminho}.tmp"
    with open(temporario, "w", encoding="utf-8") as arquivo:
        json.dump(dados, arquivo, ensure_ascii=False, indent=2)
    os.replace(temporario, caminho)


def definir_regra(regras, transacao, categoria, todas):
    if todas:
        regras["descricoes"][transacao["chave"]] = categoria
        regras["faixas"].pop(transacao["chave"], None)
        regras["transacoes"].pop(transacao["id"], None)
    else:
        regras["transacoes"][transacao["id"]] = categoria


def remover_regra(regras, transacao):
    """Devolve a transação à categoria original, desfazendo as regras que valem para ela."""
    regras["transacoes"].pop(transacao["id"], None)
    regras["descricoes"].pop(transacao["chave"], None)
    regras["faixas"].pop(transacao["chave"], None)


def _categoria_da_faixa(t, regras):
    """Separa, na mesma descrição, a entrada grande (salário) das transferências pequenas."""
    faixa = regras["faixas"].get(t["chave"])
    if faixa and t["valor"] >= faixa["minimo"]:
        return faixa["categoria"]
    return None


def aplicar_regras(transacoes, regras):
    """A correção de uma transação vale mais que a faixa de valor e que a regra da descrição."""
    for t in transacoes:
        categoria = (regras["transacoes"].get(t["id"]) or _categoria_da_faixa(t, regras)
                     or regras["descricoes"].get(t["chave"]))
        if categoria:
            t["categoria"] = categoria
            t["interno"] = categoria == INTERNO
        else:
            t["categoria"] = t["categoria_original"]
            t["interno"] = t["interno_original"]


def intervalo(periodo, hoje):
    if periodo == "Este mês":
        return hoje.replace(day=1), hoje
    if periodo == "Mês passado":
        fim = hoje.replace(day=1) - timedelta(days=1)
        return fim.replace(day=1), fim
    if periodo == "Tudo":
        return date.min, hoje
    return hoje - timedelta(days=DIAS_POR_PERIODO[periodo] - 1), hoje


def filtrar(transacoes, periodo, conta=None, categoria=None, busca="", hoje=None, de=None, ate=None):
    """de e ate (AAAA-MM-DD) substituem o período quando informados."""
    inicio, fim = intervalo(periodo, hoje or date.today())
    de, ate = de or inicio.isoformat(), ate or fim.isoformat()
    termo = normalizar_texto(busca).strip()
    return sorted(
        (t for t in transacoes
         if de <= t["data"] <= ate
         and (conta is None or t["conta"] == conta)
         and (categoria is None or t["categoria"] == categoria)
         and termo in normalizar_texto(t["descricao"])),
        key=lambda t: t["data"], reverse=True)


SITUACOES = {
    "pendentes": lambda t: t["pendente"],
    "parceladas": lambda t: t["parcelas_total"] > 1,
    "corrigidas": lambda t: t["categoria"] != t["categoria_original"],
}
TIPOS = {
    "entradas": lambda t: not t["interno"] and t["valor"] > 0,
    "saidas": lambda t: not t["interno"] and t["valor"] < 0,
    "internas": lambda t: t["interno"],
}


def filtrar_detalhes(transacoes, tipo=None, situacao=None, minimo=None, maximo=None,
                     sem_internas=False):
    """Refina o extrato. Mínimo e máximo valem para o valor sem sinal."""
    return [t for t in transacoes
            if (tipo is None or TIPOS[tipo](t))
            and (situacao is None or SITUACOES[situacao](t))
            and (minimo is None or abs(t["valor"]) >= minimo)
            and (maximo is None or abs(t["valor"]) <= maximo)
            and not (sem_internas and t["interno"])]


def totais(transacoes):
    """Entradas, saídas e gastos por categoria, sem contar movimentação interna."""
    entradas = saidas = 0.0
    por_categoria = {}
    for t in transacoes:
        if t["interno"]:
            continue
        if t["valor"] >= 0:
            entradas += t["valor"]
        else:
            saidas += -t["valor"]
            por_categoria[t["categoria"]] = por_categoria.get(t["categoria"], 0) - t["valor"]
    ordenado = sorted(por_categoria.items(), key=lambda item: item[1], reverse=True)
    return entradas, saidas, ordenado


def resumo_cartao(accounts):
    """Junta os cartões; o limite usado inclui parcelas futuras, por isso difere da fatura."""
    cartoes = [a for a in accounts if a.get("type") == "CREDIT"]
    dados = [a.get("creditData") or {} for a in cartoes]
    vencimentos = [d["balanceDueDate"][:10] for d in dados if d.get("balanceDueDate")]
    mesmos = [d.get("minimumPayment") for d in dados if d.get("minimumPayment") is not None]
    limite = sum(float(d.get("creditLimit") or 0) for d in dados)
    disponivel = sum(float(d.get("availableCreditLimit") or 0) for d in dados)
    return {
        "fatura": sum(float(a.get("balance") or 0) for a in cartoes),
        "limite": limite,
        "disponivel": disponivel,
        "usado": limite - disponivel,
        "vencimento": min(vencimentos, default=None),
        "minimo": sum(float(m) for m in mesmos) if mesmos else None,
    }


def formatar_data(data):
    if not data:
        return "—"
    return date.fromisoformat(data[:10]).strftime("%d/%m/%Y")


def somar_meses(mes, quantidade):
    ano, numero = map(int, mes.split("-"))
    ano, resto = divmod(ano * 12 + numero - 1 + quantidade, 12)
    return f"{ano}-{resto + 1:02d}"


def parcelas_abertas(transacoes, hoje):
    """Cada compra parcelada que ainda tem parcelas por vir, calculada pela última conhecida.

    O banco manda as parcelas mês a mês e a Pluggy não liga as de uma mesma compra, então
    elas são agrupadas por descrição, número de parcelas, valor e data da compra.
    """
    ultimas = {}
    for t in transacoes:
        if t["parcelas_total"] <= 1 or t["valor"] >= 0:
            continue
        chave = (t["chave"], t["parcelas_total"], round(t["valor"], 2), t["data_compra"])
        if chave not in ultimas or t["parcela"] > ultimas[chave]["parcela"]:
            ultimas[chave] = t
    mes_atual = hoje.isoformat()[:7]
    abertas = []
    for t in ultimas.values():
        base = t["mes_fatura"] or t["data"][:7]
        meses = [somar_meses(base, n) for n in range(1, t["parcelas_total"] - t["parcela"] + 1)]
        meses = [m for m in meses if m >= mes_atual]
        if meses:
            abertas.append({"descricao": t["descricao"], "parcela": t["parcela"],
                            "total": t["parcelas_total"], "valor": -t["valor"], "meses": meses,
                            "restante": -t["valor"] * len(meses), "fim": meses[-1]})
    return sorted(abertas, key=lambda a: a["fim"])


def compromisso_por_mes(abertas):
    meses = {}
    for compra in abertas:
        for mes in compra["meses"]:
            meses[mes] = meses.get(mes, 0) + compra["valor"]
    return sorted(meses.items())


def resumo_fatura(fatura):
    return {
        "vencimento": fatura.get("dueDate"),
        "fechamento": fatura.get("billClosingDate"),
        "total": float(fatura.get("totalAmount") or 0),
        "minimo": fatura.get("minimumPaymentAmount"),
        "encargos": sum(float(c.get("amount") or 0) for c in fatura.get("financeCharges") or []),
    }


def carregar_ignoradas(caminho):
    return _ler_json(caminho, {"ignoradas": []})


def _proxima_cobranca(data):
    ano, mes = map(int, somar_meses(data[:7], 1).split("-"))
    dia = min(int(data[8:10]), calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia).isoformat()


def _meses_seguidos(meses):
    """Aceita pular um mês: a cobrança pode cair no dia 1º ou 31 e mudar de mês."""
    indices = [int(m[:4]) * 12 + int(m[5:7]) for m in meses]
    return all(b - a <= 2 for a, b in zip(indices, indices[1:]))


def _valores_parecidos(valores):
    mediana = statistics.median(valores)
    parecidos = sum(abs(v - mediana) <= mediana * VARIACAO_ASSINATURA for v in valores)
    return parecidos >= len(valores) * 0.8


def detectar_assinaturas(transacoes, hoje, ignoradas=()):
    """Mesma descrição, uma vez por mês, valor parecido, em pelo menos 3 meses.

    Quem compra várias vezes no mês (mercado, delivery) e parcelas ficam de fora.
    Cobrança anual não aparece, porque não se repete dentro do histórico.
    """
    grupos = {}
    for t in transacoes:
        if not t["interno"] and t["valor"] < 0 and t["parcelas_total"] <= 1:
            grupos.setdefault(t["chave"], []).append(t)
    assinaturas = []
    for chave, cobrancas in grupos.items():
        cobrancas = sorted(cobrancas, key=lambda t: t["data"])
        meses = sorted({t["data"][:7] for t in cobrancas})
        valores = [-t["valor"] for t in cobrancas]
        if (chave in ignoradas or len(meses) < MINIMO_MESES_ASSINATURA
                or len(cobrancas) > len(meses) * 1.25
                or not _meses_seguidos(meses) or not _valores_parecidos(valores)):
            continue
        ultima = cobrancas[-1]
        dias_parada = (hoje - date.fromisoformat(ultima["data"])).days
        aumento = valores[-1] - valores[-2]
        assinaturas.append({
            "chave": chave, "descricao": ultima["descricao"], "categoria": ultima["categoria"],
            "conta": ultima["conta"], "valor": valores[-1], "meses": len(meses),
            "ultima": ultima["data"], "proxima": _proxima_cobranca(ultima["data"]),
            "ativa": dias_parada <= DIAS_ASSINATURA_ATIVA,
            "aumento": aumento if aumento > valores[-2] * 0.01 else 0,
        })
    return sorted(assinaturas, key=lambda a: (not a["ativa"], -a["valor"]))


def custo_assinaturas(assinaturas):
    return sum(a["valor"] for a in assinaturas if a["ativa"])


def ler_valor(texto, aceita_zero=False):
    """Lê valor digitado em reais: 800, 800,50, 1.234,50 ou R$ 1.234. Vazio devolve None."""
    limpo = (texto or "").replace("R$", "").replace(" ", "")
    if not limpo:
        return None
    if "," in limpo:
        limpo = limpo.replace(".", "").replace(",", ".")
    elif re.fullmatch(r"\d{1,3}(\.\d{3})+", limpo):
        limpo = limpo.replace(".", "")
    valor = float(limpo)
    if not (0 <= valor if aceita_zero else 0 < valor) or valor == float("inf"):
        raise ValueError(texto)
    return valor


def media_gastos(transacoes, mes, quantidade=3):
    """Média por categoria nos meses fechados anteriores que têm movimento."""
    meses = _por_mes(transacoes)
    anteriores = [somar_meses(mes, -n) for n in range(1, quantidade + 1)]
    com_dados = [m for m in anteriores if m in meses]
    somas = {}
    for m in com_dados:
        for categoria, valor in totais(meses[m])[2]:
            somas[categoria] = somas.get(categoria, 0) + valor
    return {c: v / len(com_dados) for c, v in somas.items()}


def estado_orcamento(gasto, limite):
    if limite is None:
        return "sem limite"
    if gasto >= limite:
        return "estourou"
    return "atencao" if gasto >= limite * LIMIAR_ATENCAO else "ok"


def situacao_orcamento(transacoes, orcamento, hoje):
    """Uma linha por categoria; as mais perto de estourar vêm primeiro."""
    mes = hoje.isoformat()[:7]
    gastos = dict(totais(_por_mes(transacoes).get(mes, []))[2])
    medias = media_gastos(transacoes, mes)
    linhas = []
    for categoria in orcamento.keys() | gastos.keys() | medias.keys():
        limite = orcamento.get(categoria)
        gasto = gastos.get(categoria, 0)
        linhas.append({"categoria": categoria, "limite": limite, "gasto": gasto,
                       "restante": None if limite is None else limite - gasto,
                       "uso": None if limite is None else gasto / limite,
                       "media": medias.get(categoria, 0),
                       "estado": estado_orcamento(gasto, limite)})
    return sorted(linhas, key=lambda l: (l["limite"] is None, -(l["uso"] or 0),
                                         -l["gasto"], -l["media"], l["categoria"]))


def texto_alerta(linhas):
    partes = [f'{l["categoria"]} estourou' if l["estado"] == "estourou"
              else f'{l["categoria"]} em {l["uso"]:.0%}'
              for l in linhas if l["estado"] in ("estourou", "atencao")]
    return f'Orçamento do mês: {", ".join(partes)}' if partes else ""


def mes_anterior(mes):
    ano, numero = map(int, mes.split("-"))
    return f"{ano - 1}-12" if numero == 1 else f"{ano}-{numero - 1:02d}"


def nome_mes(mes):
    ano, numero = mes.split("-")
    return f"{MESES[int(numero) - 1]}/{ano}"


def _por_mes(transacoes):
    meses = {}
    for t in transacoes:
        meses.setdefault(t["data"][:7], []).append(t)
    return meses


def resumo_mensal(transacoes):
    """Um item por mês, do mais novo ao mais antigo; o mês mais antigo não tem comparação."""
    meses = _por_mes(transacoes)
    primeiro = min(meses, default=None)
    resumo = []
    for mes in sorted(meses, reverse=True):
        entradas, saidas, _ = totais(meses[mes])
        variacao = None
        if mes != primeiro:
            variacao = saidas - totais(meses.get(mes_anterior(mes), []))[1]
        resumo.append({"mes": mes, "entradas": entradas, "saidas": saidas,
                       "resultado": entradas - saidas, "variacao": variacao})
    return resumo


def gastos_por_mes(transacoes):
    """Meses em ordem e, para cada categoria, o gasto mês a mês; maiores totais primeiro."""
    por_mes = _por_mes(transacoes)
    categorias = {}
    for mes in por_mes:
        for categoria, valor in totais(por_mes[mes])[2]:
            categorias.setdefault(categoria, {})[mes] = valor
    meses = sorted({m for valores in categorias.values() for m in valores})
    return meses, sorted(categorias.items(), key=lambda item: sum(item[1].values()), reverse=True)


def comparar_categorias(transacoes, mes):
    """Gastos do mês contra o mês anterior, com as maiores altas primeiro."""
    meses = _por_mes(transacoes)
    atual = dict(totais(meses.get(mes, []))[2])
    anterior = dict(totais(meses.get(mes_anterior(mes), []))[2])
    linhas = [(c, atual.get(c, 0), anterior.get(c, 0), atual.get(c, 0) - anterior.get(c, 0))
              for c in atual.keys() | anterior.keys()]
    return sorted(linhas, key=lambda linha: linha[3], reverse=True)


def previsao_mes(transacoes, hoje):
    """Gasto do mês, projeção pelo ritmo atual e a média dos 3 meses anteriores."""
    mes = hoje.isoformat()[:7]
    gasto = totais(_por_mes(transacoes).get(mes, []))[1]
    dias = calendar.monthrange(hoje.year, hoje.month)[1]
    projecao = gasto / hoje.day * dias if hoje.day >= DIA_MINIMO_PREVISAO else None
    return {"gasto": gasto, "projecao": projecao,
            "media": sum(media_gastos(transacoes, mes).values())}


def compromissos_proximo_mes(abertas, assinaturas, hoje):
    """O que já está contratado para o mês que vem: parcelas e assinaturas ativas."""
    mes = somar_meses(hoje.isoformat()[:7], 1)
    parcelas = sum(a["valor"] for a in abertas if mes in a["meses"])
    recorrentes = custo_assinaturas(assinaturas)
    return {"mes": mes, "parcelas": parcelas, "assinaturas": recorrentes,
            "total": parcelas + recorrentes}
