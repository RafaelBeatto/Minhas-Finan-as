import json
import unittest
from datetime import date, timedelta
import comparativo as comp
import financeiro as fin
import inteligencia as ia

HOJE = date(2026, 10, 15)
MESES = ["2026-01", "2026-02", "2026-03", "2026-04", "2026-05", "2026-06", "2026-07", "2026-08",
         "2026-09"]
contador = iter(range(100000))


def tx(data, valor, categoria="Lazer", descricao=None, parcelas=0, interno=False):
    descricao = descricao or f"Loja {categoria}"
    return {"id": str(next(contador)), "conta": "Conta", "data": data, "descricao": descricao,
            "chave": fin.chave_regra(descricao), "categoria_original": categoria,
            "categoria": categoria, "valor": valor, "interno": interno, "interno_original": interno,
            "pendente": False, "parcela": 1 if parcelas else 0, "parcelas_total": parcelas,
            "data_compra": "", "mes_fatura": ""}


def mensais(valores, categoria="Lazer", meses=MESES, dia="15", base=True):
    """Um gasto por mês; o aluguel fixo garante que todos os meses existam."""
    linhas = [tx(f"{m}-{dia}", -v, categoria) for m, v in zip(meses, valores) if v]
    if base:
        linhas += [tx(f"{m}-02", -500, "Moradia", f"Aluguel {m}") for m in meses]
    return linhas


def analisar(transacoes, a="2026-08", b="2026-09", hoje=HOJE):
    return ia.analisar(transacoes, comp.comparar(transacoes, a, b, hoje), hoje)


class Tendencias(unittest.TestCase):
    def test_alta_com_tres_meses(self):
        self.assertEqual(ia.classificar_serie([100, 150, 200], 10), "alta")

    def test_dois_meses_nao_bastam(self):
        self.assertIsNone(ia.classificar_serie([100, 200], 10))

    def test_vai_e_volta_nao_e_tendencia(self):
        self.assertIsNone(ia.classificar_serie([100, 300, 100, 300], 10))

    def test_estavel(self):
        self.assertEqual(ia.classificar_serie([100, 102, 99, 101], 10), "estavel")

    def test_pico_isolado_nao_vira_tendencia(self):
        self.assertIsNone(ia.classificar_serie([100, 100, 900, 100, 100, 100], 10))

    def test_queda_ate_zero(self):
        self.assertEqual(ia.classificar_serie([100, 50, 0], 10), "queda")

    def test_identifica_categoria_em_alta(self):
        grupos = analisar(mensais([0, 0, 0, 50, 80, 120, 150, 190, 230]))["tendencias"]
        self.assertEqual(grupos["alta"][0]["categoria"], "Lazer")
        self.assertEqual(grupos["alta"][0]["tipo"], ia.TENDENCIA)
        self.assertIn("altas seguidas", grupos["alta"][0]["texto"])

    def test_sem_historico_nao_afirma_tendencia(self):
        t = mensais([50, 100], meses=["2026-08", "2026-09"])
        r = analisar(t)
        self.assertEqual(r["tendencias"]["alta"], [])
        self.assertTrue(any("Tendências" in l["texto"] for l in r["limitacoes"]))

    def test_mes_em_andamento_fica_fora(self):
        base = ia.montar_base(mensais([10, 20, 30], meses=["2026-08", "2026-09", "2026-10"]), HOJE)
        self.assertEqual(base.fechados, ["2026-08", "2026-09"])

    def test_primeiro_mes_incompleto_fica_fora(self):
        t = [tx("2026-07-25", -5), tx("2026-08-05", -5), tx("2026-09-05", -5)]
        self.assertEqual(ia.montar_base(t, HOJE).fechados, ["2026-08", "2026-09"])


class MesEmAndamento(unittest.TestCase):
    def setUp(self):
        # Até o dia 15, outubro gastou mais que setembro; no mês inteiro, setembro foi maior.
        self.t = mensais([100] * 9, "Lazer", dia="10", base=False) + [
            tx("2026-09-25", -900), tx("2026-10-10", -300)]
        self.r = analisar(self.t, "2026-09", "2026-10")

    def test_leitura_compara_os_mesmos_dias(self):
        self.assertIn("Até o dia 15 de cada mês", self.r["leitura"][0])
        self.assertIn("subiram R$ 200,00", self.r["leitura"][0])

    def test_destaque_nao_chama_mes_incompleto_de_reducao(self):
        textos = " ".join(i["texto"] for i in self.r["destaques"])
        self.assertIn("aumentaram 200%", textos)
        self.assertIn("até o dia 15", textos)
        self.assertNotIn("diminuíram", textos)

    def test_outro_mes_sem_nada_nos_primeiros_dias(self):
        t = [tx("2026-09-25", -900), tx("2026-10-10", -30)]
        self.assertIn("Até o dia 15", analisar(t, "2026-09", "2026-10")["leitura"][0])

    def test_meses_fechados_seguem_inteiros(self):
        self.assertTrue(analisar(self.t)["leitura"][0].startswith("De ago/2026"))


class CorrecoesDeSerie(unittest.TestCase):
    def test_mes_sem_transacao_conta_a_distancia_real(self):
        _, inclinacao = ia.direcao_estatistica([100, 200, 300], ia._posicoes(
            ["2026-01", "2026-03", "2026-05"]))
        self.assertEqual(inclinacao, 50)

    def test_previsao_de_tendencia_vai_ate_o_mes_pedido(self):
        valor, _, _ = ia._estimar([100, 120, 140, 160], 10, [1, 2, 3, 4], 6)
        self.assertEqual(valor, 200)

    def test_receita_em_queda_nao_e_favoravel(self):
        t = [tx(f"{m}-05", v, "Salário") for m, v in
             zip(MESES[-4:], [4000, 3000, 2000, 1000])] + [
             tx(f"{m}-06", -50) for m in MESES[-4:]]
        item = analisar(t)["tendencias"]["geral"][0]
        self.assertEqual((item["titulo"], item["favoravel"]), ("Suas receitas", False))

    def test_despesa_em_queda_e_favoravel(self):
        grupos = analisar(mensais([0, 0, 0, 300, 250, 200, 150, 100, 50]))["tendencias"]
        self.assertTrue(grupos["queda"][0]["favoravel"])

    def test_parcela_antiga_nao_conta_como_dia_de_compra(self):
        t = [tx("2026-08-05", -100, "Outra"), tx("2026-09-05", -100, "Outra")]
        for dia in ("10", "11", "12", "13"):
            t.append({**tx(f"2026-09-{dia}", -50, "Móveis", parcelas=6),
                      "data_compra": f"2026-01-{dia}"})
        titulos = [i["titulo"] for i in analisar(t)["destaques"]]
        self.assertNotIn("Novo hábito de consumo", titulos)

    def test_sem_gasto_no_mes_nao_projeta_zero(self):
        t = mensais([100] * 9) + [tx("2026-10-02", 500, "Salário")]
        previsoes = analisar(t, "2026-09", "2026-10")["previsoes"]
        self.assertFalse(any(p["titulo"].startswith("Fechamento") for p in previsoes))

    def test_ordem_invertida_nao_inventa_queda_de_saldo(self):
        t = mensais([100] * 9) + [tx("2026-03-10", 3000, "Salário")]
        alertas = analisar(t, "2026-03", "2026-01")["alertas"]
        self.assertFalse(any(a["titulo"] == "Saldo mensal em queda" for a in alertas))
        alertas = analisar(t, "2026-01", "2026-03")["alertas"]
        self.assertFalse(any(a["titulo"] == "Saldo mensal em queda" for a in alertas))

    def test_ordem_invertida_ainda_ve_a_queda_real(self):
        t = mensais([100] * 9) + [tx("2026-01-10", 3000, "Salário")]
        alertas = analisar(t, "2026-03", "2026-01")["alertas"]
        self.assertTrue(any(a["titulo"] == "Saldo mensal em queda" for a in alertas))


class Previsoes(unittest.TestCase):
    def test_nao_preve_sem_historico(self):
        t = mensais([100, 100, 100], meses=["2026-07", "2026-08", "2026-09"])
        self.assertEqual([p for p in analisar(t)["previsoes"] if "2026-11" in p["titulo"]
                          or "nov" in p["titulo"]], [])

    def test_preve_com_historico_e_declara_estimativa(self):
        previsoes = analisar(mensais([300] * 9))["previsoes"]
        lazer = next(p for p in previsoes if p["titulo"].startswith("Lazer"))
        self.assertEqual(lazer["tipo"], ia.ESTIMATIVA)
        self.assertIn("aproximadamente R$ 300,00", lazer["texto"])
        self.assertIn("meses fechados", lazer["motivo"])

    def test_gasto_irregular_nao_gera_previsao(self):
        previsoes = analisar(mensais([900, 0, 0, 500, 0, 0, 800, 0, 10]))["previsoes"]
        self.assertFalse(any(p["titulo"].startswith("Lazer") for p in previsoes))

    def test_tendencia_firme_prolonga_a_reta(self):
        valor, _, metodo = ia._estimar([100, 120, 140, 160], 10)
        self.assertEqual((valor, metodo), (180, "tendência dos meses recentes"))

    def test_projecao_do_mes_considera_dias_transcorridos(self):
        t = mensais([100] * 9) + [tx("2026-10-05", -150)]
        previsao = next(p for p in analisar(t, "2026-09", "2026-10")["previsoes"]
                        if p["titulo"].startswith("Fechamento"))
        self.assertIn("15 de 31 dias", previsao["motivo"])

    def test_sem_projecao_nos_primeiros_dias(self):
        t = mensais([100] * 9) + [tx("2026-10-02", -150)]
        previsoes = analisar(t, "2026-09", "2026-10", date(2026, 10, 3))["previsoes"]
        self.assertFalse(any(p["titulo"].startswith("Fechamento") for p in previsoes))


def sabados_e_quartas(categoria, sabados, quartas):
    """Datas reais: 2026-01-03 é sábado e 2026-01-07 é quarta."""
    datas = [date(2026, 1, 3) + timedelta(weeks=7 * n // 2) for n in range(sabados)]
    datas += [date(2026, 1, 7) + timedelta(weeks=7 * n // 2) for n in range(quartas)]
    return [tx(d.isoformat(), -20, categoria) for d in datas]


class Padroes(unittest.TestCase):
    def padroes(self, transacoes):
        return analisar(transacoes + mensais([], "X"))["padroes"]

    def test_final_de_semana_usa_a_data_real(self):
        padroes = self.padroes(sabados_e_quartas("Bebidas", 9, 1))
        texto = next(p for p in padroes if "finais de semana" in p["texto"])
        self.assertIn("com Bebidas", texto["texto"])
        self.assertEqual(texto["tipo"], ia.PADRAO)
        self.assertIn("9 de 10", texto["motivo"])

    def test_distribuicao_normal_nao_vira_padrao(self):
        padroes = self.padroes(sabados_e_quartas("Bebidas", 3, 7))
        self.assertFalse(any("finais de semana" in p["texto"] for p in padroes))

    def test_poucos_dias_nao_viram_padrao(self):
        padroes = self.padroes(sabados_e_quartas("Bebidas", 4, 0))
        self.assertFalse(any("finais de semana" in p["texto"] for p in padroes))

    def test_parcela_nao_conta_como_comportamento(self):
        t = [tx(d["data"], d["valor"], d["categoria"], parcelas=6)
             for d in sabados_e_quartas("Bebidas", 9, 1)]
        self.assertFalse(any("finais de semana" in p["texto"] for p in self.padroes(t)))

    def test_inicio_do_mes(self):
        t = [tx(f"{m}-0{d}", -20, "Lazer", f"Show {m}{d}") for m in MESES for d in (3, 4)]
        padroes = self.padroes(t)
        self.assertTrue(any("início de cada mês" in p["texto"] for p in padroes))

    def test_assinatura_nao_vira_habito_de_inicio_do_mes(self):
        t = [tx(f"{m}-03", -20, "Lazer", "Streaming") for m in MESES]
        self.assertFalse(any("início" in p["texto"] for p in self.padroes(t)))

    def test_mudanca_de_habito_com_economia(self):
        padroes = analisar(mensais([100, 110, 90, 105, 100, 95, 40, 45, 40], "Transporte"))["padroes"]
        economia = next(p for p in padroes if p["titulo"] == "Economia")
        self.assertIn("Transporte", economia["texto"])
        self.assertIn("diminuíram", economia["texto"])

    def test_degrau_e_habito_e_nao_tendencia(self):
        r = analisar(mensais([100, 110, 90, 105, 100, 95, 40, 45, 40], "Transporte"))
        self.assertEqual(r["tendencias"]["queda"], [])

    def test_gasto_gradual_e_tendencia_e_nao_habito(self):
        r = analisar(mensais([50, 50, 50, 50, 80, 120, 160, 200, 240]))
        self.assertEqual(r["tendencias"]["alta"][0]["categoria"], "Lazer")
        self.assertFalse(any(p["titulo"] == "Mudança de hábito" for p in r["padroes"]))


class Alertas(unittest.TestCase):
    def test_gasto_muito_acima_do_habitual(self):
        alertas = analisar(mensais([100, 105, 95, 100, 102, 98, 100, 100, 600]))["alertas"]
        self.assertTrue(any(a["titulo"] == "Lazer acima do habitual" for a in alertas))

    def test_variacao_normal_nao_alerta(self):
        alertas = analisar(mensais([100, 130, 70, 110, 90, 120, 80, 100, 125]))["alertas"]
        self.assertEqual(alertas, [])

    def test_categoria_que_nao_costuma_ter_gastos(self):
        alertas = analisar(mensais([0, 0, 0, 0, 0, 0, 0, 0, 200], "Viagem"))["alertas"]
        self.assertTrue(any("costuma não ter gastos" in a["titulo"] for a in alertas))

    def test_saldo_em_queda(self):
        t = mensais([100, 100, 100, 100, 100, 100, 100, 100, 100]) + [
            tx("2026-08-10", 2000, "Salário"), tx("2026-09-10", 700, "Salário")]
        alerta = next(a for a in analisar(t)["alertas"] if a["titulo"] == "Saldo mensal em queda")
        self.assertIn("R$ 1.300,00", alerta["motivo"])

    def test_nao_alerta_saldo_com_mes_em_andamento(self):
        t = mensais([100] * 9) + [tx("2026-09-10", 3000, "Salário"), tx("2026-10-05", -100)]
        alertas = analisar(t, "2026-09", "2026-10")["alertas"]
        self.assertFalse(any(a["titulo"] == "Saldo mensal em queda" for a in alertas))

    def test_limita_quantidade(self):
        t = []
        for n in range(10):
            t += mensais([100, 100, 100, 100, 100, 100, 100, 100, 900], f"C{n}", base=False)
        self.assertEqual(len(analisar(t)["alertas"]), ia.MAXIMO_ALERTAS)

    def test_todo_alerta_tem_justificativa(self):
        for alerta in analisar(mensais([100] * 8 + [900]))["alertas"]:
            self.assertTrue(alerta["motivo"])


class Leitura(unittest.TestCase):
    def setUp(self):
        self.t = (mensais([100, 100, 100, 100, 100, 100, 100, 100, 100], "Transporte")
                  + mensais([15, 15, 15, 15, 15, 15, 15, 15, 30], "Bebidas", base=False)
                  + mensais([200] * 8 + [250], "Alimentação", base=False))
        self.r = analisar(self.t)

    def test_explica_os_totais(self):
        self.assertIn("De ago/2026 para set/2026", self.r["leitura"][0])

    def test_aponta_de_onde_veio_a_alta(self):
        self.assertIn("Alimentação (+R$ 50,00)", self.r["leitura"][1])

    def test_frases_com_valores_certos(self):
        textos = " ".join(i["texto"] for i in self.r["destaques"])
        self.assertIn("Seus gastos com Bebidas aumentaram 100%", textos)
        self.assertIn("R$ 15,00 a mais", textos)
        self.assertIn("Alimentação foi a categoria com maior aumento absoluto", textos)

    def test_decompoe_quantidade_e_valor_medio(self):
        t = [tx("2026-08-05", -10), tx("2026-09-05", -10), tx("2026-09-06", -10), tx("2026-09-07", -10)]
        r = analisar(t)
        self.assertTrue(any("o que mais pesou foi a quantidade" in x for x in r["leitura"]))

    def test_nao_inventa_causa(self):
        texto = json.dumps(self.r, ensure_ascii=False).lower()
        for palavra in ("porque", "devido", "por causa", "motivado"):
            self.assertNotIn(palavra, texto)

    def test_nao_diz_mes_anterior_em_meses_distantes(self):
        r = analisar(self.t, "2026-01", "2026-09")
        self.assertNotIn("mês anterior", json.dumps(r["destaques"], ensure_ascii=False))
        self.assertIn("em relação a jan/2026", json.dumps(r["destaques"], ensure_ascii=False))

    def test_nao_mistura_receita_com_despesa(self):
        t = self.t + [tx("2026-09-10", 5000, "Bebidas")]
        r = analisar(t)
        self.assertIn("R$ 15,00 a mais", " ".join(i["texto"] for i in r["destaques"]))


class Descobertas(unittest.TestCase):
    def setUp(self):
        self.t = (mensais([100, 100, 100, 100, 100, 100, 100, 100, 100], "Transporte")
                  + mensais([50, 50, 50, 50, 50, 50, 200, 210, 220], "Alimentação", base=False)
                  + [tx("2026-04-05", 4000, "Salário"), tx("2026-07-01", -900, "Compras", "Geladeira")])
        self.descobertas = analisar(self.t)["descobertas"]

    def achar(self, titulo):
        return next(d for d in self.descobertas if d["titulo"] == titulo)

    def test_campos_obrigatorios(self):
        self.assertTrue(self.descobertas)
        for d in self.descobertas:
            for campo in ("titulo", "explicacao", "valores", "periodo", "motivo", "tipo"):
                self.assertTrue(d[campo], campo)

    def test_maior_despesa(self):
        self.assertIn("Geladeira", self.achar("Maior despesa individual")["explicacao"])

    def test_melhor_resultado(self):
        self.assertIn("abr/2026", self.achar("Melhor resultado mensal")["explicacao"])

    def test_maior_crescimento(self):
        self.assertIn("Alimentação", self.achar("Categoria com maior crescimento")["explicacao"])

    def test_compra_unica_nao_vira_maior_reducao(self):
        t = mensais([100] * 9, "Transporte") + [tx("2026-05-05", -3000, "Compras", "Notebook")]
        titulos = {d["titulo"] for d in analisar(t)["descobertas"]}
        self.assertNotIn("Categoria com maior redução", titulos)

    def test_sem_evidencia_nao_ha_descoberta(self):
        titulos = {d["titulo"] for d in analisar([tx("2026-08-05", -5), tx("2026-09-05", -6)])["descobertas"]}
        self.assertEqual(titulos, {"Maior despesa individual"})

    def test_compra_fora_do_padrao(self):
        t = [tx(f"{m}-{d:02d}", -20, "Mercado", f"Feira {m}{d}") for m in MESES for d in (3, 12)]
        t.append(tx("2026-06-20", -400, "Mercado", "Compra grande"))
        d = next(x for x in analisar(t)["descobertas"] if x["titulo"] == "Despesa fora do padrão")
        self.assertIn("Compra grande", d["explicacao"])


class Robustez(unittest.TestCase):
    def test_analise_nao_altera_as_transacoes(self):
        t = mensais([100] * 9)
        copia = json.dumps(t, sort_keys=True)
        analisar(t)
        self.assertEqual(json.dumps(t, sort_keys=True), copia)

    def test_so_um_mes_com_receita(self):
        analisar([tx("2026-08-05", 100), tx("2026-09-05", 100)])

    def test_resposta_vira_json(self):
        json.dumps(analisar(mensais([100, 200] * 4 + [100])))


if __name__ == "__main__":
    unittest.main()
