import unittest
from datetime import date
import financeiro as fin

CONTA = {"id": "c", "name": "Cartão", "type": "CREDIT"}
HOJE = date(2026, 10, 30)


def tx(data, valor=39.9, descricao="Netflix", parcela=0, total=0):
    return fin.normalizar_transacao({
        "id": data + descricao, "date": f"{data}T00:00:00.000Z", "amount": valor,
        "description": descricao, "category": "Video streaming",
        "creditCardMetadata": {"installmentNumber": parcela, "totalInstallments": total}},
        CONTA, {})


def detectar(*transacoes, **opcoes):
    return fin.detectar_assinaturas(list(transacoes), HOJE, **opcoes)


class Assinaturas(unittest.TestCase):
    def test_detecta_cobranca_mensal(self):
        a = detectar(tx("2026-08-10"), tx("2026-09-10"), tx("2026-10-10"))[0]
        self.assertEqual((a["descricao"], a["meses"], a["ativa"], a["proxima"]),
                         ("Netflix", 3, True, "2026-11-10"))

    def test_dois_meses_ainda_nao_basta(self):
        self.assertEqual(detectar(tx("2026-09-10"), tx("2026-10-10")), [])

    def test_varias_compras_no_mes_nao_e_assinatura(self):
        compras = [tx(f"2026-{m:02d}-{d:02d}", 40, "iFood") for m in (8, 9, 10) for d in (5, 15)]
        self.assertEqual(detectar(*compras), [])

    def test_valores_muito_diferentes_nao_e_assinatura(self):
        self.assertEqual(detectar(tx("2026-08-10", 30, "Loja"), tx("2026-09-10", 200, "Loja"),
                                  tx("2026-10-10", 90, "Loja")), [])

    def test_compras_espalhadas_nao_e_assinatura(self):
        self.assertEqual(detectar(tx("2026-01-10"), tx("2026-05-10"), tx("2026-10-10")), [])

    def test_aceita_um_mes_pulado(self):
        self.assertEqual(len(detectar(tx("2026-06-30"), tx("2026-08-01"), tx("2026-09-01"))), 1)

    def test_parcelas_nao_sao_assinatura(self):
        self.assertEqual(detectar(*[tx(f"2026-{m:02d}-10", parcela=m - 7, total=6)
                                    for m in (8, 9, 10)]), [])

    def test_pagamento_de_fatura_nao_e_assinatura(self):
        self.assertEqual(detectar(*[tx(f"2026-{m:02d}-10", descricao="Pagamento de fatura")
                                    for m in (8, 9, 10)]), [])

    def test_estorno_nao_conta(self):
        self.assertEqual(detectar(*[tx(f"2026-{m:02d}-10", -39.9) for m in (8, 9, 10)]), [])

    def test_parada_nao_entra_no_custo(self):
        velha = [tx(f"2026-{m:02d}-10", 20, "Academia") for m in (5, 6, 7)]
        atual = [tx(f"2026-{m:02d}-10", 50) for m in (8, 9, 10)]
        assinaturas = detectar(*velha, *atual)
        self.assertEqual([a["ativa"] for a in assinaturas], [True, False])
        self.assertEqual(fin.custo_assinaturas(assinaturas), 50)

    def test_detecta_aumento(self):
        a = detectar(tx("2026-08-10", 40), tx("2026-09-10", 40), tx("2026-10-10", 45))[0]
        self.assertEqual((a["valor"], a["aumento"]), (45, 5))

    def test_mudanca_de_centavos_nao_e_aumento(self):
        a = detectar(tx("2026-08-10", 40), tx("2026-09-10", 40), tx("2026-10-10", 40.1))[0]
        self.assertEqual(a["aumento"], 0)

    def test_ignorada_some_da_lista(self):
        self.assertEqual(detectar(tx("2026-08-10"), tx("2026-09-10"), tx("2026-10-10"),
                                  ignoradas=["netflix"]), [])

    def test_proxima_cobranca_em_mes_mais_curto(self):
        a = fin.detectar_assinaturas([tx("2026-11-30"), tx("2026-12-31"), tx("2027-01-31")],
                                     date(2027, 2, 1))[0]
        self.assertEqual(a["proxima"], "2027-02-28")

    def test_movimentacao_interna_corrigida_sai_da_lista(self):
        transacoes = [tx("2026-08-10"), tx("2026-09-10"), tx("2026-10-10")]
        regras = fin.regras_vazias()
        fin.definir_regra(regras, transacoes[0], fin.INTERNO, todas=True)
        fin.aplicar_regras(transacoes, regras)
        self.assertEqual(fin.detectar_assinaturas(transacoes, HOJE), [])


if __name__ == "__main__":
    unittest.main()
