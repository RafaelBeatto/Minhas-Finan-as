import { Comparacao, Extrato, FiltrosExtrato, Painel } from '../types';

const BASE = '/api/finan';
const DESLIGADO =
  'O servidor do Finan está desligado. Dê dois cliques em Iniciar-Finan.bat e tente de novo.';

async function pedir<T>(caminho: string, opcoes?: RequestInit): Promise<T> {
  let resposta: Response;
  try {
    resposta = await fetch(`${BASE}${caminho}`, opcoes);
  } catch {
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
export const atualizarDados = () => enviar<{ aviso: string | null }>('/atualizar');
export const salvarRegra = (id: string, categoria: string, todas: boolean) =>
  enviar('/regra', { id, categoria, todas });
export const removerRegra = (id: string) => enviar('/regra/remover', { id });
export const salvarLimite = (categoria: string, valor: string) =>
  enviar('/limite', { categoria, valor });
export const ignorarAssinatura = (chave: string) => enviar('/assinaturas/ignorar', { chave });
export const restaurarAssinaturas = () => enviar('/assinaturas/restaurar');
export const ENDERECO_PLANILHA = `${BASE}/exportar`;
