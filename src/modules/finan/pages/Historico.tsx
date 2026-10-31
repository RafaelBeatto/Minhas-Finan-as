import { useEffect, useState } from 'react';
import {
  Alert,
  MenuItem,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
} from '@mui/material';
import PageContainer from 'src/components/container/PageContainer';
import { GraficoBarras, Secao, Vazio } from '../components/Visual';
import { useFinan } from '../hooks/useFinan';
import { buscarComparacao } from '../services/api';
import { nomeMes } from '../services/formato';
import { Comparacao } from '../types';

const sinal = (valor: number) => (valor > 0 ? '+' : '');

const Historico = () => {
  const { painel, moeda, ocultar, versao } = useFinan();
  const todos = painel?.mensal ?? [];
  const anos = [...new Set(todos.map((m) => m.mes.slice(0, 4)))];
  const [ano, setAno] = useState('');
  const meses = ano ? todos.filter((m) => m.mes.startsWith(ano)) : todos;
  const [selecionado, setSelecionado] = useState(meses[0]?.mes ?? '');
  const [comparacao, setComparacao] = useState<Comparacao | null>(null);
  const [erro, setErro] = useState('');

  useEffect(() => {
    if (!selecionado) return;
    buscarComparacao(selecionado)
      .then((resposta) => {
        setComparacao(resposta);
        setErro('');
      })
      .catch((e: Error) => setErro(e.message));
  }, [selecionado, versao]);

  const emOrdem = [...meses].reverse();
  const diferenca = (valor: number) => (ocultar ? moeda(valor) : `${sinal(valor)}${moeda(valor)}`);

  return (
    <PageContainer title="Histórico · Finan">
      <Stack spacing={3}>
        {erro && <Alert severity="error">{erro}</Alert>}
        <Secao
          titulo="Mês a mês"
          subtitulo="Clique em um mês para comparar as categorias"
          acao={
            <TextField
              select
              size="small"
              label="Ano"
              value={ano}
              onChange={(e) => setAno(e.target.value)}
              sx={{ minWidth: 110 }}
            >
              <MenuItem value="">Todos</MenuItem>
              {anos.map((a) => (
                <MenuItem key={a} value={a}>
                  {a}
                </MenuItem>
              ))}
            </TextField>
          }
        >
          {meses.length ? (
            <>
              <GraficoBarras
                rotulos={emOrdem.map((m) => nomeMes(m.mes))}
                series={[
                  { name: 'Entradas', data: emOrdem.map((m) => m.entradas) },
                  { name: 'Saídas', data: emOrdem.map((m) => m.saidas) },
                ]}
                formatar={moeda}
                altura={260}
              />
              <TableContainer sx={{ mt: 2 }}>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Mês</TableCell>
                      <TableCell align="right">Entradas</TableCell>
                      <TableCell align="right">Saídas</TableCell>
                      <TableCell align="right">Resultado</TableCell>
                      <TableCell align="right">Saídas x mês anterior</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {meses.map((m) => (
                      <TableRow
                        key={m.mes}
                        hover
                        selected={m.mes === selecionado}
                        onClick={() => setSelecionado(m.mes)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>{nomeMes(m.mes)}</TableCell>
                        <TableCell align="right">{moeda(m.entradas)}</TableCell>
                        <TableCell align="right">{moeda(m.saidas)}</TableCell>
                        <TableCell align="right">{moeda(m.resultado)}</TableCell>
                        <TableCell align="right">
                          {m.variacao === null ? '—' : diferenca(m.variacao)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </>
          ) : (
            <Vazio texto="Nenhuma transação salva ainda." />
          )}
        </Secao>
        {comparacao && (
          <Secao
            titulo={`Categorias em ${nomeMes(comparacao.mes)}`}
            subtitulo={`Comparado com ${nomeMes(comparacao.anterior)}, maiores altas primeiro`}
          >
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Categoria</TableCell>
                    <TableCell align="right">Neste mês</TableCell>
                    <TableCell align="right">Mês anterior</TableCell>
                    <TableCell align="right">Diferença</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {comparacao.linhas.map((l) => (
                    <TableRow key={l.categoria}>
                      <TableCell>{l.categoria}</TableCell>
                      <TableCell align="right">{moeda(l.atual)}</TableCell>
                      <TableCell align="right">{moeda(l.anterior)}</TableCell>
                      <TableCell
                        align="right"
                        sx={{ color: l.diferenca > 0 ? 'error.main' : 'success.main' }}
                      >
                        {diferenca(l.diferenca)}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Secao>
        )}
      </Stack>
    </PageContainer>
  );
};

export default Historico;
