import { ReactNode } from 'react';
import {
  Box,
  Card,
  CardContent,
  Chip,
  Grid,
  LinearProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
  useMediaQuery,
} from '@mui/material';
import type { Theme } from '@mui/material/styles';
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
    <Grid container spacing={{ xs: 1.5, sm: 3 }}>
      {itens.map(({ titulo, valor, detalhe }, i) => (
        <Grid
          item
          xs={itens.length % 2 && i === itens.length - 1 ? 12 : 6}
          sm={itens.length % 2 ? 4 : 6}
          lg={12 / itens.length}
          key={titulo}
        >
          <Card variant="outlined" sx={{ p: 0, height: '100%' }}>
            <CardContent sx={{ p: { xs: 1.5, sm: 3 }, '&:last-child': { pb: { xs: 1.5, sm: 3 } } }}>
              <Typography
                variant="subtitle2"
                color="text.secondary"
                sx={{ fontSize: { xs: '0.75rem', sm: undefined } }}
              >
                {titulo}
              </Typography>
              <Typography
                variant="h4"
                fontWeight={600}
                mt={{ xs: 0.5, sm: 1 }}
                noWrap
                sx={{ fontSize: { xs: '1.1rem', sm: undefined } }}
              >
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

export interface ColunaTabela<T> {
  rotulo: string;
  render: (linha: T) => ReactNode;
  align?: 'right';
  largura?: number;
}

/**
 * Tabela no computador; no celular cada linha vira um item de lista:
 * 1ª coluna é o título, 2ª o valor em destaque, as demais viram "rótulo: valor".
 * Colunas sem rótulo (botões) ficam numa linha própria no fim.
 */
export function TabelaAdaptavel<T>({
  colunas,
  linhas,
  chave,
  aoClicar,
  selecionada,
}: {
  colunas: ColunaTabela<T>[];
  linhas: T[];
  chave: (linha: T) => string;
  aoClicar?: (linha: T) => void;
  selecionada?: (linha: T) => boolean;
}) {
  const celular = useMediaQuery((theme: Theme) => theme.breakpoints.down('md'));
  if (!celular) {
    return (
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              {colunas.map((c, i) => (
                <TableCell key={i} align={c.align} sx={{ minWidth: c.largura }}>
                  {c.rotulo}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {linhas.map((l) => (
              <TableRow
                key={chave(l)}
                hover={!!aoClicar}
                selected={selecionada?.(l)}
                onClick={aoClicar && (() => aoClicar(l))}
                sx={{ cursor: aoClicar ? 'pointer' : undefined }}
              >
                {colunas.map((c, i) => (
                  <TableCell key={i} align={c.align}>
                    {c.render(l)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    );
  }

  const [titulo, destaque, ...resto] = colunas;
  const detalhes = resto.filter((c) => c.rotulo);
  const acoes = resto.filter((c) => !c.rotulo);
  return (
    <Box>
      {linhas.map((l) => (
        <Box
          key={chave(l)}
          onClick={aoClicar && (() => aoClicar(l))}
          sx={{
            py: 1.25,
            px: 0.5,
            borderBottom: 1,
            borderColor: 'divider',
            cursor: aoClicar ? 'pointer' : undefined,
            bgcolor: selecionada?.(l) ? 'action.selected' : undefined,
            '&:last-of-type': { borderBottom: 0 },
          }}
        >
          <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1.5}>
            <Box fontWeight={500} minWidth={0} sx={{ overflowWrap: 'anywhere' }}>
              {titulo.render(l)}
            </Box>
            {destaque && (
              <Box fontWeight={600} whiteSpace="nowrap">
                {destaque.render(l)}
              </Box>
            )}
          </Stack>
          {detalhes.length > 0 && (
            <Stack direction="row" flexWrap="wrap" columnGap={2} rowGap={0.25} mt={0.5}>
              {detalhes.map((c) => (
                <Typography key={c.rotulo} variant="caption" color="text.secondary" component="div">
                  {c.rotulo}: <Box component="span">{c.render(l)}</Box>
                </Typography>
              ))}
            </Stack>
          )}
          {acoes.length > 0 && (
            <Stack direction="row" justifyContent="flex-end" mt={0.5}>
              {acoes.map((c, i) => (
                <Box key={i} onClick={(e) => e.stopPropagation()}>
                  {c.render(l)}
                </Box>
              ))}
            </Stack>
          )}
        </Box>
      ))}
    </Box>
  );
}

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
    <CardContent sx={{ p: { xs: 2, sm: 3 }, '&:last-child': { pb: { xs: 2, sm: 3 } } }}>
      <Stack
        direction="row"
        flexWrap="wrap"
        justifyContent="space-between"
        alignItems="center"
        gap={{ xs: 1, sm: 2 }}
        mb={2}
      >
        <Box flex="1 1 160px" minWidth={0}>
          <Typography variant="h5">{titulo}</Typography>
          {subtitulo && (
            <Typography variant="subtitle2" color="text.secondary">
              {subtitulo}
            </Typography>
          )}
        </Box>
        {acao && <Box sx={{ width: { xs: '100%', md: 'auto' } }}>{acao}</Box>}
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
  altura = 260,
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
        tickAmount: 3,
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
