import {
  Comparacao,
  ComparacaoMeses,
  Extrato,
  FiltrosExtrato,
  Painel,
  PainelCategorias,
} from '../types';

const BASE = '/api/finan';
const DESLIGADO =
  'O servidor do Finan está desligado. Dê dois cliques em Iniciar-Finan.bat e tente de novo.';

// Modo nuvem (app Android): o servidor exige um token, guardado no aparelho.
const CHAVE_TOKEN = 'finan_token';

function lerToken(): string {
  try {
    return localStorage.getItem(CHAVE_TOKEN) ?? '';
  } catch {
    return '';
  }
}

function pedirToken(): string {
  const digitado = window.prompt('Digite o código de acesso do Finan:') ?? '';
  try {
    if (digitado) localStorage.setItem(CHAVE_TOKEN, digitado);
  } catch {
    /* sem armazenamento: o código vale só nesta sessão */
  }
  return digitado;
}

let tokenEmUso = lerToken();

async function executar(caminho: string, opcoes: RequestInit): Promise<Response> {
  const cabecalhos = new Headers(opcoes.headers);
  if (tokenEmUso) cabecalhos.set('Authorization', `Bearer ${tokenEmUso}`);
  return fetch(`${BASE}${caminho}`, { ...opcoes, headers: cabecalhos });
}

async function pedir<T>(caminho: string, opcoes: RequestInit = {}): Promise<T> {
  let resposta: Response;
  try {
    resposta = await executar(caminho, opcoes);
    if (resposta.status === 401) {
      tokenEmUso = pedirToken();
      if (!tokenEmUso) throw new Error('Código de acesso necessário.');
      resposta = await executar(caminho, opcoes);
    }
  } catch (erro) {
    if (erro instanceof Error && erro.message.startsWith('Código')) throw erro;
    throw new Error(DESLIGADO);
  }
  const dados = await resposta.json().catch(() => null);
  if (!resposta.ok) throw new Error(dados?.erro ?? DESLIGADO);
  return dados as T;
}

function enviar<T>(caminho: string, corpo: unknown = {}) {
  return pedir<T>(caminho, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(corpo),
  });
}

const consulta = (filtros: object) => {
  const parametros = new URLSearchParams();
  Object.entries(filtros).forEach(([chave, valor]) => {
    if (valor) parametros.set(chave, String(valor));
  });
  return parametros.toString();
};

export const buscarPainel = () => pedir<Painel>('/painel');
export const buscarExtrato = (filtros: FiltrosExtrato) =>
  pedir<Extrato>(`/extrato?${consulta(filtros)}`);
export const buscarComparacao = (mes: string) => pedir<Comparacao>(`/comparacao?mes=${mes}`);
export const compararMeses = (primeiro: string, segundo: string) =>
  pedir<ComparacaoMeses>(`/comparar?${consulta({ primeiro, segundo })}`);
export const atualizarDados = () => enviar<{ aviso: string | null }>('/atualizar');
export const salvarRegra = (id: string, categoria: string, todas: boolean) =>
  enviar('/regra', { id, categoria, todas });
export const removerRegra = (id: string) => enviar('/regra/remover', { id });
export const salvarLimite = (categoria: string, valor: string) =>
  enviar('/limite', { categoria, valor });
export const ignorarAssinatura = (chave: string) => enviar('/assinaturas/ignorar', { chave });
export const restaurarAssinaturas = () => enviar('/assinaturas/restaurar');
export const buscarCategorias = (periodo: string) =>
  pedir<PainelCategorias>(`/categorias?${consulta({ periodo })}`);
export const criarCategoria = (nome: string) => enviar('/categorias/criar', { nome });
export const renomearCategoria = (origem: string, destino: string) =>
  enviar('/categorias/renomear', { origem, destino });
export const excluirCategoria = (nome: string) => enviar('/categorias/excluir', { nome });
export const desfazerRenomeacao = (origem: string) => enviar('/categorias/desfazer', { origem });
export const removerRegraSalva = (tipo: string, chave: string) =>
  enviar('/categorias/regra/remover', { tipo, chave });
export const ENDERECO_PLANILHA = `${BASE}/exportar`;
