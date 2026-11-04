import unittest
from datetime import date
import comparativo as comp
import financeiro as fin

HOJE = date(2026, 10, 15)


def tx(data, valor, categoria="Lazer", interno=False, descricao="Loja"):
    return {"id": f"{data}{categoria}{valor}", "conta": "Conta", "data": data, "descricao": descricao,
            "chave": fin.chave_regra(descricao), "categoria_original": categoria,
            "categoria": categoria, "valor": valor, "interno": interno, "interno_original": interno,
            "pendente": False, "parcela": 0, "parcelas_total": 0, "data_compra": "", "mes_fatura": ""}


def linha(resultado, categoria):
    return next(l for l in resultado["categorias"] if l["categoria"] == categoria)


class Calculo(unittest.TestCase):
    def test_exemplos_da_regra(self):
        self.assertEqual(comp.comparar_valores(15, 30)["percentual"], 100)
        self.assertEqual(comp.comparar_valores(15, 30)["diferenca"], 15)
        self.assertEqual(comp.comparar_valores(100, 80)["percentual"], -20)
        self.assertEqual(comp.comparar_valores(100, 80)["diferenca"], -20)
        self.assertEqual(comp.comparar_valores(50, 50)["percentual"], 0)

    def test_primeiro_zero_nao_gera_percentual_infinito(self):
        l = comp.comparar_valores(0, 30, comp.NOVO_GASTO)
        self.assertIsNone(l["percentual"])
        self.assertEqual(l["rotulo"], "Novo gasto")

    def test_dois_zeros(self):
        self.assertEqual(comp.comparar_valores(0, 0)["rotulo"], "Sem movimentação")

    def test_segundo_zero_e_reducao_de_cem_por_cento(self):
        self.assertEqual(comp.comparar_valores(40, 0)["percentual"], -100)

    def test_base_negativa_nao_inverte_o_sentido(self):
        l = comp.comparar_valores(-100, -50)
        self.assertEqual(l["diferenca"], 50)
        self.assertIsNone(l["percentual"])

    def test_nao_arredonda_antes_de_calcular(self):
        self.assertAlmostEqual(comp.comparar_valores(3, 3.335)["percentual"], 11.1666, places=3)

    def test_residuo_de_soma_conta_como_igual(self):
        self.assertEqual(comp.situacao(0.1 + 0.2, 0.3, True), comp.IGUAL)


class Comparacao(unittest.TestCase):
    def test_nao_mistura_outros_meses_nem_receitas(self):
        r = comp.comparar([tx("2025-10-05", -10), tx("2026-03-05", -20), tx("2026-03-06", 500),
                           tx("2026-09-05", -999), tx("2026-10-05", -40)],
                          "2025-10", "2026-03", HOJE)
        self.assertEqual(r["resumo"]["despesas"]["a"], 10)
        self.assertEqual(r["resumo"]["despesas"]["b"], 20)
        self.assertEqual(r["resumo"]["receitas"]["b"], 500)
        self.assertEqual(r["resumo"]["saldo"]["b"], 480)

    def test_ignora_movimentacao_interna(self):
        r = comp.comparar([tx("2026-01-05", -10), tx("2026-02-05", -10),
                           tx("2026-02-06", -900, fin.INTERNO, interno=True)],
                          "2026-01", "2026-02", HOJE)
        self.assertEqual(r["resumo"]["despesas"]["b"], 10)
        self.assertEqual(r["categorias"][0]["categoria"], "Lazer")
        self.assertEqual(len(r["categorias"]), 1)

    def test_soma_igual_a_do_historico(self):
        transacoes = [tx("2026-01-05", -10.1), tx("2026-02-05", -20.2, "Mercado"), tx("2026-02-06", 7)]
        r = comp.comparar(transacoes, "2026-01", "2026-02", HOJE)
        mensal = {m["mes"]: m for m in fin.resumo_mensal(transacoes)}
        self.assertEqual(r["resumo"]["saldo"]["b"], mensal["2026-02"]["resultado"])

    def test_ordem_invertida_segue_a_formula(self):
        r = comp.comparar([tx("2026-01-05", -10), tx("2026-03-05", -30)], "2026-03", "2026-01", HOJE)
        self.assertEqual(r["resumo"]["despesas"]["diferenca"], -20)

    def test_mes_sem_dados_e_recusado(self):
        with self.assertRaises(ValueError):
            comp.comparar([tx("2026-01-05", -10)], "2026-01", "2026-13", HOJE)

    def test_categoria_personalizada_aparece(self):
        r = comp.comparar([tx("2026-01-05", -10, "Minha categoria"), tx("2026-02-05", -30)],
                          "2026-01", "2026-02", HOJE)
        self.assertEqual(linha(r, "Minha categoria")["situacao"], comp.DIMINUIU)
        self.assertEqual(linha(r, "Minha categoria")["percentual"], -100)

    def test_categoria_de_outros_meses_fica_sem_movimentacao(self):
        r = comp.comparar([tx("2026-01-05", -10), tx("2026-02-05", -10), tx("2026-03-05", -5, "Viagem")],
                          "2026-01", "2026-02", HOJE)
        self.assertEqual(linha(r, "Viagem")["situacao"], comp.SEM_MOVIMENTO)


class CategoriasDeUmPeriodo(unittest.TestCase):
    def test_nova_nao_se_confunde_com_retomada(self):
        r = comp.comparar([tx("2026-01-05", -9, "Antiga"), tx("2026-02-05", -1),
                           tx("2026-03-05", -1), tx("2026-03-06", -9, "Antiga"),
                           tx("2026-03-07", -9, "Inedita")], "2026-02", "2026-03", HOJE)
        tipos = {c["categoria"]: c["tipo"] for c in r["um_periodo"]}
        self.assertEqual(tipos, {"Antiga": "retomada", "Inedita": "nova"})
        self.assertEqual(linha(r, "Inedita")["situacao"], comp.NOVA)
        self.assertEqual(linha(r, "Antiga")["situacao"], comp.AUMENTOU)
        self.assertEqual(linha(r, "Antiga")["rotulo"], comp.NOVO_GASTO)

    def test_retomada_cita_o_ultimo_gasto_anterior(self):
        r = comp.comparar([tx("2025-12-05", -9, "Antiga"), tx("2026-01-05", -1),
                           tx("2026-03-05", -9, "Antiga"), tx("2026-06-05", -9, "Antiga")],
                          "2026-01", "2026-03", HOJE)
        self.assertEqual(r["um_periodo"][0]["ultimo_outro_mes"], "2025-12")

    def test_categoria_so_no_primeiro_mes(self):
        r = comp.comparar([tx("2026-02-05", -8, "Saiu"), tx("2026-03-05", -1)],
                          "2026-02", "2026-03", HOJE)
        self.assertEqual(r["um_periodo"][0], {"categoria": "Saiu", "tipo": "so_primeiro", "valor": 8,
                                              "ultimo_outro_mes": None})


class Rankings(unittest.TestCase):
    def setUp(self):
        self.r = comp.comparar(
            [tx("2026-01-05", -100, "A"), tx("2026-02-05", -110, "A"),
             tx("2026-01-05", -10, "B"), tx("2026-02-05", -30, "B"),
             tx("2026-01-05", -50, "C"), tx("2026-02-05", -25, "C"),
             tx("2026-01-05", -20, "D"), tx("2026-02-05", -40, "E")], "2026-01", "2026-02", HOJE)

    def test_aumentos_ordenados_pelo_percentual(self):
        self.assertEqual([l["categoria"] for l in self.r["aumentos"]], ["B", "A"])

    def test_reducoes_ordenadas_pelo_percentual(self):
        self.assertEqual([l["categoria"] for l in self.r["reducoes"]], ["D", "C"])

    def test_novo_gasto_fica_fora_do_ranking(self):
        self.assertNotIn("E", [l["categoria"] for l in self.r["aumentos"]])


class MesEmAndamento(unittest.TestCase):
    def test_compara_mesmo_numero_de_dias(self):
        r = comp.comparar([tx("2026-09-10", -30), tx("2026-09-20", -70), tx("2026-10-12", -40)],
                          "2026-09", "2026-10", HOJE)
        parcial = r["em_andamento"]
        self.assertEqual((parcial["mes"], parcial["dia"], parcial["dias_no_mes"]), ("2026-10", 15, 31))
        self.assertEqual((parcial["despesas"], parcial["despesas_outro"]), (40, 30))

    def test_meses_fechados_nao_tem_aviso(self):
        r = comp.comparar([tx("2026-08-10", -30), tx("2026-09-20", -70)], "2026-08", "2026-09", HOJE)
        self.assertIsNone(r["em_andamento"])


class Evolucao(unittest.TestCase):
    def test_completa_ate_doze_meses_com_os_vizinhos(self):
        transacoes = [tx(f"{fin.somar_meses('2025-01', n)}-05", -1) for n in range(20)]
        r = comp.comparar(transacoes, "2025-10", "2025-11", HOJE)
        self.assertEqual(len(r["evolucao"]), 12)
        self.assertTrue({"2025-10", "2025-11"} <= {m["mes"] for m in r["evolucao"]})

    def test_meses_distantes_entram_inteiros(self):
        transacoes = [tx(f"{fin.somar_meses('2024-01', n)}-05", -1) for n in range(20)]
        r = comp.comparar(transacoes, "2024-01", "2025-08", HOJE)
        self.assertEqual(len(r["evolucao"]), 20)


if __name__ == "__main__":
    unittest.main()
