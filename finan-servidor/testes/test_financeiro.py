import os
import tempfile
import unittest
from datetime import date
import financeiro as fin

BANCO = {"name": "Conta", "type": "BANK", "balance": 1000}
CARTAO = {"name": "Cartão", "type": "CREDIT", "balance": 300}


def tx(conta=BANCO, categorias=None, **campos):
    return fin.normalizar_transacao({"date": "2026-10-10T00:00:00.000Z", **campos},
                                    conta, categorias or {})


class Regras(unittest.TestCase):
    def test_fatura_nao_soma_no_saldo(self):
        self.assertEqual(fin.resumo_contas([BANCO, CARTAO]), (1000, 300))

    def test_compra_no_cartao_e_saida(self):
        self.assertEqual(tx(CARTAO, amount=50, type="CREDIT", description="Loja")["valor"], -50)

    def test_conta_segue_campo_type(self):
        self.assertEqual(tx(amount=80, type="DEBIT", description="Boleto")["valor"], -80)
        self.assertEqual(tx(amount=-80, type="CREDIT", description="Pix")["valor"], 80)

    def test_compra_em_moeda_estrangeira_usa_valor_em_reais(self):
        t = tx(CARTAO, amount=10, amountInAccountCurrency=55, description="Steam")
        self.assertEqual(t["valor"], -55)

    def test_pagar_fatura_nao_conta_duas_vezes(self):
        compra = tx(CARTAO, amount=100, description="Loja")
        na_conta = tx(amount=100, type="DEBIT", description="Pagamento de fatura")
        no_cartao = tx(CARTAO, amount=-100, description="Pagamento recebido")
        entradas, saidas, _ = fin.totais([compra, na_conta, no_cartao])
        self.assertEqual((entradas, saidas), (0, 100))

    def test_categoria_usa_nome_traduzido_da_principal(self):
        mapa = fin.mapa_categorias([
            {"id": "1", "description": "Leisure", "descriptionTranslated": "Lazer"},
            {"id": "2", "description": "Cinema", "descriptionTranslated": "Cinema", "parentId": "1"},
        ])
        t = tx(categorias=mapa, amount=1, type="DEBIT", description="X", categoryId="2")
        self.assertEqual(t["categoria"], "Lazer")

    def test_sem_categoria_da_pluggy_usa_palavras(self):
        self.assertEqual(tx(amount=1, type="DEBIT", description="IFOOD *Lanche")["categoria"],
                         "Alimentação")
        self.assertEqual(tx(amount=1, type="DEBIT", description="Zzz")["categoria"],
                         fin.SEM_CATEGORIA)

    def test_mes_passado_atravessa_o_ano(self):
        self.assertEqual(fin.intervalo("Mês passado", date(2026, 1, 15)),
                         (date(2025, 12, 1), date(2025, 12, 31)))

    def test_filtro_busca_sem_acento(self):
        t = tx(amount=1, type="DEBIT", description="Padaria São João")
        self.assertEqual(fin.filtrar([t], "Este mês", busca="sao joao", hoje=date(2026, 10, 30)), [t])
        self.assertEqual(fin.filtrar([t], "Mês passado", hoje=date(2026, 10, 30)), [])

    def test_regra_vale_para_mesma_loja_com_numero_diferente(self):
        a = tx(id="a", amount=10, type="DEBIT", description="LOJA X 03/12")
        b = tx(id="b", amount=10, type="DEBIT", description="Loja X 04/12")
        regras = fin.regras_vazias()
        fin.definir_regra(regras, a, "Lazer", todas=True)
        fin.aplicar_regras([a, b], regras)
        self.assertEqual((a["categoria"], b["categoria"]), ("Lazer", "Lazer"))

    def test_regra_de_uma_transacao_nao_afeta_as_outras(self):
        a = tx(id="a", amount=10, type="DEBIT", description="Loja X", category="Shopping")
        b = tx(id="b", amount=10, type="DEBIT", description="Loja X", category="Shopping")
        regras = fin.regras_vazias()
        fin.definir_regra(regras, a, "Lazer", todas=False)
        fin.aplicar_regras([a, b], regras)
        self.assertEqual((a["categoria"], b["categoria"]), ("Lazer", "Shopping"))

    def test_correcao_interna_muda_os_totais(self):
        pix = tx(id="a", amount=100, type="DEBIT", description="Pix para mim")
        guardar = tx(id="b", amount=50, type="DEBIT", description="Dinheiro guardado")
        regras = fin.regras_vazias()
        fin.definir_regra(regras, pix, fin.INTERNO, todas=True)
        fin.definir_regra(regras, guardar, "Lazer", todas=True)
        fin.aplicar_regras([pix, guardar], regras)
        self.assertEqual(fin.totais([pix, guardar])[1], 50)

    def entrada(self, id, valor):
        return fin.normalizar_transacao({
            "id": id, "date": "2026-10-01T00:00:00.000Z", "amount": valor, "type": "CREDIT",
            "description": "Transferencia recebida Fulano", "category": "Same person transfer"},
            BANCO, {})

    def test_faixa_separa_salario_de_transferencia_pequena(self):
        salario, pequena = self.entrada("a", 1821), self.entrada("b", 24.01)
        regras = fin.regras_vazias()
        regras["faixas"][salario["chave"]] = {"minimo": 1000, "categoria": "Salário"}
        fin.aplicar_regras([salario, pequena], regras)
        self.assertEqual((salario["categoria"], salario["interno"]), ("Salário", False))
        self.assertEqual(pequena["categoria"], fin.INTERNO)
        self.assertEqual(fin.totais([salario, pequena])[0], 1821)

    def test_saida_grande_com_mesma_descricao_nao_vira_salario(self):
        saida = fin.normalizar_transacao({"id": "a", "date": "2026-10-01T00:00:00.000Z",
                                          "amount": 1821, "type": "DEBIT",
                                          "description": "Transferencia recebida Fulano"}, BANCO, {})
        regras = fin.regras_vazias()
        regras["faixas"][saida["chave"]] = {"minimo": 1000, "categoria": "Salário"}
        fin.aplicar_regras([saida], regras)
        self.assertNotEqual(saida["categoria"], "Salário")

    def test_correcao_na_tela_vale_mais_que_a_faixa(self):
        um, dois = self.entrada("a", 1821), self.entrada("b", 1815)
        regras = fin.regras_vazias()
        regras["faixas"][um["chave"]] = {"minimo": 1000, "categoria": "Salário"}
        fin.definir_regra(regras, um, "Bônus", todas=False)
        fin.aplicar_regras([um, dois], regras)
        self.assertEqual((um["categoria"], dois["categoria"]), ("Bônus", "Salário"))
        fin.definir_regra(regras, dois, "Outros", todas=True)
        fin.aplicar_regras([um, dois], regras)
        self.assertEqual(dois["categoria"], "Outros")

    def test_arquivo_antigo_de_regras_continua_funcionando(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "regras.json")
            fin.gravar_json({"transacoes": {}, "descricoes": {"loja": "Lazer"}}, caminho)
            self.assertEqual(fin.carregar_regras(caminho)["faixas"], {})

    def test_regras_sobrevivem_ao_reabrir(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "regras.json")
            self.assertEqual(fin.carregar_regras(caminho), fin.regras_vazias())
            regras = fin.regras_vazias()
            regras["descricoes"]["padaria sao joao"] = "Alimentação"
            fin.gravar_json(regras, caminho)
            self.assertEqual(fin.carregar_regras(caminho), regras)

    def test_arquivo_estragado_nao_e_perdido(self):
        with tempfile.TemporaryDirectory() as pasta:
            caminho = os.path.join(pasta, "regras.json")
            with open(caminho, "w", encoding="utf-8") as arquivo:
                arquivo.write("{quebrado")
            self.assertEqual(fin.carregar_regras(caminho), fin.regras_vazias())
            self.assertTrue(os.path.exists(f"{caminho}.estragado"))

    def test_formato_brl(self):
        self.assertEqual(fin.formatar_brl(-1234.5), "- R$ 1.234,50")


if __name__ == "__main__":
    unittest.main()
