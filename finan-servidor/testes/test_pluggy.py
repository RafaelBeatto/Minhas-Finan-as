import os
import tempfile
import unittest
from unittest import mock
import requests
import historico
import pluggy

CONTA = {"id": "c1", "name": "Conta", "type": "BANK", "balance": 150.5, "segredo": "x"}
CARTAO = {"id": "c2", "name": "Cartão", "type": "CREDIT", "balance": 80, "creditData": {}}
TRANSACAO = {"id": "t1", "description": "Padaria", "date": "2026-04-02T10:00:00Z",
             "amount": 12.5, "type": "DEBIT", "status": "POSTED"}
FATURA = {"dueDate": "2026-05-10", "billClosingDate": "2026-05-01", "totalAmount": 80,
          "minimumPaymentAmount": 8, "financeCharges": []}


def resposta(dados, status=200):
    r = requests.Response()
    r.status_code = status
    r.json = lambda: dados
    return r


def falsa_get(url, **argumentos):
    if url.endswith("/accounts"):
        return resposta({"results": [CONTA, CARTAO]})
    if url.endswith("/categories"):
        return resposta({"results": [], "totalPages": 1})
    if url.endswith("/bills"):
        return resposta({"results": [FATURA], "totalPages": 1})
    if argumentos["params"]["accountId"] == "c1":
        return resposta({"results": [TRANSACAO]})
    return resposta({"results": []})


class TestSincronizar(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        self.banco = os.path.join(pasta.name, "h.db")

    def sincronizar(self, get):
        with mock.patch.object(pluggy.requests, "post", return_value=resposta({"apiKey": "k"})), \
             mock.patch.object(pluggy.requests, "get", side_effect=get):
            return pluggy.sincronizar("id", "secret", "item", self.banco)

    def test_grava_transacoes_contas_e_faturas(self):
        self.assertIsNone(self.sincronizar(falsa_get))
        self.assertEqual(historico.carregar(self.banco)[0]["valor"], -12.5)
        guardado = historico.carregar_instantaneo(self.banco)
        self.assertEqual(guardado["contas"][0]["balance"], 150.5)
        self.assertNotIn("segredo", guardado["contas"][0])
        self.assertEqual(guardado["faturas"][0]["total"], 80)
        self.assertTrue(guardado["atualizado_em"])

    def test_falha_nas_faturas_mantem_as_salvas(self):
        self.sincronizar(falsa_get)

        def get(url, **argumentos):
            if url.endswith("/bills"):
                raise requests.ConnectionError("queda")
            return falsa_get(url, **argumentos)
        aviso = self.sincronizar(get)
        self.assertIn("faturas", aviso)
        self.assertEqual(len(historico.carregar_instantaneo(self.banco)["faturas"]), 1)

    def test_extrato_falhou_mas_contas_ficam(self):
        def get(url, **argumentos):
            if "/v2/transactions" in url:
                return resposta({}, 500)
            return falsa_get(url, **argumentos)
        aviso = self.sincronizar(get)
        self.assertIn("extrato", aviso)
        self.assertEqual(len(historico.carregar_instantaneo(self.banco)["contas"]), 2)


if __name__ == "__main__":
    unittest.main()
