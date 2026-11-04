# Finan

Módulo financeiro do sistema, em `/finan`. Somente leitura: não movimenta dinheiro.

## Como abrir

- Uso normal: rode `npm run build` uma vez e dê dois cliques em `Iniciar-Finan.bat`.
  O endereço é http://127.0.0.1:8766/finan.
- Desenvolvimento: rode `python servidor.py` nesta pasta e `npm run dev` na raiz.

## Como está dividido

- `src/modules/finan`: interface. Não usa o store nem os dados do resto do sistema.
- `finan-servidor`: servidor local em Python, com as regras (`financeiro.py`), o banco
  (`historico.py`), a Pluggy (`pluggy.py`), a planilha (`exportar.py`), a comparação entre
  dois meses (`comparativo.py`), a análise da aba Comparação (`inteligencia.py`) e a gestão
  de categorias (`categorias.py`).
- A análise roda só neste computador, com estatística e regras: não usa serviço externo e
  não grava nada. Os limites de evidência são as constantes no topo de `inteligencia.py`.
- A Client Secret fica só no servidor, porque a Pluggy não pode ser chamada do navegador.
- Fora da pasta do módulo, o sistema mudou em quatro pontos: `Router.tsx` (uma rota),
  `MenuItems.ts` (um item), `vite.config.ts` (proxy da API) e `.gitignore`.

## Dados

- Tudo fica em `finan-servidor/dados`: `.env`, `historico.db`, `regras.json`, `orcamento.json`,
  `assinaturas.json` e `categorias.json`. Essa pasta fica fora do Git.
- Copie essa pasta se trocar de computador. Só envie a quem pode ver seu extrato completo.

## Testes

Nesta pasta, com o Windows PowerShell:

```
$env:PYTHONPATH = "."; python -m unittest discover -s testes -t testes
```
