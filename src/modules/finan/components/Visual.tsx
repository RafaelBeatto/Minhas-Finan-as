import { ReactNode } from 'react';
import {
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  LinearProgress,
  Stack,
  Typography,
} from '@mui/material';
import { useTheme } from '@mui/material/styles';
import { ApexOptions } from 'apexcharts';
import Chart from 'react-apexcharts';
import { EstadoOrcamento } from '../types';
import { brlCurto, brlEixo } from '../services/formato';
import { useFinan } from '../hooks/useFinan';

export interface ItemIndicador {
  titulo: string;
  valor: string | number;
  detalhe?: string;
}

/** Linha de indicadores: número grande, um rótulo e, se houver, o contexto dele. */
export const Indicadores = ({ itens }: { itens: ItemIndicador[] }) => (
  <Box>
    <Grid container spacing={3}>
      {itens.map(({ titulo, valor, detalhe }) => (
        <Grid item xs={12} sm={itens.length % 2 ? 4 : 6} lg={12 / itens.length} key={titulo}>
          <Card variant="outlined" sx={{ p: 0, height: '100%' }}>
            <CardContent sx={{ p: 3 }}>
              <Typography variant="subtitle2" color="text.secondary">
                {titulo}
              </Typography>
              <Typography variant="h4" fontWeight={600} mt={1} noWrap>
                {valor}
              </Typography>
              {detalhe && (
                <Typography variant="caption" color="text.secondary">
                  {detalhe}
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      ))}
    </Grid>
  </Box>
);

const ESTADOS: Record<
  EstadoOrcamento,
  { rotulo: string; cor: 'success' | 'warning' | 'error' | 'default' }
> = {
  ok: { rotulo: 'Dentro do limite', cor: 'success' },
  atencao: { rotulo: 'Atenção', cor: 'warning' },
  estourou: { rotulo: 'Estourou', cor: 'error' },
  'sem limite': { rotulo: 'Sem limite', cor: 'default' },
};

export const EtiquetaEstado = ({ estado }: { estado: EstadoOrcamento }) => (
  <Chip
    size="small"
    variant="outlined"
    label={ESTADOS[estado].rotulo}
    color={ESTADOS[estado].cor}
  />
);

export const BarraUso = ({ uso, cor }: { uso: number; cor?: 'primary' | 'warning' | 'error' }) => (
  <LinearProgress
    variant="determinate"
    value={Math.min(uso * 100, 100)}
    color={cor ?? 'primary'}
    sx={{ height: 6, borderRadius: 3 }}
  />
);

export const Vazio = ({ texto }: { texto: string }) => (
  <Box py={4} textAlign="center">
    <Typography color="text.secondary">{texto}</Typography>
  </Box>
);

export const Secao = ({
  titulo,
  subtitulo,
  acao,
  children,
}: {
  titulo: string;
  subtitulo?: string;
  acao?: ReactNode;
  children: ReactNode;
}) => (
  <Card variant="outlined" sx={{ p: 0, height: '100%' }}>
    <CardContent sx={{ p: 3 }}>
      <Stack
        direction="row"
        flexWrap="wrap"
        justifyContent="space-between"
        alignItems="center"
        gap={2}
        mb={2}
      >
        <Box flex="1 1 220px" minWidth={0}>
          <Typography variant="h5">{titulo}</Typography>
          {subtitulo && (
            <Typography variant="subtitle2" color="text.secondary">
              {subtitulo}
            </Typography>
          )}
        </Box>
        {acao}
      </Stack>
      {children}
    </CardContent>
  </Card>
);

interface Serie {
  name: string;
  data: number[];
}

/** Cores validadas para daltonismo, em par claro/escuro: azul e laranja. */
const CORES = { light: ['#2a78d6', '#d95f02'], dark: ['#3987e5', '#e0702a'] };
const COR_NEUTRA = { light: '#c3cbd4', dark: '#4d5863' };

export const GraficoBarras = ({
  rotulos,
  series,
  formatar,
  altura = 300,
  horizontal = false,
  coresPontos,
}: {
  rotulos: string[];
  series: Serie[];
  formatar: (valor: number) => string;
  altura?: number;
  horizontal?: boolean;
  /** Com uma série só, pinta cada barra: 0 azul, 1 laranja, null neutra. */
  coresPontos?: (0 | 1 | null)[];
}) => {
  const theme = useTheme();
  const { ocultar } = useFinan();
  const modo = theme.palette.mode;
  const dados = coresPontos
    ? series.map((s) => ({
        ...s,
        data: s.data.map((y, i) => {
          const cor = coresPontos[i];
          return {
            x: rotulos[i],
            y,
            fillColor: cor === null ? COR_NEUTRA[modo] : CORES[modo][cor],
          };
        }),
      }))
    : series;
  const opcoes: ApexOptions = {
    chart: {
      type: 'bar',
      toolbar: { show: false },
      foreColor: theme.palette.text.secondary,
      fontFamily: 'inherit',
      background: 'transparent',
    },
    theme: { mode: modo },
    colors: CORES[modo],
    plotOptions: {
      bar: {
        horizontal,
        barHeight: '72%',
        columnWidth: '55%',
        borderRadius: 4,
        borderRadiusApplication: 'end',
      },
    },
    stroke: { show: true, width: 2, colors: ['transparent'] },
    dataLabels: { enabled: false },
    grid: { borderColor: theme.palette.divider, strokeDashArray: 3 },
    legend: { show: series.length > 1, position: 'top', horizontalAlign: 'left' },
    xaxis: {
      categories: rotulos,
      axisBorder: { show: false },
      axisTicks: { show: false },
      ...(horizontal && {
        tickAmount: 4,
        labels: { show: !ocultar, formatter: (valor: string) => brlEixo(Number(valor)) },
      }),
    },
    yaxis: {
      labels: horizontal
        ? { maxWidth: 150 }
        : { show: !ocultar, formatter: coresPontos ? brlEixo : brlCurto },
    },
    tooltip: { theme: modo, y: { formatter: formatar } },
  };
  return (
    <Chart
      key={`${ocultar}-${altura}`}
      options={opcoes}
      series={dados}
      type="bar"
      height={altura}
    />
  );
};
