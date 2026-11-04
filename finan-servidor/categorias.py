"""Gestão de categorias: visão por período, criação, renomeação e regras salvas.

Nada aqui toca nas transações. Renomear grava um de-para em regras["renomeadas"], aplicado
na leitura por financeiro.aplicar_regras: vale para lançamentos futuros e pode ser desfeito.
"""
import financeiro as fin

TAMANHO_MAXIMO = 40
PRINCIPAIS = 5
RESERVADAS = (fin.INTERNO, fin.SEM_CATEGORIA)
TIPOS_REGRA = {"transacao": "transacoes", "descricao": "descricoes", "faixa": "faixas"}


def validar_nome(nome):
    """Devolve o nome limpo. Lança ValueError com a mensagem para o usuário."""
    limpo = " ".join(str(nome or "").split())
    if not limpo or len(limpo) > TAMANHO_MAXIMO:
        raise ValueError(f"Use um nome de 1 a {TAMANHO_MAXIMO} caracteres.")
    if limpo in RESERVADAS:
        raise ValueError(f"“{limpo}” é uma categoria do sistema.")
    return limpo


def _valores_de_regras(regras):
    return ({*regras["transacoes"].values(), *regras["descricoes"].values()}
            | {f["categoria"] for f in regras["faixas"].values()})


def em_uso(nome, transacoes, regras):
    return nome in _valores_de_regras(regras) or any(t["categoria"] == nome for t in transacoes)


def nomes_ativos(transacoes, criadas):
    """Categorias que o usuário administra: a interna tem regra própria e fica de fora."""
    return {t["categoria"] for t in transacoes if not t["interno"]} | set(criadas)


def _principais(lancamentos):
    grupos = {}
    for t in lancamentos:
        grupo = grupos.setdefault(t["chave"], {"descricao": t["descricao"], "quantidade": 0,
                                               "total": 0})
        grupo["quantidade"] += 1
        grupo["total"] += abs(t["valor"])
    return sorted(grupos.values(), key=lambda g: -g["total"])[:PRINCIPAIS]


def _linhas(transacoes, no_periodo, orcamento, criadas, regras):
    originais = {t["categoria_original"] for t in transacoes}
    _, total_gastos, _ = fin.totais(no_periodo)
    grupos = {}
    for t in no_periodo:
        if not t["interno"]:
            grupos.setdefault(t["categoria"], []).append(t)
    linhas = []
    for nome in nomes_ativos(transacoes, criadas):
        lancamentos = grupos.get(nome, [])
        entradas, gastos, _ = fin.totais(lancamentos)
        linhas.append({
            "categoria": nome, "gastos": gastos, "entradas": entradas,
            "lancamentos": len(lancamentos),
            "fatia": gastos / total_gastos if total_gastos else 0,
            "limite": orcamento.get(nome),
            "personalizada": nome in criadas or nome not in originais,
            "em_uso": em_uso(nome, transacoes, regras),
            "principais": _principais(lancamentos),
        })
    return sorted(linhas, key=lambda l: (-l["gastos"], -l["entradas"], l["categoria"]))


def _regras_salvas(transacoes, regras):
    por_id = {t["id"]: t for t in transacoes}
    exemplos, contagem = {}, {}
    for t in transacoes:
        exemplos[t["chave"]] = t["descricao"]
        contagem[t["chave"]] = contagem.get(t["chave"], 0) + 1
    final = lambda categoria: regras["renomeadas"].get(categoria, categoria)
    lista = []
    for chave, categoria in regras["descricoes"].items():
        lista.append({"tipo": "descricao", "chave": chave, "categoria": final(categoria),
                      "descricao": exemplos.get(chave, chave),
                      "lancamentos": contagem.get(chave, 0), "minimo": None})
    for chave, faixa in regras["faixas"].items():
        lista.append({"tipo": "faixa", "chave": chave, "categoria": final(faixa["categoria"]),
                      "descricao": exemplos.get(chave, chave),
                      "lancamentos": contagem.get(chave, 0), "minimo": faixa["minimo"]})
    for identificador, categoria in regras["transacoes"].items():
        t = por_id.get(identificador)
        lista.append({"tipo": "transacao", "chave": identificador, "categoria": final(categoria),
                      "descricao": t["descricao"] if t else "Transação não encontrada",
                      "lancamentos": 1 if t else 0, "minimo": None})
    return sorted(lista, key=lambda r: (r["categoria"], r["descricao"]))


def visao(transacoes, regras, orcamento, criadas, periodo, hoje):
    no_periodo = fin.filtrar(transacoes, periodo, hoje=hoje)
    return {
        "periodo": periodo,
        "total_gastos": fin.totais(no_periodo)[1],
        "linhas": _linhas(transacoes, no_periodo, orcamento, criadas, regras),
        "regras": _regras_salvas(transacoes, regras),
        "renomeadas": [{"origem": o, "destino": d} for o, d in sorted(regras["renomeadas"].items())],
    }


def renomear(transacoes, regras, orcamento, criadas, origem, destino):
    """Renomeia, ou junta quando o destino já existe. O limite da origem passa ao destino.

    Se o destino já tem limite, ele fica: somar os dois mudaria o orçamento sem você pedir.
    """
    destino = validar_nome(destino)
    if origem not in nomes_ativos(transacoes, criadas) or origem == fin.SEM_CATEGORIA:
        raise ValueError("Escolha uma categoria existente.")
    if origem == destino:
        raise ValueError("Digite um nome diferente do atual.")
    if em_uso(origem, transacoes, regras):
        renomeadas = regras["renomeadas"]
        renomeadas[origem] = destino
        for chave, valor in list(renomeadas.items()):
            if valor == origem:
                renomeadas[chave] = destino
            if renomeadas[chave] == chave:
                del renomeadas[chave]
    if origem in orcamento:
        orcamento.setdefault(destino, orcamento[origem])
        del orcamento[origem]
    if origem in criadas:
        criadas.remove(origem)
        if destino not in criadas:
            criadas.append(destino)


def excluir(transacoes, regras, orcamento, criadas, nome):
    """Só categoria criada e sem uso: qualquer outra sumiria levando lançamentos junto."""
    if nome not in criadas:
        raise ValueError("Só dá para excluir categoria criada por você.")
    if em_uso(nome, transacoes, regras):
        raise ValueError("Esta categoria tem lançamentos ou regras. Junte-a com outra.")
    criadas.remove(nome)
    orcamento.pop(nome, None)


def remover_regra_salva(regras, tipo, chave):
    if tipo not in TIPOS_REGRA or chave not in regras[TIPOS_REGRA[tipo]]:
        raise ValueError("Regra não encontrada.")
    del regras[TIPOS_REGRA[tipo]][chave]
