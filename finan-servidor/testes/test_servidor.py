import http.client
import json
import os
import tempfile
import threading
import unittest
from datetime import date
from functools import partial
from unittest import mock
import financeiro as fin
import historico
import servidor


def transacao(id_, data, valor, descricao="Mercado"):
    return {"id": id_, "conta": "Conta", "data": data, "descricao": descricao,
            "chave": fin.chave_regra(descricao), "categoria_original": "Mercado", "valor": valor,
            "interno_original": False, "pendente": False, "parcela": 0, "parcelas_total": 0,
            "data_compra": "", "mes_fatura": ""}


class TestPrevisao(unittest.TestCase):
    def test_projeta_pelo_ritmo_do_mes(self):
        t = {**transacao("1", "2026-04-05", -100), "categoria": "Mercado", "interno": False}
        previsao = fin.previsao_mes([t], date(2026, 4, 10))
        self.assertEqual(previsao["gasto"], 100)
        self.assertEqual(previsao["projecao"], 300)

    def test_sem_projecao_nos_primeiros_dias(self):
        self.assertIsNone(fin.previsao_mes([], date(2026, 4, 3))["projecao"])

    def test_proximo_mes_soma_parcelas_e_assinaturas(self):
        abertas = [{"valor": 50, "meses": ["2026-05", "2026-06"]}, {"valor": 9, "meses": ["2026-06"]}]
        resultado = fin.compromissos_proximo_mes(abertas, [{"valor": 20, "ativa": True}],
                                                 date(2026, 4, 10))
        self.assertEqual((resultado["mes"], resultado["total"]), ("2026-05", 70))

    def test_remover_regra_desfaz_regra_da_descricao(self):
        regras = {"transacoes": {"1": "A"}, "faixas": {"x": {}}, "descricoes": {"x": "B"}}
        fin.remover_regra(regras, {"id": "1", "chave": "x"})
        self.assertEqual(regras, fin.regras_vazias())

    def test_filtro_por_datas_substitui_periodo(self):
        t = [{**transacao("1", "2020-01-10", -1), "categoria": "M", "interno": False}]
        self.assertEqual(len(fin.filtrar(t, "Este mês", hoje=date(2026, 4, 1))), 0)
        self.assertEqual(len(fin.filtrar(t, "Este mês", hoje=date(2026, 4, 1),
                                         de="2020-01-01", ate="2020-01-31")), 1)


class TestFiltros(unittest.TestCase):
    def setUp(self):
        base = {"categoria": "Mercado", "interno": False}
        self.lista = [
            {**transacao("1", "2026-04-01", -50), **base},
            {**transacao("2", "2026-04-02", 300), **base},
            {**transacao("3", "2026-04-03", -900), **base, "interno": True},
            {**transacao("4", "2026-04-04", -120), **base, "parcelas_total": 3, "pendente": True},
            {**transacao("5", "2026-04-05", -10), **base, "categoria": "Lazer"},
        ]

    def ids(self, **filtros):
        return [t["id"] for t in fin.filtrar_detalhes(self.lista, **filtros)]

    def test_por_tipo(self):
        self.assertEqual(self.ids(tipo="entradas"), ["2"])
        self.assertEqual(self.ids(tipo="saidas"), ["1", "4", "5"])
        self.assertEqual(self.ids(tipo="internas"), ["3"])

    def test_por_situacao(self):
        self.assertEqual(self.ids(situacao="pendentes"), ["4"])
        self.assertEqual(self.ids(situacao="parceladas"), ["4"])
        self.assertEqual(self.ids(situacao="corrigidas"), ["5"])

    def test_faixa_de_valor_ignora_o_sinal(self):
        self.assertEqual(self.ids(minimo=100, maximo=400), ["2", "4"])

    def test_sem_internas(self):
        self.assertEqual(self.ids(sem_internas=True), ["1", "2", "4", "5"])


class TestApi(unittest.TestCase):
    def setUp(self):
        pasta = tempfile.TemporaryDirectory()
        self.addCleanup(pasta.cleanup)
        banco = os.path.join(pasta.name, "h.db")
        hoje = date.today().isoformat()
        historico.salvar(banco, "c1", "2000-01-01", [transacao("1", hoje, -80)])
        self.addCleanup(mock.patch.stopall)
        for nome, arquivo in (("ARQUIVO_HISTORICO", banco),
                              ("ARQUIVO_REGRAS", os.path.join(pasta.name, "r.json")),
                              ("ARQUIVO_ORCAMENTO", os.path.join(pasta.name, "o.json")),
                              ("ARQUIVO_ASSINATURAS", os.path.join(pasta.name, "a.json"))):
            mock.patch.object(servidor, nome, arquivo).start()
        self.http = servidor.Servidor(("127.0.0.1", 0),
                                      partial(servidor.Manipulador, directory=pasta.name))
        self.addCleanup(self.http.server_close)
        self.addCleanup(self.http.shutdown)
        threading.Thread(target=self.http.serve_forever, daemon=True).start()

    def pedir(self, metodo, caminho, corpo=None, cabecalhos=None):
        conexao = http.client.HTTPConnection("127.0.0.1", self.http.server_address[1])
        self.addCleanup(conexao.close)
        enviar = {"Content-Type": "application/json", **(cabecalhos or {})}
        conexao.request(metodo, f"/api/finan{caminho}",
                        None if corpo is None else json.dumps(corpo), enviar)
        resposta = conexao.getresponse()
        conteudo = resposta.read()
        return resposta.status, json.loads(conteudo) if conteudo[:1] == b"{" else conteudo

    def test_painel_nao_expoe_segredo(self):
        with mock.patch.object(servidor, "CLIENT_SECRET", "segredo-teste"):
            status, dados = self.pedir("GET", "/painel")
        self.assertEqual(status, 200)
        self.assertNotIn("segredo-teste", json.dumps(dados))

    def test_corrigir_e_desfazer_categoria(self):
        self.pedir("POST", "/regra", {"id": "1", "categoria": "Lazer", "todas": True})
        t = self.pedir("GET", "/extrato")[1]["transacoes"][0]
        self.assertEqual((t["categoria"], t["corrigida"]), ("Lazer", True))
        self.pedir("POST", "/regra/remover", {"id": "1"})
        t = self.pedir("GET", "/extrato")[1]["transacoes"][0]
        self.assertEqual((t["categoria"], t["corrigida"]), ("Mercado", False))

    def test_filtros_valem_para_os_totais(self):
        dados = self.pedir("GET", "/extrato?tipo=entradas")[1]
        self.assertEqual((dados["saidas"], dados["transacoes"]), (0, []))
        self.assertEqual(self.pedir("GET", "/extrato?minimo=50,00")[1]["saidas"], 80)
        self.assertEqual(self.pedir("GET", "/extrato?maximo=50")[1]["transacoes"], [])

    def test_categoria_muda_totais_mas_nao_a_lista(self):
        with mock.patch.object(servidor.historico, "carregar", return_value=[
                {**transacao("1", date.today().isoformat(), -80), "categoria": "A", "interno": False},
                {**transacao("2", date.today().isoformat(), -20, "Bar"), "categoria": "B", "interno": False},
        ]), mock.patch.object(servidor.fin, "aplicar_regras"):
            dados = self.pedir("GET", "/extrato?categoria=B")[1]
        self.assertEqual((dados["saidas"], dados["total_categorias"]), (20, 100))
        self.assertEqual(len(dados["por_categoria"]), 2)
        self.assertEqual(dados["categorias_disponiveis"], ["A", "B"])

    def test_minimo_zero_e_aceito(self):
        self.assertEqual(self.pedir("GET", "/extrato?minimo=0")[0], 200)

    def test_pedido_que_nao_e_objeto_recebe_resposta(self):
        self.assertEqual(self.pedir("POST", "/limite", [])[0], 400)

    def test_erro_inesperado_recebe_resposta(self):
        with mock.patch.object(servidor.historico, "carregar", side_effect=RuntimeError("x")), \
             mock.patch("traceback.print_exc"):
            status, dados = self.pedir("GET", "/painel")
        self.assertEqual(status, 500)
        self.assertIn("erro", dados)

    def test_regras_com_formato_errado_nao_derrubam(self):
        with open(servidor.ARQUIVO_REGRAS, "w", encoding="utf-8") as arquivo:
            arquivo.write("[]")
        self.assertEqual(self.pedir("GET", "/painel")[0], 200)
        self.assertTrue(os.path.exists(f"{servidor.ARQUIVO_REGRAS}.estragado"))

    def test_porta_ocupada_pelo_proprio_finan_abre_navegador(self):
        with mock.patch.object(servidor, "finan_em_execucao",
                               return_value={"pasta": str(servidor.PASTA)}), \
             mock.patch.object(servidor.webbrowser, "open") as abrir, mock.patch("builtins.print"):
            self.assertEqual(servidor.porta_ocupada(), 0)
        abrir.assert_called_once()

    def test_porta_ocupada_por_outra_pasta_avisa(self):
        with mock.patch.object(servidor, "finan_em_execucao", return_value={"pasta": "C:/outra"}), \
             mock.patch.object(servidor.webbrowser, "open") as abrir, \
             mock.patch("builtins.print") as mostrar:
            self.assertEqual(servidor.porta_ocupada(), 1)
        abrir.assert_not_called()
        self.assertIn("C:/outra", mostrar.call_args[0][0])

    def test_filtro_invalido_e_recusado(self):
        self.assertEqual(self.pedir("GET", "/extrato?tipo=xyz")[0], 400)
        self.assertEqual(self.pedir("GET", "/extrato?minimo=abc")[0], 400)

    def test_limite_invalido_e_recusado(self):
        status, dados = self.pedir("POST", "/limite", {"categoria": "Mercado", "valor": "abc"})
        self.assertEqual(status, 400)
        self.assertIn("erro", dados)

    def test_recusa_site_externo(self):
        status, _ = self.pedir("POST", "/limite", {"categoria": "M", "valor": "1"},
                               {"Origin": "https://exemplo.com"})
        self.assertEqual(status, 403)
        self.assertEqual(self.pedir("GET", "/painel", cabecalhos={"Host": "exemplo.com"})[0], 403)

    def test_recusa_formulario_sem_json(self):
        status, _ = self.pedir("POST", "/limite", {}, {"Content-Type": "text/plain"})
        self.assertEqual(status, 403)

    def test_exporta_planilha(self):
        status, conteudo = self.pedir("GET", "/exportar")
        self.assertEqual(status, 200)
        self.assertEqual(conteudo[:2], b"PK")

    def test_atualizar_sem_configuracao(self):
        with mock.patch.object(servidor, "CLIENT_ID", ""):
            self.assertEqual(self.pedir("POST", "/atualizar", {})[0], 400)


if __name__ == "__main__":
    unittest.main()
