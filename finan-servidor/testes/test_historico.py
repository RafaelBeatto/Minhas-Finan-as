import os
import sqlite3
import tempfile
import unittest
from datetime import date
import financeiro as fin
import historico

CONTA = {"id": "c1", "name": "Conta", "type": "BANK"}


def tx(id, data="2026-10-10", valor=10, status="POSTED", descricao="Loja"):
    return fin.normalizar_transacao({"id": id, "date": f"{data}T00:00:00.000Z", "amount": valor,
                                     "type": "DEBIT", "status": status,
                                     "description": descricao, "category": "Shopping"}, CONTA, {})


class Historico(unittest.TestCase):
    def setUp(self):
        self.pasta = tempfile.TemporaryDirectory()
        self.addCleanup(self.pasta.cleanup)
        self.banco = os.path.join(self.pasta.name, "historico.db")

    def ids(self):
        return sorted(t["id"] for t in historico.carregar(self.banco))

    def test_guarda_e_devolve_igual(self):
        historico.salvar(self.banco, "c1", "2026-10-01", [tx("a", status="PENDING")])
        t = historico.carregar(self.banco)[0]
        self.assertEqual((t["valor"], t["categoria"], t["interno"], t["pendente"]),
                         (-10, "Shopping", False, True))

    def test_transacao_antiga_continua_quando_sai_da_janela(self):
        historico.salvar(self.banco, "c1", "2025-01-01", [tx("velha", data="2025-02-01")])
        historico.salvar(self.banco, "c1", "2026-10-01", [tx("nova")])
        self.assertEqual(self.ids(), ["nova", "velha"])

    def test_atualizar_de_novo_nao_duplica(self):
        for _ in range(2):
            historico.salvar(self.banco, "c1", "2026-10-01", [tx("a")])
        self.assertEqual(self.ids(), ["a"])

    def test_pendente_confirmada_com_outro_id_nao_duplica(self):
        historico.salvar(self.banco, "c1", "2026-10-01", [tx("p", status="PENDING")])
        historico.salvar(self.banco, "c1", "2026-10-01", [tx("q")])
        self.assertEqual(self.ids(), ["q"])

    def test_resposta_vazia_nao_apaga_confirmadas(self):
        historico.salvar(self.banco, "c1", "2026-10-01", [tx("a")])
        historico.salvar(self.banco, "c1", "2026-10-01", [])
        self.assertEqual(self.ids(), ["a"])

    def test_pendente_de_outra_conta_nao_e_mexida(self):
        historico.salvar(self.banco, "c2", "2026-10-01", [tx("outra", status="PENDING")])
        historico.salvar(self.banco, "c1", "2026-10-01", [])
        self.assertEqual(self.ids(), ["outra"])

    def test_tem_dados_por_conta(self):
        self.assertFalse(historico.tem_dados(self.banco, "c1"))
        historico.salvar(self.banco, "c1", "2026-10-01", [tx("a")])
        self.assertTrue(historico.tem_dados(self.banco, "c1"))
        self.assertFalse(historico.tem_dados(self.banco, "c2"))


    def test_banco_da_versao_anterior_e_migrado_sem_perder_nada(self):
        conexao = sqlite3.connect(self.banco)
        conexao.execute(historico.CRIAR_TABELA)
        conexao.execute("INSERT INTO transacoes VALUES ('velha','c1','Conta','2025-02-01','Loja',"
                        "'loja','Shopping',-10,0,0)")
        conexao.commit()
        conexao.close()
        self.assertFalse(historico.tem_dados(self.banco, "c1"))
        self.assertEqual(historico.carregar(self.banco)[0]["parcelas_total"], 0)
        historico.salvar(self.banco, "c1", "2026-10-01", [tx("nova")])
        self.assertEqual(self.ids(), ["nova", "velha"])
        self.assertTrue(historico.tem_dados(self.banco, "c1"))

    def test_guarda_dados_de_parcela(self):
        t = tx("a")
        t.update(parcela=2, parcelas_total=10, data_compra="2026-08-01", mes_fatura="2026-10")
        historico.salvar(self.banco, "c1", "2026-10-01", [t])
        salva = historico.carregar(self.banco)[0]
        self.assertEqual((salva["parcela"], salva["parcelas_total"], salva["mes_fatura"]),
                         (2, 10, "2026-10"))


class Cartao(unittest.TestCase):
    HOJE = date(2026, 10, 30)
    CARTAO = {"id": "c", "name": "Cartão", "type": "CREDIT"}

    def compra(self, id, parcela, total, mes, valor=100, descricao="Loja X", compra="2026-08-01"):
        return fin.normalizar_transacao({
            "id": id, "date": f"{mes}-05T00:00:00.000Z", "amount": valor, "description": descricao,
            "creditCardMetadata": {"installmentNumber": parcela, "totalInstallments": total,
                                   "purchaseDate": f"{compra}T00:00:00.000Z",
                                   "billForecastDate": f"{mes}-20"}}, self.CARTAO, {})

    def test_usa_a_ultima_parcela_conhecida(self):
        abertas = fin.parcelas_abertas([self.compra("a", 2, 4, "2026-09"),
                                        self.compra("b", 3, 4, "2026-10")], self.HOJE)
        self.assertEqual(len(abertas), 1)
        self.assertEqual((abertas[0]["parcela"], abertas[0]["meses"], abertas[0]["restante"]),
                         (3, ["2026-11"], 100))

    def test_compra_quitada_nao_aparece(self):
        self.assertEqual(fin.parcelas_abertas([self.compra("a", 4, 4, "2026-10")], self.HOJE), [])

    def test_a_vista_nao_aparece(self):
        self.assertEqual(fin.parcelas_abertas([self.compra("a", 1, 1, "2026-10")], self.HOJE), [])

    def test_mesma_loja_em_compras_diferentes_fica_separada(self):
        abertas = fin.parcelas_abertas([
            self.compra("a", 1, 3, "2026-10", compra="2026-10-01"),
            self.compra("b", 1, 3, "2026-10", compra="2026-10-02")], self.HOJE)
        self.assertEqual(fin.compromisso_por_mes(abertas),
                         [("2026-11", 200), ("2026-12", 200)])

    def test_parcelas_viram_o_ano(self):
        abertas = fin.parcelas_abertas([self.compra("a", 1, 4, "2026-11")], self.HOJE)
        self.assertEqual(abertas[0]["meses"], ["2026-12", "2027-01", "2027-02"])

    def test_mes_ja_passado_nao_conta_como_compromisso(self):
        abertas = fin.parcelas_abertas([self.compra("a", 1, 3, "2026-06")], self.HOJE)
        self.assertEqual(abertas, [])

    def test_resumo_separa_limite_usado_da_fatura(self):
        r = fin.resumo_cartao([{"type": "BANK", "balance": 999},
                               {"type": "CREDIT", "balance": 300, "creditData": {
                                   "creditLimit": 1000, "availableCreditLimit": 400,
                                   "balanceDueDate": "2026-11-10T00:00:00.000Z",
                                   "minimumPayment": 45}}])
        self.assertEqual((r["fatura"], r["usado"], r["vencimento"], r["minimo"]),
                         (300, 600, "2026-11-10", 45))

    def test_resumo_sem_dados_do_cartao(self):
        r = fin.resumo_cartao([{"type": "CREDIT", "balance": 300}])
        self.assertEqual((r["limite"], r["vencimento"], r["minimo"]), (0, None, None))

    def test_resumo_de_fatura_soma_encargos(self):
        r = fin.resumo_fatura({"dueDate": "2026-11-10", "totalAmount": 500,
                               "financeCharges": [{"amount": 10}, {"amount": 5.5}]})
        self.assertEqual((r["total"], r["encargos"]), (500, 15.5))


class Meses(unittest.TestCase):
    def test_resumo_compara_com_mes_anterior(self):
        transacoes = [tx("a", "2026-09-05", 100), tx("b", "2026-10-05", 150),
                      tx("c", "2026-10-06", 900, descricao="Pagamento de fatura")]
        outubro, setembro = fin.resumo_mensal(transacoes)
        self.assertEqual((outubro["mes"], outubro["saidas"], outubro["variacao"]), ("2026-10", 150, 50))
        self.assertIsNone(setembro["variacao"])

    def test_mes_sem_movimento_nao_compara_com_o_errado(self):
        transacoes = [tx("a", "2026-08-05", 100), tx("b", "2026-10-05", 150)]
        self.assertEqual(fin.resumo_mensal(transacoes)[0]["variacao"], 150)

    def test_comparacao_por_categoria(self):
        transacoes = [tx("a", "2026-09-05", 100), tx("b", "2026-10-05", 150)]
        self.assertEqual(fin.comparar_categorias(transacoes, "2026-10"), [("Shopping", 150, 100, 50)])

    def test_mes_anterior_vira_o_ano(self):
        self.assertEqual(fin.mes_anterior("2026-01"), "2025-12")

    def test_nome_do_mes(self):
        self.assertEqual(fin.nome_mes("2026-10"), "out/2026")


if __name__ == "__main__":
    unittest.main()
