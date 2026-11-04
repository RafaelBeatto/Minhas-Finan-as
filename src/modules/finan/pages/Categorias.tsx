import { FormEvent, useEffect, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
import { IconPlus } from '@tabler/icons-react';
import PageContainer from 'src/components/container/PageContainer';
import EditarCategoria from '../components/EditarCategoria';
import { BarraUso, Indicadores, Secao, Vazio } from '../components/Visual';
import { useFinan } from '../hooks/useFinan';
import {
  buscarCategorias,
  criarCategoria,
  desfazerRenomeacao,
  removerRegraSalva,
} from '../services/api';
import { porcento, semAcento } from '../services/formato';
import { LinhaCategoria, PainelCategorias, RegraSalva } from '../types';

const ROTULOS_REGRA: Record<RegraSalva['tipo'], string> = {
  descricao: 'Mesma descrição',
  transacao: 'Uma transação',
  faixa: 'Valor mínimo',
};

const NovaCategoria = ({ aoFechar }: { aoFechar: () => void }) => {
  const { recarregar } = useFinan();
  const [nome, setNome] = useState('');
  const [erro, setErro] = useState('');

  const enviar = async (evento: FormEvent) => {
    evento.preventDefault();
    try {
      await criarCategoria(nome);
      await recarregar();
      aoFechar();
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="xs">
      <form onSubmit={enviar}>
        <DialogTitle>Nova categoria</DialogTitle>
        <DialogContent>
          {erro && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {erro}
            </Alert>
          )}
          <TextField
            autoFocus
            fullWidth
            label="Nome"
            value={nome}
            onChange={(e) => setNome(e.target.value)}
            helperText="Ela passa a aparecer ao corrigir uma transação no Extrato."
            sx={{ mt: 1 }}
          />
        </DialogContent>
        <DialogActions>
          <Button color="inherit" onClick={aoFechar}>
            Cancelar
          </Button>
          <Button variant="contained" type="submit">
            Criar
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

const Categorias = () => {
  const { painel, moeda, ocultavel, recarregar, versao } = useFinan();
  const [periodo, setPeriodo] = useState(painel?.periodos[0] ?? '');
  const [dados, setDados] = useState<PainelCategorias | null>(null);
  const [erro, setErro] = useState('');
  const [busca, setBusca] = useState('');
  const [editando, setEditando] = useState<LinhaCategoria | null>(null);
  const [criando, setCriando] = useState(false);

  useEffect(() => {
    if (!periodo) return undefined;
    let valida = true;
    setErro('');
    buscarCategorias(periodo)
      .then((resposta) => {
        if (valida) setDados(resposta);
      })
      .catch((e: Error) => valida && setErro(e.message));
    return () => {
      valida = false;
    };
  }, [periodo, versao]);

  const alterar = async (acao: () => Promise<unknown>) => {
    try {
      await acao();
      await recarregar();
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  const removerRegra = (regra: RegraSalva) => {
    const aviso = `Remover a regra de “${regra.descricao}”? Os lançamentos voltam à categoria original.`;
    if (window.confirm(aviso)) alterar(() => removerRegraSalva(regra.tipo, regra.chave));
  };

  if (!dados) {
    return (
      <PageContainer title="Categorias · Finan">
        {erro ? (
          <Alert severity="error">{erro}</Alert>
        ) : (
          <Box textAlign="center" py={6}>
            <CircularProgress />
          </Box>
        )}
      </PageContainer>
    );
  }

  const termo = semAcento(busca.trim());
  const contem = (texto: string) => semAcento(texto).includes(termo);
  const linhas = dados.linhas.filter((l) => contem(l.categoria));
  const regras = dados.regras.filter((r) => contem(r.categoria) || contem(r.descricao));
  const comGasto = dados.linhas.filter((l) => l.gastos > 0);
  const semCategoria = dados.linhas.find((l) => l.categoria === 'Sem categoria');

  return (
    <PageContainer title="Categorias · Finan">
      <>
        <Stack spacing={3}>
          {erro && <Alert severity="error">{erro}</Alert>}
          <Indicadores
            itens={[
              {
                titulo: 'Categorias com gasto',
                valor: comGasto.length,
                detalhe: `De ${dados.linhas.length} categorias`,
              },
              {
                titulo: 'Maior gasto',
                valor: comGasto[0]?.categoria ?? '—',
                detalhe: comGasto[0]
                  ? `${moeda(comGasto[0].gastos)} · ${porcento(comGasto[0].fatia)}`
                  : 'Nenhum gasto no período',
              },
              {
                titulo: 'Sem categoria',
                valor: moeda(semCategoria?.gastos ?? 0),
                detalhe: `${semCategoria?.lancamentos ?? 0} lançamentos no período`,
              },
            ]}
          />
          <Secao
            titulo="Categorias"
            subtitulo="Clique para renomear, juntar ou excluir. Movimentação interna fica de fora."
            acao={
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1}>
                <TextField
                  select
                  size="small"
                  label="Período"
                  value={periodo}
                  onChange={(e) => setPeriodo(e.target.value)}
                  sx={{ minWidth: 170 }}
                >
                  {painel?.periodos.map((p) => (
                    <MenuItem key={p} value={p}>
                      {p}
                    </MenuItem>
                  ))}
                </TextField>
                <TextField
                  size="small"
                  label="Buscar"
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                />
                <Button
                  variant="outlined"
                  startIcon={<IconPlus size={18} />}
                  onClick={() => setCriando(true)}
                >
                  Nova
                </Button>
              </Stack>
            }
          >
            {linhas.length ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Categoria</TableCell>
                      <TableCell align="right">Gastos</TableCell>
                      <TableCell sx={{ minWidth: 130 }}>Fatia</TableCell>
                      <TableCell align="right">Entradas</TableCell>
                      <TableCell align="right">Lançamentos</TableCell>
                      <TableCell align="right">Limite</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {linhas.map((l) => (
                      <TableRow
                        key={l.categoria}
                        hover
                        onClick={() => setEditando(l)}
                        sx={{ cursor: 'pointer' }}
                      >
                        <TableCell>
                          {l.categoria}
                          {l.personalizada && (
                            <Chip size="small" variant="outlined" label="Sua" sx={{ ml: 1 }} />
                          )}
                        </TableCell>
                        <TableCell align="right">{moeda(l.gastos)}</TableCell>
                        <TableCell>
                          <Stack direction="row" spacing={1} alignItems="center">
                            <Stack flexGrow={1}>
                              <BarraUso uso={l.fatia} />
                            </Stack>
                            <span>{porcento(l.fatia)}</span>
                          </Stack>
                        </TableCell>
                        <TableCell align="right">{moeda(l.entradas)}</TableCell>
                        <TableCell align="right">{l.lancamentos}</TableCell>
                        <TableCell align="right">
                          {l.limite === null ? '—' : moeda(l.limite)}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Vazio texto="Nenhuma categoria encontrada." />
            )}
          </Secao>
          {dados.renomeadas.length > 0 && (
            <Secao
              titulo="Nomes alterados"
              subtitulo="Valem também para lançamentos futuros. Ao desfazer, o limite não volta."
            >
              <Stack spacing={1}>
                {dados.renomeadas.map((r) => (
                  <Stack
                    key={r.origem}
                    direction="row"
                    justifyContent="space-between"
                    alignItems="center"
                    gap={2}
                  >
                    <span>
                      {r.origem} → {r.destino}
                    </span>
                    <Button
                      size="small"
                      color="inherit"
                      onClick={() => alterar(() => desfazerRenomeacao(r.origem))}
                    >
                      Desfazer
                    </Button>
                  </Stack>
                ))}
              </Stack>
            </Secao>
          )}
          <Secao titulo="Regras salvas" subtitulo="Correções feitas por você">
            {regras.length ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Descrição</TableCell>
                      <TableCell>Categoria</TableCell>
                      <TableCell>Vale para</TableCell>
                      <TableCell align="right">Lançamentos</TableCell>
                      <TableCell />
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {regras.map((r) => (
                      <TableRow key={`${r.tipo}${r.chave}`}>
                        <TableCell>{r.descricao}</TableCell>
                        <TableCell>{r.categoria}</TableCell>
                        <TableCell>
                          {ROTULOS_REGRA[r.tipo]}
                          {r.minimo !== null && ` (${ocultavel(moeda(r.minimo))})`}
                        </TableCell>
                        <TableCell align="right">{r.lancamentos}</TableCell>
                        <TableCell align="right">
                          <Button size="small" color="inherit" onClick={() => removerRegra(r)}>
                            Remover
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Vazio texto="Nenhuma regra encontrada." />
            )}
          </Secao>
        </Stack>
        {criando && <NovaCategoria aoFechar={() => setCriando(false)} />}
        {editando && (
          <EditarCategoria
            linha={editando}
            nomes={dados.linhas.map((l) => l.categoria)}
            aoFechar={() => setEditando(null)}
          />
        )}
      </>
    </PageContainer>
  );
};

export default Categorias;
