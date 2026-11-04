import { Box, Chip, Divider, Grid, Stack, Typography } from '@mui/material';
import {
  IconAlertTriangle,
  IconMinus,
  IconTrendingDown,
  IconTrendingUp,
} from '@tabler/icons-react';
import { useFinan } from '../hooks/useFinan';
import { ComparacaoMeses, Descoberta, ItemAnalise, TipoEvidencia } from '../types';
import { Secao, Vazio } from './Visual';

const EVIDENCIAS: Record<TipoEvidencia, { rotulo: string; explicacao: string }> = {
  confirmado: { rotulo: 'Dado confirmado', explicacao: 'Conta direta sobre suas movimentações.' },
  padrao: { rotulo: 'Padrão identificado', explicacao: 'Repetição que o acaso explicaria mal.' },
  tendencia: { rotulo: 'Tendência estatística', explicacao: 'Direção firme em meses fechados.' },
  estimativa: { rotulo: 'Estimativa', explicacao: 'Projeção a partir do histórico, sem garantia.' },
  insuficiente: { rotulo: 'Informação insuficiente', explicacao: 'Faltam dados para concluir.' },
};

const Evidencia = ({ tipo }: { tipo: TipoEvidencia }) => (
  <Chip size="small" variant="outlined" label={EVIDENCIAS[tipo].rotulo} />
);

const Motivo = ({ texto }: { texto?: string }) => {
  const { ocultavel } = useFinan();
  if (!texto) return null;
  return (
    <Typography variant="caption" color="text.secondary" display="block" mt={0.5}>
      {ocultavel(texto)}
    </Typography>
  );
};

const Item = ({ item }: { item: ItemAnalise }) => {
  const { ocultavel } = useFinan();
  return (
    <Box>
      <Stack direction="row" flexWrap="wrap" alignItems="center" gap={1} mb={0.5}>
        <Typography variant="subtitle1" fontWeight={600}>
          {item.titulo}
        </Typography>
        <Evidencia tipo={item.tipo} />
      </Stack>
      <Typography>{ocultavel(item.texto)}</Typography>
      <Motivo texto={item.motivo} />
    </Box>
  );
};

const Lista = ({ itens, vazio }: { itens: ItemAnalise[]; vazio: string }) =>
  itens.length ? (
    <Stack spacing={2} divider={<Divider />}>
      {itens.map((item) => (
        <Item key={`${item.titulo}${item.texto}`} item={item} />
      ))}
    </Stack>
  ) : (
    <Vazio texto={vazio} />
  );

const CartaoDescoberta = ({ descoberta: d }: { descoberta: Descoberta }) => {
  const { ocultavel } = useFinan();
  return (
    <Box height="100%" sx={{ borderLeft: 2, borderColor: 'divider', pl: 2 }}>
      <Stack direction="row" flexWrap="wrap" alignItems="center" gap={1} mb={0.5}>
        <Typography variant="subtitle1" fontWeight={600}>
          {d.titulo}
        </Typography>
        <Evidencia tipo={d.tipo} />
      </Stack>
      <Typography>{ocultavel(d.explicacao)}</Typography>
      <Stack direction="row" flexWrap="wrap" columnGap={3} rowGap={0.5} my={1}>
        {d.valores.map((v) => (
          <Box key={v.rotulo}>
            <Typography variant="caption" color="text.secondary" display="block">
              {v.rotulo}
            </Typography>
            <Typography variant="body2" fontWeight={600}>
              {ocultavel(v.texto)}
            </Typography>
          </Box>
        ))}
      </Stack>
      <Typography variant="caption" color="text.secondary" display="block">
        Período: {d.periodo}
      </Typography>
      <Motivo texto={d.motivo} />
    </Box>
  );
};

const AnaliseComparacao = ({ dados }: { dados: ComparacaoMeses }) => {
  const { moeda, ocultavel } = useFinan();
  const { analise } = dados;
  const { tendencias: t } = analise;
  const direcoes = [...t.geral, ...t.alta, ...t.queda];
  const semTendencia = !direcoes.length && !t.estaveis.length;

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Secao
            titulo="Análise do período"
            subtitulo={`Calculada neste computador, com ${analise.base.despesas} despesas de ${analise.base.periodo}`}
          >
            <Stack spacing={1.5} mb={analise.destaques.length ? 3 : 0}>
              {analise.leitura.map((texto) => (
                <Typography key={texto}>{ocultavel(texto)}</Typography>
              ))}
            </Stack>
            {analise.destaques.length > 0 && <Lista itens={analise.destaques} vazio="" />}
          </Secao>
        </Grid>
        {analise.alertas.length > 0 && (
          <Grid item xs={12}>
            <Secao titulo="Alertas">
              <Stack spacing={2}>
                {analise.alertas.map((a) => (
                  <Stack key={a.titulo} direction="row" spacing={1.5}>
                    <Box color="warning.main" pt={0.25}>
                      <IconAlertTriangle size={18} />
                    </Box>
                    <Box minWidth={0}>
                      <Typography fontWeight={600}>{a.titulo}</Typography>
                      <Typography>{ocultavel(a.texto)}</Typography>
                      <Motivo texto={a.motivo} />
                    </Box>
                  </Stack>
                ))}
              </Stack>
            </Secao>
          </Grid>
        )}
        <Grid item xs={12} lg={6}>
          <Secao titulo="Padrões" subtitulo="Encontrados em todo o histórico">
            <Lista itens={analise.padroes} vazio="Nenhum padrão com evidência suficiente." />
          </Secao>
        </Grid>
        <Grid item xs={12} lg={6}>
          <Secao
            titulo="Tendências"
            subtitulo={t.meses ? `Últimos ${t.meses} meses fechados` : undefined}
          >
            {semTendencia ? (
              <Vazio texto="Nenhuma tendência com evidência suficiente." />
            ) : (
              <Stack spacing={2}>
                {direcoes.map((item) => (
                  <Stack key={item.texto} direction="row" spacing={1.5}>
                    <Box color={item.favoravel ? 'success.main' : 'warning.main'} pt={0.25}>
                      {item.direcao === 'alta' ? (
                        <IconTrendingUp size={18} />
                      ) : (
                        <IconTrendingDown size={18} />
                      )}
                    </Box>
                    <Box minWidth={0}>
                      <Typography>{ocultavel(item.texto)}</Typography>
                      <Motivo texto={item.motivo} />
                    </Box>
                  </Stack>
                ))}
                {t.estaveis.length > 0 && (
                  <Stack direction="row" spacing={1.5}>
                    <Box color="text.secondary" pt={0.25}>
                      <IconMinus size={18} />
                    </Box>
                    <Typography>
                      Estáveis:{' '}
                      {t.estaveis.map((e) => `${e.categoria} (${moeda(e.media)})`).join(', ')}.
                    </Typography>
                  </Stack>
                )}
              </Stack>
            )}
          </Secao>
        </Grid>
        <Grid item xs={12}>
          <Secao titulo="Previsões" subtitulo="Estimativas, não certezas">
            <Lista itens={analise.previsoes} vazio="Ainda não há histórico regular para prever." />
          </Secao>
        </Grid>
        <Grid item xs={12}>
          <Secao titulo="Descobertas" subtitulo="O que chamou atenção no histórico">
            {analise.descobertas.length ? (
              <Grid container spacing={3}>
                {analise.descobertas.map((d) => (
                  <Grid item xs={12} md={6} key={`${d.titulo}${d.explicacao}`}>
                    <CartaoDescoberta descoberta={d} />
                  </Grid>
                ))}
              </Grid>
            ) : (
              <Vazio texto="Ainda não há evidência suficiente para descobertas." />
            )}
          </Secao>
        </Grid>
        <Grid item xs={12}>
          <Secao titulo="Como ler esta análise">
            <Stack spacing={1}>
              {(Object.keys(EVIDENCIAS) as TipoEvidencia[]).map((tipo) => (
                <Stack key={tipo} direction="row" flexWrap="wrap" alignItems="center" gap={1}>
                  <Evidencia tipo={tipo} />
                  <Typography variant="body2" color="text.secondary">
                    {EVIDENCIAS[tipo].explicacao}
                  </Typography>
                </Stack>
              ))}
            </Stack>
            {analise.limitacoes.length > 0 && (
              <Stack spacing={0.5} mt={2}>
                {analise.limitacoes.map((l) => (
                  <Typography key={l.texto} variant="body2">
                    {l.texto}
                  </Typography>
                ))}
              </Stack>
            )}
            <Typography variant="caption" color="text.secondary" display="block" mt={2}>
              A análise descreve o que aparece nos dados; ela não sabe por que um gasto aconteceu.
            </Typography>
          </Secao>
        </Grid>
      </Grid>
    </Box>
  );
};

export default AnaliseComparacao;
