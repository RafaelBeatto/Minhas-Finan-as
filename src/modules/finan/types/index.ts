export type EstadoOrcamento = 'ok' | 'atencao' | 'estourou' | 'sem limite';

export interface Conta {
  id: string;
  nome: string;
  cartao: boolean;
  saldo: number;
}

export interface Investimento {
  id: string;
  nome: string;
  tipo: string;
  saldo: number;
  data: string | null;
}

export interface PeriodoRendimento {
  rotulo: string;
  de: string;
  ate: string;
  saldo_inicial: number;
  saldo_final: number;
  aportes: number;
  rendimento: number;
  percentual: number | null;
  parcial: boolean;
  variacao: number | null;
}

export interface Rendimento {
  semanas: PeriodoRendimento[];
  meses: PeriodoRendimento[];
  desde: string | null;
  tem_aportes: boolean;
}

export interface ResumoCartao {
  fatura: number;
  limite: number;
  disponivel: number;
  usado: number;
  vencimento: string | null;
  minimo: number | null;
}

export interface Fatura {
  vencimento: string | null;
  fechamento: string | null;
  total: number;
  minimo: number | null;
  encargos: number;
}

export interface Mes {
  mes: string;
  entradas: number;
  saidas: number;
  resultado: number;
  variacao: number | null;
}

export interface LinhaOrcamento {
  categoria: string;
  limite: number | null;
  gasto: number;
  restante: number | null;
  uso: number | null;
  media: number;
  estado: EstadoOrcamento;
}

export interface Assinatura {
  chave: string;
  descricao: string;
  categoria: string;
  conta: string;
  valor: number;
  meses: number;
  ultima: string;
  proxima: string;
  ativa: boolean;
  aumento: number;
}

export interface Parcela {
  descricao: string;
  parcela: number;
  total: number;
  valor: number;
  meses: string[];
  restante: number;
  fim: string;
}

export interface Painel {
  hoje: string;
  configurado: boolean;
  atualizado_em: string | null;
  banco_lido_em: string | null;
  proxima_leitura: string | null;
  tem_contas: boolean;
  em_conta: number;
  fatura: number;
  contas: Conta[];
  investimentos: Investimento[];
  investimentos_encerrados: number;
  investido: number;
  investimentos_status: 'ok' | 'vazio' | 'falhou' | null;
  rendimento: Rendimento;
  cartao: ResumoCartao;
  faturas: Fatura[];
  mensal: Mes[];
  orcamento: LinhaOrcamento[];
  alerta: string;
  assinaturas: Assinatura[];
  custo_assinaturas: number;
  ignoradas: number;
  parcelas: Parcela[];
  compromisso: { mes: string; valor: number }[];
  previsao: { gasto: number; projecao: number | null; media: number };
  proximo_mes: { mes: string; parcelas: number; assinaturas: number; total: number };
  nomes_contas: string[];
  categorias: string[];
  periodos: string[];
}

export interface Transacao {
  id: string;
  data: string;
  descricao: string;
  conta: string;
  categoria: string;
  valor: number;
  interno: boolean;
  pendente: boolean;
  parcela: number;
  parcelas_total: number;
  corrigida: boolean;
}

export interface Extrato {
  entradas: number;
  saidas: number;
  resultado: number;
  total_categorias: number;
  categorias_disponiveis: string[];
  por_categoria: { categoria: string; total: number }[];
  transacoes: Transacao[];
}

export interface FiltrosExtrato {
  periodo: string;
  conta?: string;
  categoria?: string;
  busca?: string;
  de?: string;
  tipo?: string;
  situacao?: string;
  minimo?: string;
  maximo?: string;
  sem_internas?: string;
  ate?: string;
}

export interface Comparacao {
  mes: string;
  anterior: string;
  linhas: { categoria: string; atual: number; anterior: number; diferenca: number }[];
}

export interface ValorComparado {
  a: number;
  b: number;
  diferenca: number;
  percentual: number | null;
  rotulo: string | null;
}

export type SituacaoCategoria =
  'Aumentou' | 'Diminuiu' | 'Permaneceu igual' | 'Nova categoria' | 'Sem movimentação';

export interface CategoriaComparada extends ValorComparado {
  categoria: string;
  situacao: SituacaoCategoria;
  ultimo_outro_mes: string | null;
}

export type TipoEvidencia = 'confirmado' | 'padrao' | 'tendencia' | 'estimativa' | 'insuficiente';

export interface ItemAnalise {
  tipo: TipoEvidencia;
  titulo: string;
  texto: string;
  motivo?: string;
}

export interface Alerta {
  titulo: string;
  texto: string;
  motivo: string;
}

export interface ItemTendencia extends ItemAnalise {
  direcao: 'alta' | 'queda';
  favoravel: boolean;
}

export interface Descoberta {
  tipo: TipoEvidencia;
  titulo: string;
  explicacao: string;
  valores: { rotulo: string; texto: string }[];
  periodo: string;
  motivo: string;
}

export interface AnaliseFinanceira {
  base: { meses_fechados: number; despesas: number; periodo: string };
  leitura: string[];
  destaques: ItemAnalise[];
  alertas: Alerta[];
  padroes: ItemAnalise[];
  tendencias: {
    meses: number;
    geral: ItemTendencia[];
    alta: ItemTendencia[];
    queda: ItemTendencia[];
    estaveis: { categoria: string; media: number }[];
  };
  previsoes: ItemAnalise[];
  descobertas: Descoberta[];
  limitacoes: { tipo: TipoEvidencia; texto: string }[];
}

export interface ComparacaoMeses {
  primeiro: string;
  segundo: string;
  resumo: { receitas: ValorComparado; despesas: ValorComparado; saldo: ValorComparado };
  categorias: CategoriaComparada[];
  aumentos: CategoriaComparada[];
  reducoes: CategoriaComparada[];
  um_periodo: {
    categoria: string;
    tipo: 'nova' | 'retomada' | 'so_primeiro';
    valor: number;
    ultimo_outro_mes: string | null;
  }[];
  evolucao: { mes: string; saidas: number }[];
  em_andamento: {
    mes: string;
    outro: string;
    dia: number;
    dias_no_mes: number;
    receitas: number;
    despesas: number;
    receitas_outro: number;
    despesas_outro: number;
  } | null;
  analise: AnaliseFinanceira;
}

export interface LinhaCategoria {
  categoria: string;
  gastos: number;
  entradas: number;
  lancamentos: number;
  fatia: number;
  limite: number | null;
  personalizada: boolean;
  em_uso: boolean;
  principais: { descricao: string; quantidade: number; total: number }[];
}

export interface RegraSalva {
  tipo: 'descricao' | 'transacao' | 'faixa';
  chave: string;
  categoria: string;
  descricao: string;
  lancamentos: number;
  minimo: number | null;
}

export interface PainelCategorias {
  periodo: string;
  total_gastos: number;
  linhas: LinhaCategoria[];
  regras: RegraSalva[];
  renomeadas: { origem: string; destino: string }[];
}
