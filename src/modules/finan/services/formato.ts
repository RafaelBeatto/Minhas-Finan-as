import dayjs from 'dayjs';

const MESES = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun', 'jul', 'ago', 'set', 'out', 'nov', 'dez'];
const REAIS = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' });

export const brl = (valor: number) => REAIS.format(valor);
export const porcento = (valor: number) => `${Math.round(valor * 100)}%`;
export const dataBr = (data?: string | null) => (data ? dayjs(data).format('DD/MM/YYYY') : '—');
export const dataHoraBr = (data: string) => dayjs(data).format('DD/MM/YYYY [às] HH:mm');

/** Para comparar textos digitados: "saude" encontra "Saúde". */
export const semAcento = (texto: string) =>
  texto
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase();

export const nomeMes = (mes: string) => {
  const [ano, numero] = mes.split('-');
  return `${MESES[Number(numero) - 1]}/${ano}`;
};

/** Texto curto para o eixo dos gráficos: R$ 12 mil. */
export const brlCurto = (valor: number) =>
  Math.abs(valor) >= 1000 ? `R$ ${Math.round(valor / 1000)} mil` : `R$ ${Math.round(valor)}`;
