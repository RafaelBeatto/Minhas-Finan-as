import os
import tempfile
import unittest
from datetime import date, datetime
from openpyxl import load_workbook
import exportar
import financeiro as fin

CONTA = {"id": "c", "name": "Conta", "type": "BANK"}
HOJE = date(2026, 10, 30)


def tx(id, data, valor, descricao="Netflix", categoria="Lazer"):
    return fin.normalizar_transacao({"id": id, "date": f"{data}T00:00:00.000Z", "amount": valor,
                                     "type": "DEBIT", "description": descricao,
                                     "category": categoria}, CONTA, {})


class Planilha(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.caminho = os.path.join(pasta.name, "saida.xlsx")

    def gerar(self, transacoes, orcamento=None):
        exportar.gerar_planilha(self.caminho, transacoes, orcamento or {}, [], HOJE)
        return load_workbook(self.caminho)

    def test_cria_todas_as_abas_mesmo_sem_dados(self):
        self.assertEqual(self.gerar([]).sheetnames, ["Extrato", "Meses", "Categorias", "Orçamento",
                                                     "Assinaturas", "Parcelas"])

    def test_extrato_tem_numero_e_data_de_verdade(self):
        linha = self.gerar([tx("a", "2026-10-10", 39.9)])["Extrato"][2]
        self.assertEqual(linha[0].value, datetime(2026, 10, 10))
        self.assertEqual(linha[4].value, -39.9)
        self.assertEqual(linha[5].value, "Sim")

    def test_movimentacao_interna_fica_marcada(self):
        aba = self.gerar([tx("a", "2026-10-10", 100, "Pagamento de fatura")])["Extrato"]
        self.assertEqual(aba["F2"].value, "Não")
        self.assertIsNone(self.gerar([tx("a", "2026-10-10", 100, "Pagamento de fatura")])["Categorias"]["A2"].value)

    def test_texto_com_igual_nao_vira_formula(self):
        arquivo = self.gerar([tx("a", "2026-10-10", 1, '=HYPERLINK("http://x")')])
        celula = arquivo["Extrato"]["B2"]
        self.assertEqual(celula.data_type, "s")
        self.assertEqual(celula.value, '=HYPERLINK("http://x")')

    def test_categorias_por_mes_batem_com_o_total(self):
        aba = self.gerar([tx("a", "2026-09-10", 100), tx("b", "2026-10-10", 50),
                          tx("c", "2026-10-11", 25, categoria="Moradia")])["Categorias"]
        self.assertEqual([c.value for c in aba[1]], ["Categoria", "set/2026", "out/2026", "Total"])
        self.assertEqual([c.value for c in aba[2]], ["Lazer", 100, 50, 150])
        self.assertEqual([c.value for c in aba[3]], ["Moradia", 0, 25, 25])

    def test_orcamento_e_assinaturas_saem_na_planilha(self):
        transacoes = [tx(m, f"2026-{m}-10", 40) for m in ("08", "09", "10")]
        arquivo = self.gerar(transacoes, {"Lazer": 100})
        self.assertEqual([c.value for c in arquivo["Orçamento"][2]][:3], ["Lazer", 100, 40])
        self.assertEqual(arquivo["Assinaturas"]["A2"].value, "Netflix")


if __name__ == "__main__":
    unittest.main()
