import { useEffect, useState } from 'react';
import {
  Alert,
  Box,
  CircularProgress,
  MenuItem,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
} from '@mui/material';
import PageContainer from 'src/components/container/PageContainer';
import AnaliseComparacao from '../components/AnaliseComparacao';
import GraficosComparacao from '../components/GraficosComparacao';
import IndicadoresComparacao from '../components/IndicadoresComparacao';
import { Indicadores, Vazio } from '../components/Visual';
import { useFinan } from '../hooks/useFinan';
import { compararMeses } from '../services/api';
import { nomeMes, variacao } from '../services/formato';
import { ComparacaoMeses, ValorComparado } from '../types';

type Visao = 'graficos' | 'indicadores' | 'analise';

const VISOES: { valor: Visao; rotulo: string }[] = [
  { valor: 'graficos', rotulo: 'Gráficos' },
  { valor: 'indicadores', rotulo: 'Indicadores' },
  { valor: 'analise', rotulo: 'Análise IA' },
];

const SeletorMes = ({
  rotulo,
  valor,
  outro,
  meses,
  aoMudar,
}: {
  rotulo: string;
  valor: string;
  outro: string;
  meses: string[];
  aoMudar: (mes: string) => void;
}) => (
  <TextField
    select
    size="small"
    label={rotulo}
    value={valor}
    onChange={(e) => aoMudar(e.target.value)}
    sx={{ flex: { xs: 1, sm: '0 0 180px' } }}
  >
    {meses.map((mes) => (
      <MenuItem key={mes} value={mes} disabled={mes === outro}>
        {nomeMes(mes)}
      </MenuItem>
    ))}
  </TextField>
);

const Comparacao = () => {
  const { painel, moeda, diferenca, versao } = useFinan();
  const meses = painel?.mensal.map((m) => m.mes) ?? [];
  // Sem escolha do usuário segue os meses mais novos, que podem chegar depois de abrir a página.
  const [escolhaPrimeiro, setPrimeiro] = useState('');
  const [escolhaSegundo, setSegundo] = useState('');
  const segundo = escolhaSegundo || (meses[0] ?? '');
  const primeiro = escolhaPrimeiro || (meses.find((m) => m !== segundo) ?? '');
  const [visao, setVisao] = useState<Visao>('graficos');
  const [resposta, setResposta] = useState<ComparacaoMeses | null>(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    if (!primeiro || !segundo) return undefined;
    let valida = true; // trocar de mês rápido não deixa a resposta antiga sobrescrever a nova
    setErro('');
    compararMeses(primeiro, segundo)
      .then((nova) => {
        if (valida) setResposta(nova);
      })
      .catch((e: Error) => valida && setErro(e.message));
    return () => {
      valida = false;
    };
  }, [primeiro, segundo, versao]);

  if (meses.length < 2) {
    return (
      <PageContainer title="Comparação · Finan">
        <Vazio texto="A comparação precisa de pelo menos dois meses com movimentações." />
      </PageContainer>
    );
  }

  // Só mostra números do par selecionado, mesmo que a consulta nova falhe.
  const dados = resposta?.primeiro === primeiro && resposta.segundo === segundo ? resposta : null;
  const tile = (titulo: string, linha: ValorComparado) => ({
    titulo: `${titulo} em ${nomeMes(segundo)}`,
    valor: moeda(linha.b),
    detalhe: `${diferenca(linha.diferenca)} (${variacao(linha)}) sobre ${nomeMes(primeiro)}`,
  });
  const parcial = dados?.em_andamento;

  return (
    <PageContainer title="Comparação · Finan">
      <Stack spacing={3}>
        <Stack direction="row" spacing={2} alignItems="center">
          <SeletorMes
            rotulo="Primeiro mês"
            valor={primeiro}
            outro={segundo}
            meses={meses}
            aoMudar={setPrimeiro}
          />
          <SeletorMes
            rotulo="Segundo mês"
            valor={segundo}
            outro={primeiro}
            meses={meses}
            aoMudar={setSegundo}
          />
        </Stack>
        {erro && <Alert severity="error">{erro}</Alert>}
        {!dados && !erro && (
          <Box textAlign="center" py={6}>
            <CircularProgress />
          </Box>
        )}
        {dados && (
          <>
            {parcial && (
              <Alert severity="info">
                {nomeMes(parcial.mes)} ainda está em andamento (dia {parcial.dia} de{' '}
                {parcial.dias_no_mes}), então a comparação é com um mês incompleto. Até o dia{' '}
                {parcial.dia}, as despesas foram {moeda(parcial.despesas)} em {nomeMes(parcial.mes)}{' '}
                e {moeda(parcial.despesas_outro)} em {nomeMes(parcial.outro)}.
              </Alert>
            )}
            <Indicadores
              itens={[
                tile('Receitas', dados.resumo.receitas),
                tile('Despesas', dados.resumo.despesas),
                tile('Saldo', dados.resumo.saldo),
              ]}
            />
            <ToggleButtonGroup
              exclusive
              fullWidth
              color="primary"
              size="small"
              value={visao}
              onChange={(_, nova: Visao | null) => nova && setVisao(nova)}
              aria-label="Visualização da comparação"
              sx={{ maxWidth: 480 }}
            >
              {VISOES.map((v) => (
                <ToggleButton key={v.valor} value={v.valor} sx={{ textTransform: 'none' }}>
                  {v.rotulo}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
            {visao === 'graficos' && <GraficosComparacao dados={dados} />}
            {visao === 'indicadores' && <IndicadoresComparacao dados={dados} />}
            {visao === 'analise' && <AnaliseComparacao dados={dados} />}
          </>
        )}
      </Stack>
    </PageContainer>
  );
};

export default Comparacao;
