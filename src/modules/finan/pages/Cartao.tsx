import { useState } from 'react';
import {
  Box,
  Grid,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from '@mui/material';
import PageContainer from 'src/components/container/PageContainer';
import { BarraUso, GraficoBarras, Indicadores, Secao, Vazio } from '../components/Visual';
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
      <Stack spacing={3}>
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
          <Grid container spacing={3}>
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
                  <TableContainer>
                    <Table size="small">
                      <TableHead>
                        <TableRow>
                          <TableCell>Compra</TableCell>
                          <TableCell align="right">Parcela</TableCell>
                          <TableCell align="right">Valor</TableCell>
                          <TableCell align="right">Falta pagar</TableCell>
                          <TableCell align="right">Termina</TableCell>
                        </TableRow>
                      </TableHead>
                      <TableBody>
                        {visiveis.map((p) => (
                          <TableRow key={`${p.descricao}-${p.fim}-${p.parcela}-${p.valor}`}>
                            <TableCell>{p.descricao}</TableCell>
                            <TableCell align="right">
                              {p.parcela}/{p.total}
                            </TableCell>
                            <TableCell align="right">{moeda(p.valor)}</TableCell>
                            <TableCell align="right">{moeda(p.restante)}</TableCell>
                            <TableCell align="right">{nomeMes(p.fim)}</TableCell>
                          </TableRow>
                        ))}
                      </TableBody>
                    </Table>
                  </TableContainer>
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
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Vencimento</TableCell>
                    <TableCell>Fechamento</TableCell>
                    <TableCell align="right">Total</TableCell>
                    <TableCell align="right">Mínimo</TableCell>
                    <TableCell align="right">Juros e encargos</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {faturas.map((f) => (
                    <TableRow key={`${f.vencimento}-${f.total}`}>
                      <TableCell>{dataBr(f.vencimento)}</TableCell>
                      <TableCell>{dataBr(f.fechamento)}</TableCell>
                      <TableCell align="right">{moeda(f.total)}</TableCell>
                      <TableCell align="right">
                        {f.minimo === null ? '—' : moeda(Number(f.minimo))}
                      </TableCell>
                      <TableCell align="right">{moeda(f.encargos)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Vazio texto="As faturas aparecem depois da primeira atualização." />
          )}
        </Secao>
      </Stack>
    </PageContainer>
  );
};

export default Cartao;
