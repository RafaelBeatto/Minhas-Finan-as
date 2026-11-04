import {
  Alert,
  Box,
  Button,
  Divider,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';
import { Link } from 'react-router-dom';
import PageContainer from 'src/components/container/PageContainer';
import { BarraUso, GraficoBarras, Indicadores, Secao, Vazio } from '../components/Visual';
import { useFinan } from '../hooks/useFinan';
import { nomeMes, porcento } from '../services/formato';

const MESES_GRAFICO = 12;
const CATEGORIAS_RESUMO = 6;

const VisaoGeral = () => {
  const { painel, moeda } = useFinan();
  if (!painel) return null;
  const { previsao, proximo_mes: proximo } = painel;
  const mesAtual = painel.mensal.find((m) => m.mes === painel.hoje.slice(0, 7));
  const meses = painel.mensal.slice(0, MESES_GRAFICO).reverse();
  const gastos = painel.orcamento.filter((l) => l.gasto > 0).sort((a, b) => b.gasto - a.gasto);
  const maiorGasto = gastos[0]?.gasto ?? 0;
  const projetado = previsao.projecao;

  return (
    <PageContainer title="Visão geral · Finan">
      <Stack spacing={{ xs: 1.5, sm: 3 }}>
        {painel.alerta && (
          <Alert
            severity="warning"
            action={
              <Button color="inherit" size="small" component={Link} to="/finan/orcamento">
                Ver
              </Button>
            }
          >
            {painel.alerta}
          </Alert>
        )}
        <Indicadores
          itens={[
            {
              titulo: 'Saldo em conta',
              valor: painel.tem_contas ? moeda(painel.em_conta) : '—',
              detalhe: painel.tem_contas ? `${painel.contas.length} contas` : 'Atualize para ver',
            },
            {
              titulo: 'Caixinhas',
              valor: painel.investimentos.length ? moeda(painel.investido) : '—',
              detalhe: 'Veja na aba Caixinha',
            },
            {
              titulo: 'Fatura do cartão',
              valor: painel.tem_contas ? moeda(painel.fatura) : '—',
              detalhe: 'É dívida: não sai do saldo acima',
            },
            {
              titulo: 'Resultado do mês',
              valor: moeda(mesAtual?.resultado ?? 0),
              detalhe:
                mesAtual && mesAtual.entradas > 0
                  ? `Guardou ${porcento(Math.max(mesAtual.resultado, 0) / mesAtual.entradas)} das entradas`
                  : 'Sem entradas neste mês',
            },
            {
              titulo: 'Previsão de gastos',
              valor: projetado === null ? '—' : moeda(projetado),
              detalhe:
                projetado === null
                  ? 'Disponível a partir do dia 5'
                  : `No ritmo atual · média ${moeda(previsao.media)}`,
            },
          ]}
        />
        <Box>
          <Grid container spacing={{ xs: 1.5, sm: 3 }}>
            <Grid item xs={12} lg={8}>
              <Secao titulo="Entradas e saídas" subtitulo="Sem movimentação interna">
                {meses.length ? (
                  <GraficoBarras
                    rotulos={meses.map((m) => nomeMes(m.mes))}
                    series={[
                      { name: 'Entradas', data: meses.map((m) => m.entradas) },
                      { name: 'Saídas', data: meses.map((m) => m.saidas) },
                    ]}
                    formatar={moeda}
                  />
                ) : (
                  <Vazio texto="Nenhuma transação salva ainda." />
                )}
              </Secao>
            </Grid>
            <Grid item xs={12} lg={4}>
              <Secao titulo="Já contratado" subtitulo={`Para ${nomeMes(proximo.mes)}`}>
                <Typography variant="h4" fontWeight={600}>
                  {moeda(proximo.total)}
                </Typography>
                <Divider sx={{ my: 2 }} />
                <Stack spacing={1}>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography color="text.secondary">Parcelas</Typography>
                    <Typography>{moeda(proximo.parcelas)}</Typography>
                  </Stack>
                  <Stack direction="row" justifyContent="space-between">
                    <Typography color="text.secondary">Assinaturas</Typography>
                    <Typography>{moeda(proximo.assinaturas)}</Typography>
                  </Stack>
                </Stack>
                <Typography variant="caption" color="text.secondary" display="block" mt={2}>
                  Calculado pelo app a partir das parcelas e cobranças conhecidas.
                </Typography>
              </Secao>
            </Grid>
            <Grid item xs={12} md={6}>
              <Secao titulo="Maiores gastos do mês">
                {gastos.length ? (
                  <Stack spacing={2}>
                    {gastos.slice(0, CATEGORIAS_RESUMO).map((l) => (
                      <Box key={l.categoria}>
                        <Stack direction="row" justifyContent="space-between" mb={0.5}>
                          <Typography variant="body2">{l.categoria}</Typography>
                          <Typography variant="body2" fontWeight={600}>
                            {moeda(l.gasto)}
                          </Typography>
                        </Stack>
                        <BarraUso uso={l.gasto / maiorGasto} />
                      </Box>
                    ))}
                  </Stack>
                ) : (
                  <Vazio texto="Nenhum gasto neste mês." />
                )}
              </Secao>
            </Grid>
            <Grid item xs={12} md={6}>
              <Secao titulo="Contas conectadas">
                {painel.contas.length ? (
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Conta</TableCell>
                          <TableCell>Tipo</TableCell>
                          <TableCell align="right">Saldo</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {painel.contas.map((c) => (
                          <TableRow key={c.id}>
                            <TableCell>{c.nome}</TableCell>
                            <TableCell>{c.cartao ? 'Cartão de crédito' : 'Conta'}</TableCell>
                            <TableCell align="right">{moeda(c.saldo)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
                ) : (
                  <Vazio texto="Clique em Atualizar para trazer as contas." />
                )}
              </Secao>
            </Grid>
          </Grid>
        </Box>
      </Stack>
    </PageContainer>
  );
};

export default VisaoGeral;
