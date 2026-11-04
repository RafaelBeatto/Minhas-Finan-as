import { useState } from 'react';
import { Box, Grid, Stack, TextField, Typography } from '@mui/material';
import PageContainer from 'src/components/container/PageContainer';
import {
  BarraUso,
  GraficoBarras,
  Indicadores,
  Secao,
  TabelaAdaptavel,
  Vazio,
} from '../components/Visual';
import { useFinan } from '../hooks/useFinan';
import { dataBr, nomeMes, porcento, semAcento } from '../services/formato';

const Cartao = () => {
  const { painel, moeda } = useFinan();
  const [busca, setBusca] = useState('');
  if (!painel) return null;
  const { cartao, parcelas, compromisso, faturas } = painel;
  const uso = cartao.limite ? cartao.usado / cartao.limite : 0;
  const restante = parcelas.reduce((total, p) => total + p.restante, 0);
  const termo = semAcento(busca.trim());
  const visiveis = parcelas.filter((p) => semAcento(p.descricao).includes(termo));

  return (
    <PageContainer title="Cartão · Finan">
      <Stack spacing={{ xs: 1.5, sm: 3 }}>
        <Indicadores
          itens={[
            { titulo: 'Fatura atual', valor: painel.tem_contas ? moeda(cartao.fatura) : '—' },
            {
              titulo: 'Limite disponível',
              valor: painel.tem_contas ? moeda(cartao.disponivel) : '—',
            },
            { titulo: 'Vencimento', valor: dataBr(cartao.vencimento) },
            {
              titulo: 'Pagamento mínimo',
              valor: cartao.minimo === null ? '—' : moeda(cartao.minimo),
            },
          ]}
        />
        {cartao.limite > 0 && (
          <Box>
            <Typography variant="body2" color="text.secondary" mb={1}>
              Limite usado: {moeda(cartao.usado)} de {moeda(cartao.limite)} ({porcento(uso)}),
              parcelas futuras incluídas
            </Typography>
            <BarraUso uso={uso} cor={uso >= 0.8 ? 'warning' : 'primary'} />
          </Box>
        )}
        <Box>
          <Grid container spacing={{ xs: 1.5, sm: 3 }}>
            <Grid item xs={12} lg={7}>
              <Secao
                titulo="Parcelas em aberto"
                subtitulo={parcelas.length ? `Falta pagar ${moeda(restante)}` : undefined}
                acao={
                  parcelas.length > 0 && (
                    <TextField
                      size="small"
                      label="Buscar compra"
                      value={busca}
                      onChange={(e) => setBusca(e.target.value)}
                    />
                  )
                }
              >
                {visiveis.length ? (
                  <TabelaAdaptavel
                    linhas={visiveis}
                    chave={(p) => `${p.descricao}-${p.fim}-${p.parcela}-${p.valor}`}
                    colunas={[
                      { rotulo: 'Compra', render: (p) => p.descricao },
                      { rotulo: 'Valor', align: 'right', render: (p) => moeda(p.valor) },
                      {
                        rotulo: 'Parcela',
                        align: 'right',
                        render: (p) => `${p.parcela}/${p.total}`,
                      },
                      { rotulo: 'Falta pagar', align: 'right', render: (p) => moeda(p.restante) },
                      { rotulo: 'Termina', align: 'right', render: (p) => nomeMes(p.fim) },
                    ]}
                  />
                ) : (
                  <Vazio
                    texto={
                      parcelas.length ? 'Nenhuma compra nesta busca.' : 'Nenhuma parcela em aberto.'
                    }
                  />
                )}
              </Secao>
            </Grid>
            <Grid item xs={12} lg={5}>
              <Secao titulo="Já comprometido por mês" subtitulo="Parcelas previstas em cada fatura">
                {compromisso.length ? (
                  <GraficoBarras
                    rotulos={compromisso.map((c) => nomeMes(c.mes))}
                    series={[{ name: 'Parcelas', data: compromisso.map((c) => c.valor) }]}
                    formatar={moeda}
                    altura={260}
                  />
                ) : (
                  <Vazio texto="Nada comprometido." />
                )}
              </Secao>
            </Grid>
          </Grid>
        </Box>
        <Secao titulo="Faturas">
          {faturas.length ? (
            <TabelaAdaptavel
              linhas={faturas}
              chave={(f) => `${f.vencimento}-${f.total}`}
              colunas={[
                { rotulo: 'Vencimento', render: (f) => dataBr(f.vencimento) },
                { rotulo: 'Total', align: 'right', render: (f) => moeda(f.total) },
                { rotulo: 'Fechamento', render: (f) => dataBr(f.fechamento) },
                {
                  rotulo: 'Mínimo',
                  align: 'right',
                  render: (f) => (f.minimo === null ? '—' : moeda(Number(f.minimo))),
                },
                { rotulo: 'Juros e encargos', align: 'right', render: (f) => moeda(f.encargos) },
              ]}
            />
          ) : (
            <Vazio texto="As faturas aparecem depois da primeira atualização." />
          )}
        </Secao>
      </Stack>
    </PageContainer>
  );
};

export default Cartao;
