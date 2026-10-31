import { useState } from 'react';
import {
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
import DefinirLimite from '../components/DefinirLimite';
import { BarraUso, EtiquetaEstado, Indicadores, Secao, Vazio } from '../components/Visual';
import { useFinan } from '../hooks/useFinan';
import { nomeMes, porcento, semAcento } from '../services/formato';
import { LinhaOrcamento } from '../types';

const Orcamento = () => {
  const { painel, moeda } = useFinan();
  const [editando, setEditando] = useState<LinhaOrcamento | null>(null);
  const [busca, setBusca] = useState('');
  const [estado, setEstado] = useState('');
  if (!painel) return null;
  const linhas = painel.orcamento;
  const comLimite = linhas.filter((l) => l.limite !== null);
  const termo = semAcento(busca.trim());
  const visiveis = linhas.filter(
    (l) => semAcento(l.categoria).includes(termo) && (!estado || l.estado === estado),
  );
  const soma = (valor: (l: LinhaOrcamento) => number) =>
    comLimite.reduce((total, l) => total + valor(l), 0);

  return (
    <PageContainer title="Orçamento · Finan">
      <>
        <Stack spacing={3}>
          <Indicadores
            itens={[
              { titulo: 'Orçado no mês', valor: moeda(soma((l) => l.limite ?? 0)) },
              { titulo: 'Gasto nessas categorias', valor: moeda(soma((l) => l.gasto)) },
              {
                titulo: 'Ainda pode gastar',
                valor: moeda(soma((l) => Math.max(l.restante ?? 0, 0))),
              },
            ]}
          />
          <Secao
            titulo={`Limites de ${nomeMes(painel.hoje.slice(0, 7))}`}
            subtitulo="Clique em uma categoria para definir o limite. O gasto recomeça a cada mês."
            acao={
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                <TextField
                  size="small"
                  label="Buscar categoria"
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                />
                <TextField
                  select
                  size="small"
                  label="Situação"
                  value={estado}
                  onChange={(e) => setEstado(e.target.value)}
                  sx={{ minWidth: 160 }}
                >
                  <MenuItem value="">Todas</MenuItem>
                  <MenuItem value="estourou">Estourou</MenuItem>
                  <MenuItem value="atencao">Atenção</MenuItem>
                  <MenuItem value="ok">Dentro do limite</MenuItem>
                  <MenuItem value="sem limite">Sem limite</MenuItem>
                </TextField>
              </Stack>
            }
          >
            {visiveis.length ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Categoria</TableCell>
                      <TableCell align="right">Limite</TableCell>
                      <TableCell align="right">Gasto</TableCell>
                      <TableCell align="right">Resta</TableCell>
                      <TableCell sx={{ minWidth: 140 }}>Uso</TableCell>
                      <TableCell align="right">Média 3 meses</TableCell>
                      <TableCell>Situação</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {visiveis.map((l) => (
                      <TableRow
                        key={l.categoria}
                        hover
                        onClick={() => setEditando(l)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>{l.categoria}</TableCell>
                        <TableCell align="right">
                          {l.limite === null ? '—' : moeda(l.limite)}
                        </TableCell>
                        <TableCell align="right">{moeda(l.gasto)}</TableCell>
                        <TableCell align="right">
                          {l.restante === null ? '—' : moeda(l.restante)}
                        </TableCell>
                        <TableCell>
                          {l.uso === null ? (
                            '—'
                          ) : (
                            <Stack direction="row" spacing={1} alignItems="center">
                              <Stack flexGrow={1}>
                                <BarraUso
                                  uso={l.uso}
                                  cor={
                                    l.estado === 'estourou'
                                      ? 'error'
                                      : l.estado === 'atencao'
                                        ? 'warning'
                                        : 'primary'
                                  }
                                />
                              </Stack>
                              <span>{porcento(l.uso)}</span>
                            </Stack>
                          )}
                        </TableCell>
                        <TableCell align="right">{moeda(l.media)}</TableCell>
                        <TableCell>
                          <EtiquetaEstado estado={l.estado} />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Vazio
                texto={
                  linhas.length
                    ? 'Nenhuma categoria neste filtro.'
                    : 'As categorias aparecem quando houver gastos salvos.'
                }
              />
            )}
          </Secao>
        </Stack>
        {editando && <DefinirLimite linha={editando} aoFechar={() => setEditando(null)} />}
      </>
    </PageContainer>
  );
};

export default Orcamento;
