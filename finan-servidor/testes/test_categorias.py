import unittest
from datetime import date
import categorias as cat
import financeiro as fin

HOJE = date(2026, 10, 20)


def tx(id_, categoria, valor=-10, descricao="Loja", data="2026-10-05"):
    return {"id": id_, "conta": "Conta", "data": data, "descricao": descricao,
            "chave": fin.chave_regra(descricao), "categoria_original": categoria,
            "categoria": categoria, "valor": valor, "interno": categoria == fin.INTERNO,
            "interno_original": categoria == fin.INTERNO, "pendente": False, "parcela": 0,
            "parcelas_total": 0, "data_compra": "", "mes_fatura": ""}


def linha(resultado, nome):
    return next(l for l in resultado["linhas"] if l["categoria"] == nome)


class Renomeadas(unittest.TestCase):
    def test_vale_para_a_categoria_original(self):
        t = [tx("1", "Compras")]
        regras = {**fin.regras_vazias(), "renomeadas": {"Compras": "Casa"}}
        fin.aplicar_regras(t, regras)
        self.assertEqual(t[0]["categoria"], "Casa")

    def test_vale_para_regra_e_nao_marca_como_corrigida(self):
        t = [tx("1", "Compras"), tx("2", "Lazer", descricao="Bar")]
        regras = {**fin.regras_vazias(), "renomeadas": {"Compras": "Casa"},
                  "descricoes": {"bar": "Compras"}}
        fin.aplicar_regras(t, regras)
        self.assertEqual(t[1]["categoria"], "Casa")
        self.assertEqual(t[0]["categoria"], t[0]["categoria_original"])

    def test_arquivo_antigo_sem_renomeadas(self):
        t = [tx("1", "Compras")]
        fin.aplicar_regras(t, {"transacoes": {}, "faixas": {}, "descricoes": {}})
        self.assertEqual(t[0]["categoria"], "Compras")


class Renomear(unittest.TestCase):
    def setUp(self):
        self.t = [tx("1", "Compras"), tx("2", "Lazer", -30)]
        self.regras = fin.regras_vazias()
        self.orcamento = {"Compras": 100}
        self.criadas = []

    def renomear(self, origem, destino):
        cat.renomear(self.t, self.regras, self.orcamento, self.criadas, origem, destino)

    def test_nao_altera_as_transacoes(self):
        self.renomear("Compras", "Casa")
        self.assertEqual(self.t[0]["categoria_original"], "Compras")
        self.assertEqual(self.regras["renomeadas"], {"Compras": "Casa"})

    def test_limite_acompanha(self):
        self.renomear("Compras", "Casa")
        self.assertEqual(self.orcamento, {"Casa": 100})

    def test_juntar_mantem_o_limite_do_destino(self):
        self.orcamento["Lazer"] = 50
        self.renomear("Compras", "Lazer")
        self.assertEqual(self.orcamento, {"Lazer": 50})

    def test_encadeia_sem_perder_o_destino(self):
        self.regras["renomeadas"]["Velha"] = "Compras"
        self.renomear("Compras", "Casa")
        self.assertEqual(self.regras["renomeadas"], {"Velha": "Casa", "Compras": "Casa"})

    def test_voltar_ao_nome_antigo_nao_cria_laco(self):
        self.regras["renomeadas"]["Lazer"] = "Compras"
        self.renomear("Compras", "Lazer")
        self.assertEqual(self.regras["renomeadas"], {"Compras": "Lazer"})

    def test_recusa_nome_do_sistema(self):
        for destino in (fin.INTERNO, fin.SEM_CATEGORIA, "", "   ", "x" * 41):
            with self.assertRaises(ValueError):
                self.renomear("Compras", destino)

    def test_recusa_origem_interna_ou_inexistente(self):
        self.t.append(tx("3", fin.INTERNO))
        for origem in (fin.INTERNO, "Nada"):
            with self.assertRaises(ValueError):
                self.renomear(origem, "Casa")

    def test_recusa_mesmo_nome(self):
        with self.assertRaises(ValueError):
            self.renomear("Compras", "Compras")

    def test_criada_sem_uso_so_troca_o_nome(self):
        self.criadas.append("Pets")
        self.renomear("Pets", "Animais")
        self.assertEqual(self.criadas, ["Animais"])
        self.assertEqual(self.regras["renomeadas"], {})


class Excluir(unittest.TestCase):
    def setUp(self):
        self.t = [tx("1", "Compras")]
        self.regras = fin.regras_vazias()
        self.criadas = ["Pets", "Compras"]
        self.orcamento = {"Pets": 10}

    def test_exclui_criada_sem_uso(self):
        cat.excluir(self.t, self.regras, self.orcamento, self.criadas, "Pets")
        self.assertEqual((self.criadas, self.orcamento), (["Compras"], {}))

    def test_recusa_com_lancamentos(self):
        with self.assertRaises(ValueError):
            cat.excluir(self.t, self.regras, self.orcamento, self.criadas, "Compras")

    def test_recusa_com_regra(self):
        self.regras["descricoes"]["x"] = "Pets"
        with self.assertRaises(ValueError):
            cat.excluir(self.t, self.regras, self.orcamento, self.criadas, "Pets")

    def test_recusa_categoria_que_nao_foi_criada(self):
        with self.assertRaises(ValueError):
            cat.excluir(self.t, self.regras, self.orcamento, [], "Compras")


class Visao(unittest.TestCase):
    def visao(self, t, regras=None, criadas=(), periodo="Este mês"):
        return cat.visao(t, regras or fin.regras_vazias(), {"Lazer": 80}, list(criadas), periodo, HOJE)

    def test_soma_e_fatia_do_periodo(self):
        r = self.visao([tx("1", "Lazer", -30), tx("2", "Lazer", -10, "Bar"), tx("3", "Mercado", -60),
                        tx("4", "Lazer", -999, data="2026-01-05")])
        l = linha(r, "Lazer")
        self.assertEqual((l["gastos"], l["fatia"], l["lancamentos"], l["limite"]), (40, .4, 2, 80))
        self.assertEqual(r["total_gastos"], 100)
        self.assertEqual(l["principais"][0]["total"], 30)

    def test_nao_mistura_entrada_com_gasto(self):
        l = linha(self.visao([tx("1", "Lazer", -30), tx("2", "Lazer", 500)]), "Lazer")
        self.assertEqual((l["gastos"], l["entradas"]), (30, 500))

    def test_interna_fica_de_fora(self):
        r = self.visao([tx("1", fin.INTERNO, -900), tx("2", "Lazer", -10)])
        self.assertEqual([l["categoria"] for l in r["linhas"]], ["Lazer"])
        self.assertEqual(r["total_gastos"], 10)

    def test_categoria_sem_movimento_no_periodo_aparece(self):
        r = self.visao([tx("1", "Viagem", data="2026-01-05")], criadas=["Pets"])
        self.assertEqual({l["categoria"]: l["gastos"] for l in r["linhas"]}, {"Viagem": 0, "Pets": 0})

    def test_personalizada(self):
        t = [tx("1", "Lazer", descricao="Bar"), tx("2", "Mercado")]
        regras = {**fin.regras_vazias(), "descricoes": {"bar": "Bebidas"}}
        fin.aplicar_regras(t, regras)
        r = self.visao(t, regras)
        self.assertTrue(linha(r, "Bebidas")["personalizada"])
        self.assertFalse(linha(r, "Mercado")["personalizada"])

    def test_lista_regras_com_nome_atual(self):
        t = [tx("1", "Lazer", descricao="Bar 1"), tx("2", "Lazer", descricao="Bar 2")]
        regras = {**fin.regras_vazias(), "descricoes": {"bar": "Antiga"},
                  "renomeadas": {"Antiga": "Nova"}, "transacoes": {"sumiu": "Lazer"},
                  "faixas": {"pix": {"minimo": 1000, "categoria": "Salário"}}}
        por_tipo = {r["tipo"]: r for r in self.visao(t, regras)["regras"]}
        self.assertEqual((por_tipo["descricao"]["categoria"], por_tipo["descricao"]["lancamentos"]),
                         ("Nova", 2))
        self.assertEqual(por_tipo["transacao"]["descricao"], "Transação não encontrada")
        self.assertEqual(por_tipo["faixa"]["minimo"], 1000)


class RemoverRegra(unittest.TestCase):
    def test_remove_so_a_regra_pedida(self):
        regras = {**fin.regras_vazias(), "descricoes": {"a": "X", "b": "Y"}}
        cat.remover_regra_salva(regras, "descricao", "a")
        self.assertEqual(regras["descricoes"], {"b": "Y"})

    def test_recusa_tipo_ou_chave_invalidos(self):
        for tipo, chave in (("renomeadas", "a"), ("descricao", "nada")):
            with self.assertRaises(ValueError):
                cat.remover_regra_salva(fin.regras_vazias(), tipo, chave)


if __name__ == "__main__":
    unittest.main()
