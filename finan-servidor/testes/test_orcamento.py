import os
import tempfile
import unittest
from datetime import date
import financeiro as fin

CONTA = {"id": "c1", "name": "Conta", "type": "BANK"}
HOJE = date(2026, 10, 30)


def tx(data, valor, categoria="Lazer", descricao="Loja"):
    return fin.normalizar_transacao({"id": data + categoria, "date": f"{data}T00:00:00.000Z",
                                     "amount": valor, "type": "DEBIT", "description": descricao,
                                     "category": categoria}, CONTA, {})


def linha(linhas, categoria):
    return next(l for l in linhas if l["categoria"] == categoria)


class Orcamento(unittest.TestCase):
    def test_estados_do_limite(self):
        self.assertEqual(fin.estado_orcamento(79, 100), "ok")
        self.assertEqual(fin.estado_orcamento(80, 100), "atencao")
        self.assertEqual(fin.estado_orcamento(100, 100), "estourou")
        self.assertEqual(fin.estado_orcamento(500, None), "sem limite")

    def test_conta_so_o_mes_atual(self):
        linhas = fin.situacao_orcamento([tx("2026-09-10", 500), tx("2026-10-10", 50)],
                                        {"Lazer": 100}, HOJE)
        l = linha(linhas, "Lazer")
        self.assertEqual((l["gasto"], l["restante"], l["uso"]), (50, 50, .5))

    def test_movimentacao_interna_nao_gasta_orcamento(self):
        linhas = fin.situacao_orcamento([tx("2026-10-10", 500, descricao="Pagamento de fatura")],
                                        {"Lazer": 100}, HOJE)
        self.assertEqual(linha(linhas, "Lazer")["gasto"], 0)

    def test_categoria_com_limite_aparece_mesmo_sem_gasto(self):
        self.assertEqual(linha(fin.situacao_orcamento([], {"Viagem": 300}, HOJE), "Viagem")["estado"],
                         "ok")

    def test_mais_perto_de_estourar_vem_primeiro(self):
        linhas = fin.situacao_orcamento(
            [tx("2026-10-10", 90, "A"), tx("2026-10-11", 120, "B"), tx("2026-10-12", 999, "C")],
            {"A": 100, "B": 100}, HOJE)
        self.assertEqual([l["categoria"] for l in linhas], ["B", "A", "C"])

    def test_media_ignora_o_mes_atual_e_meses_sem_movimento(self):
        transacoes = [tx("2026-09-10", 100), tx("2026-08-10", 200), tx("2026-10-10", 999)]
        self.assertEqual(fin.media_gastos(transacoes, "2026-10"), {"Lazer": 150})

    def test_media_vira_o_ano(self):
        self.assertEqual(fin.media_gastos([tx("2025-12-10", 90)], "2026-01"), {"Lazer": 90})

    def test_sem_historico_nao_divide_por_zero(self):
        self.assertEqual(fin.media_gastos([], "2026-10"), {})

    def test_texto_do_alerta(self):
        linhas = fin.situacao_orcamento(
            [tx("2026-10-10", 90, "A"), tx("2026-10-11", 120, "B"), tx("2026-10-12", 1, "C")],
            {"A": 100, "B": 100, "C": 100}, HOJE)
        self.assertEqual(fin.texto_alerta(linhas), "Orçamento do mês: B estourou, A em 90%")
        self.assertEqual(fin.texto_alerta([]), "")

    def test_ler_valor(self):
        for texto, esperado in (("800", 800), ("800,50", 800.5), ("1.234,50", 1234.5),
                                ("1.234", 1234), ("R$ 2.000", 2000), ("12.5", 12.5), ("", None)):
            self.assertEqual(fin.ler_valor(texto), esperado)

    def test_valor_invalido(self):
        for texto in ("abc", "0", "-5", "inf", "nan"):
            with self.assertRaises(ValueError):
                fin.ler_valor(texto)

    def test_orcamento_sobrevive_ao_reabrir(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "orcamento.json")
            self.assertEqual(fin.carregar_orcamento(caminho), {})
            fin.gravar_json({"Lazer": 300}, caminho)
            self.assertEqual(fin.carregar_orcamento(caminho), {"Lazer": 300})


if __name__ == "__main__":
    unittest.main()
