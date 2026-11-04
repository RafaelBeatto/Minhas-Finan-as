import { Box, Grid, Stack, Typography } from '@mui/material';
import { useFinan } from '../hooks/useFinan';
import { nomeMes, variacao } from '../services/formato';
import { ComparacaoMeses, ValorComparado } from '../types';
import { GraficoBarras, Secao, Vazio } from './Visual';

const ALTURA_POR_CATEGORIA = 52;
const ALTURA_MINIMA = 280;

const PorMes = ({
  titulo,
  linha,
  meses,
  subirEBom,
}: {
  titulo: string;
  linha: ValorComparado;
  meses: [string, string];
  subirEBom: boolean;
}) => {
  const { moeda, diferenca } = useFinan();
  const melhorou = linha.diferenca > 0 === subirEBom;
  const semValores = linha.a === 0 && linha.b === 0;
  return (
    <Secao titulo={titulo}>
      {semValores ? (
        <Vazio texto="Sem movimentações nestes meses." />
      ) : (
        <>
          <GraficoBarras
            rotulos={meses}
            series={[{ name: titulo, data: [linha.a, linha.b] }]}
            coresPontos={[0, 1]}
            formatar={moeda}
            altura={210}
          />
          <Stack direction="row" justifyContent="space-between" flexWrap="wrap" gap={1} mt={1}>
            <Typography variant="body2" color="text.secondary">
              {moeda(linha.a)} → {moeda(linha.b)}
            </Typography>
            <Typography
              variant="body2"
              fontWeight={600}
              color={
                Math.abs(linha.diferenca) < 0.005
                  ? 'text.primary'
                  : melhorou
                    ? 'success.main'
                    : 'error.main'
              }
            >
              {diferenca(linha.diferenca)} ({variacao(linha)})
            </Typography>
          </Stack>
        </>
      )}
    </Secao>
  );
};

const GraficosComparacao = ({ dados }: { dados: ComparacaoMeses }) => {
  const { moeda } = useFinan();
  const { primeiro, segundo, resumo, evolucao } = dados;
  const rotulos: [string, string] = [nomeMes(primeiro), nomeMes(segundo)];
  const categorias = dados.categorias.filter((c) => c.a > 0 || c.b > 0);
  const destaque = (mes: string) => {
    if (mes === primeiro) return 0;
    return mes === segundo ? 1 : null;
  };

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <PorMes titulo="Despesas" linha={resumo.despesas} meses={rotulos} subirEBom={false} />
        </Grid>
        <Grid item xs={12} md={4}>
          <PorMes titulo="Receitas" linha={resumo.receitas} meses={rotulos} subirEBom />
        </Grid>
        <Grid item xs={12} md={4}>
          <PorMes titulo="Saldo" linha={resumo.saldo} meses={rotulos} subirEBom />
        </Grid>
        <Grid item xs={12}>
          <Secao
            titulo="Despesas por categoria"
            subtitulo={`${rotulos[0]} em azul e ${rotulos[1]} em laranja`}
          >
            {categorias.length ? (
              <GraficoBarras
                horizontal
                rotulos={categorias.map((c) => c.categoria)}
                series={[
                  { name: rotulos[0], data: categorias.map((c) => c.a) },
                  { name: rotulos[1], data: categorias.map((c) => c.b) },
                ]}
                formatar={moeda}
                altura={Math.max(ALTURA_MINIMA, categorias.length * ALTURA_POR_CATEGORIA)}
              />
            ) : (
              <Vazio texto="Nenhuma despesa nestes dois meses." />
            )}
          </Secao>
        </Grid>
        <Grid item xs={12}>
          <Secao titulo="Evolução das despesas" subtitulo="Meses comparados em destaque">
            <GraficoBarras
              rotulos={evolucao.map((m) => nomeMes(m.mes))}
              series={[{ name: 'Despesas', data: evolucao.map((m) => m.saidas) }]}
              coresPontos={evolucao.map((m) => destaque(m.mes))}
              formatar={moeda}
              altura={260}
            />
          </Secao>
        </Grid>
      </Grid>
    </Box>
  );
};

export default GraficosComparacao;
