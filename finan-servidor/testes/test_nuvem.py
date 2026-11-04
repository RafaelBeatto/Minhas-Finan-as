"""Modo nuvem: com FINAN_TOKEN, a API exige o token e a página do app fica pública."""
import threading
import unittest
from functools import partial
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import servidor

TOKEN = "segredo-de-teste"


class ModoNuvem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.patches = [
            mock.patch.object(servidor, "NUVEM", True),
            mock.patch.object(servidor, "TOKEN", TOKEN),
        ]
        for p in cls.patches:
            p.start()
        cls.servidor = servidor.Servidor(
            ("127.0.0.1", 0), partial(servidor.Manipulador, directory=str(servidor.DIST)))
        cls.base = f"http://127.0.0.1:{cls.servidor.server_address[1]}"
        threading.Thread(target=cls.servidor.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.servidor.shutdown()
        cls.servidor.server_close()
        for p in cls.patches:
            p.stop()

    def pedir(self, caminho, cabecalhos=None, corpo=None):
        dados = None
        cabecalhos = dict(cabecalhos or {})
        if corpo is not None:
            import json
            dados = json.dumps(corpo).encode()
            cabecalhos["Content-Type"] = "application/json"
        req = Request(self.base + caminho, data=dados, headers=cabecalhos,
                      method="POST" if dados is not None else "GET")
        try:
            with urlopen(req, timeout=5) as r:
                return r.status
        except HTTPError as e:
            return e.code

    def test_api_sem_token_recusa(self):
        self.assertEqual(self.pedir("/api/finan/servidor"), 401)

    def test_api_com_token_errado_recusa(self):
        self.assertEqual(
            self.pedir("/api/finan/servidor", {"Authorization": "Bearer errado"}), 401)

    def test_api_com_token_certo_responde(self):
        self.assertEqual(
            self.pedir("/api/finan/servidor", {"Authorization": f"Bearer {TOKEN}"}), 200)

    def test_escrita_sem_token_recusa(self):
        self.assertEqual(self.pedir("/api/finan/atualizar", corpo={}), 401)

    def test_pagina_do_app_e_publica(self):
        self.assertIn(self.pedir("/finan"), (200, 404))
        self.assertNotEqual(self.pedir("/finan"), 401)


if __name__ == "__main__":
    unittest.main()
