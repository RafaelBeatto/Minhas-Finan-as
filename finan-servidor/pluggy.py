"""Busca contas, transações e faturas na Pluggy. Somente leitura: não movimenta dinheiro."""
from datetime import date, datetime, timedelta
import requests
import financeiro as fin
import historico

BASE_URL = "https://api.pluggy.ai"
CAMPOS_CONTA = ("id", "name", "number", "type", "balance", "creditData")
CAMPOS_INVESTIMENTO = ("id", "name", "type", "subtype", "balance", "status", "date")


def mensagem_erro(e):
    """A chave de acesso nunca entra aqui: só o status e a resposta da Pluggy."""
    resposta = getattr(e, "response", None)
    if resposta is None:
        return "Não foi possível falar com a Pluggy. Verifique a internet."
    try:
        return f"Pluggy: {resposta.status_code} — {resposta.json()}"
    except ValueError:
        return f"Pluggy: {resposta.status_code}"


def _todas_paginas(caminho, params, headers):
    encontrados, pagina, total = [], 1, 1
    while pagina <= total:
        response = requests.get(f"{BASE_URL}{caminho}", params={**params, "page": pagina},
                                headers=headers, timeout=30)
        response.raise_for_status()
        payload = response.json()
        encontrados += payload.get("results", [])
        total = payload.get("totalPages", 1)
        pagina += 1
    return encontrados


def _buscar_transacoes(conta_id, inicio, headers):
    response = requests.get(f"{BASE_URL}/v2/transactions", params={
        "accountId": conta_id,
        "dateFrom": inicio,
        "dateTo": date.today().isoformat(),
    }, headers=headers, timeout=30)
    while True:
        response.raise_for_status()
        payload = response.json()
        yield from payload.get("results", [])
        proxima = payload.get("next")
        if not proxima:
            return
        response = requests.get(f"{BASE_URL}/v2/transactions{proxima}", headers=headers, timeout=30)


def _buscar_categorias(headers):
    """Sem a lista as transações ainda aparecem, só com o nome original da Pluggy."""
    try:
        return fin.mapa_categorias(_todas_paginas("/categories", {}, headers))
    except requests.RequestException:
        return {}


def _buscar_faturas(accounts, headers):
    """None indica falha: o resto do app funciona e as faturas salvas continuam valendo."""
    try:
        faturas = []
        for conta in accounts:
            if conta.get("type") == "CREDIT":
                faturas += _todas_paginas("/bills", {"accountId": conta["id"]}, headers)
        return faturas
    except requests.RequestException:
        return None


def _buscar_investimentos(item_id, headers):
    """Caixinhas e aplicações. None indica falha (plano ou conector sem o produto)."""
    try:
        encontrados = _todas_paginas("/investments", {"itemId": item_id}, headers)
    except requests.RequestException:
        return None
    return [{c: i.get(c) for c in CAMPOS_INVESTIMENTO} for i in encontrados]


def _leitura_do_banco(item_id, headers):
    """Quando a Pluggy leu o banco de verdade; sem resposta, valem as datas já salvas."""
    try:
        response = requests.get(f"{BASE_URL}/items/{item_id}", headers=headers, timeout=30)
        response.raise_for_status()
        item = response.json()
    except requests.RequestException:
        return {}
    datas = {"banco_lido_em": item.get("lastUpdatedAt"), "proxima_leitura": item.get("nextAutoSyncAt")}
    return {chave: valor for chave, valor in datas.items() if valor}


def sincronizar(client_id, client_secret, item_id, arquivo):
    """Grava contas e transações no banco. Devolve um aviso se só as contas vieram."""
    auth = requests.post(f"{BASE_URL}/auth",
                         json={"clientId": client_id, "clientSecret": client_secret}, timeout=30)
    auth.raise_for_status()
    headers = {"X-API-KEY": auth.json()["apiKey"]}
    response = requests.get(f"{BASE_URL}/accounts", params={"itemId": item_id},
                            headers=headers, timeout=30)
    response.raise_for_status()
    payload = response.json()
    accounts = payload.get("results", payload if isinstance(payload, list) else [])
    contas = [{c: a.get(c) for c in CAMPOS_CONTA} for a in accounts]
    agora = datetime.now().isoformat(timespec="seconds")
    historico.salvar_instantaneo(arquivo, {"contas": contas, "atualizado_em": agora,
                                           **_leitura_do_banco(item_id, headers)})
    try:
        categorias = _buscar_categorias(headers)
        for conta in accounts:
            conhecida = historico.tem_dados(arquivo, conta["id"])
            dias = fin.DIAS_BUSCADOS if conhecida else fin.DIAS_PRIMEIRA_CARGA
            inicio = (date.today() - timedelta(days=dias)).isoformat()
            novas = [fin.normalizar_transacao(tx, conta, categorias)
                     for tx in _buscar_transacoes(conta["id"], inicio, headers)]
            historico.salvar(arquivo, conta["id"], inicio, novas)
        faturas = _buscar_faturas(accounts, headers)
        novos = {}
        if faturas is not None:
            novos["faturas"] = [fin.resumo_fatura(f) for f in faturas]
        investimentos = _buscar_investimentos(item_id, headers)
        if investimentos is None:
            novos["investimentos_status"] = "falhou"  # as salvas continuam valendo
        else:
            novos["investimentos"] = investimentos
            novos["investimentos_status"] = "ok" if investimentos else "vazio"
        if categorias:
            novos["categorias"] = sorted({c["nome"] for c in categorias.values()})
        historico.salvar_instantaneo(arquivo, novos)
    except requests.RequestException as e:
        return f"As contas carregaram, mas o extrato não. {mensagem_erro(e)}"
    return None if faturas is not None else "As faturas não vieram: mostrando as últimas salvas."
