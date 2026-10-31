import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  Box,
  Button,
  Chip,
  FormControlLabel,
  Grid,
  List,
  ListItemButton,
  ListItemText,
  MenuItem,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TableSortLabel,
  TextField,
  Typography,
} from '@mui/material';
import PageContainer from 'src/components/container/PageContainer';
import CorrigirCategoria from '../components/CorrigirCategoria';
import { Indicadores, Secao, Vazio } from '../components/Visual';
import { useFinan } from '../hooks/useFinan';
import { buscarExtrato } from '../services/api';
import { dataBr, porcento } from '../services/formato';
import { Extrato as DadosExtrato, Transacao } from '../types';

const ESPERA_BUSCA_MS = 300;
const PERSONALIZADO = 'Personalizado';
const TIPOS = [
  { valor: 'entradas', rotulo: 'Entradas' },
  { valor: 'saidas', rotulo: 'Saídas' },
  { valor: 'internas', rotulo: 'Movimentação interna' },
];
const SITUACOES = [
  { valor: 'pendentes', rotulo: 'Pendentes' },
  { valor: 'parceladas', rotulo: 'Parceladas' },
  { valor: 'corrigidas', rotulo: 'Categoria corrigida' },
];
const ORDENACOES = [
  { valor: 'data-desc', rotulo: 'Mais recentes' },
  { valor: 'data-asc', rotulo: 'Mais antigas' },
  { valor: 'valor-desc', rotulo: 'Maior valor' },
  { valor: 'valor-asc', rotulo: 'Menor valor' },
  { valor: 'descricao-asc', rotulo: 'Descrição A–Z' },
  { valor: 'descricao-desc', rotulo: 'Descrição Z–A' },
  { valor: 'categoria-asc', rotulo: 'Categoria A–Z' },
  { valor: 'categoria-desc', rotulo: 'Categoria Z–A' },
];

/** Valor ordena sem o sinal, como os filtros de mínimo e máximo. */
const comparar = (a: Transacao, b: Transacao, campo: string) => {
  if (campo === 'valor') return Math.abs(a.valor) - Math.abs(b.valor);
  if (campo === 'data') return a.data.localeCompare(b.data);
  const texto = (t: Transacao) => (campo === 'categoria' ? t.categoria : t.descricao);
  return texto(a).localeCompare(texto(b), 'pt-BR', { sensitivity: 'base' });
};

const Coluna = ({
  campo,
  rotulo,
  ordem,
  aoOrdenar,
}: {
  campo: string;
  rotulo: string;
  ordem: string;
  aoOrdenar: (ordem: string) => void;
}) => {
  const [atual, direcao] = ordem.split('-');
  const inicial = campo === 'data' || campo === 'valor' ? 'desc' : 'asc';
  const inversa = direcao === 'asc' ? 'desc' : 'asc';
  return (
    <TableSortLabel
      active={atual === campo}
      direction={atual === campo ? (direcao as 'asc' | 'desc') : (inicial as 'asc' | 'desc')}
      onClick={() => aoOrdenar(`${campo}-${atual === campo ? inversa : inicial}`)}
    >
      {rotulo}
    </TableSortLabel>
  );
};

const Extrato = () => {
  const { painel, moeda, versao } = useFinan();
  const [periodo, setPeriodo] = useState('Este mês');
  const [conta, setConta] = useState('');
  const [busca, setBusca] = useState('');
  const [de, setDe] = useState('');
  const [ate, setAte] = useState('');
  const [categoria, setCategoria] = useState('');
  const [tipo, setTipo] = useState('');
  const [situacao, setSituacao] = useState('');
  const [minimo, setMinimo] = useState('');
  const [maximo, setMaximo] = useState('');
  const [semInternas, setSemInternas] = useState(false);
  const [dados, setDados] = useState<DadosExtrato | null>(null);
  const [erro, setErro] = useState('');
  const [pagina, setPagina] = useState(0);
  const [porPagina, setPorPagina] = useState(25);
  const [corrigindo, setCorrigindo] = useState<Transacao | null>(null);
  const [ordem, setOrdem] = useState('data-desc');

  useEffect(() => {
    let cancelado = false;
    const espera = setTimeout(async () => {
      try {
        const personalizado = periodo === PERSONALIZADO;
        const resposta = await buscarExtrato({
          periodo: personalizado ? 'Tudo' : periodo,
          conta,
          categoria,
          busca,
          tipo,
          situacao,
          minimo,
          maximo,
          sem_internas: semInternas ? '1' : '',
          de: personalizado ? de : undefined,
          ate: personalizado ? ate : undefined,
        });
        if (!cancelado) {
          setDados(resposta);
          setErro('');
          setPagina(0);
        }
      } catch (e) {
        if (!cancelado) setErro((e as Error).message);
      }
    }, ESPERA_BUSCA_MS);
    return () => {
      cancelado = true;
      clearTimeout(espera);
    };
  }, [
    periodo,
    conta,
    categoria,
    busca,
    de,
    ate,
    tipo,
    situacao,
    minimo,
    maximo,
    semInternas,
    versao,
  ]);

  const transacoes = useMemo(() => {
    const [campo, direcao] = ordem.split('-');
    const sinal = direcao === 'asc' ? 1 : -1;
    return [...(dados?.transacoes ?? [])].sort(
      (a, b) => sinal * comparar(a, b, campo) || b.data.localeCompare(a.data),
    );
  }, [dados, ordem]);
  const ordenar = (nova: string) => {
    setOrdem(nova);
    setPagina(0);
  };
  // A categoria escolhida fica na lista mesmo se os outros filtros a deixarem sem transações.
  const categorias = [
    ...new Set([...(categoria ? [categoria] : []), ...(dados?.categorias_disponiveis ?? [])]),
  ].sort((a, b) => a.localeCompare(b, 'pt-BR'));
  const filtrosAtivos =
    [conta, categoria, busca, tipo, situacao, minimo, maximo].filter(Boolean).length +
    Number(semInternas) +
    Number(periodo !== 'Este mês');
  const limparFiltros = () => {
    setPeriodo('Este mês');
    setConta('');
    setCategoria('');
    setBusca('');
    setDe('');
    setAte('');
    setTipo('');
    setSituacao('');
    setMinimo('');
    setMaximo('');
    setSemInternas(false);
  };

  return (
    <PageContainer title="Extrato · Finan">
      <>
        <Stack spacing={3}>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2}>
            <TextField
              select
              size="small"
              label="Período"
              value={periodo}
              onChange={(e) => setPeriodo(e.target.value)}
              sx={{ minWidth: 180 }}
            >
              {[...(painel?.periodos ?? []), PERSONALIZADO].map((p) => (
                <MenuItem key={p} value={p}>
                  {p}
                </MenuItem>
              ))}
            </TextField>
            {periodo === PERSONALIZADO && (
              <>
                <TextField
                  size="small"
                  type="date"
                  label="De"
                  value={de}
                  onChange={(e) => setDe(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                />
                <TextField
                  size="small"
                  type="date"
                  label="Até"
                  value={ate}
                  onChange={(e) => setAte(e.target.value)}
                  InputLabelProps={{ shrink: true }}
                />
              </>
            )}
            <TextField
              select
              size="small"
              label="Conta"
              value={conta}
              onChange={(e) => setConta(e.target.value)}
              sx={{ minWidth: 200 }}
            >
              <MenuItem value="">Todas</MenuItem>
              {painel?.nomes_contas.map((c) => (
                <MenuItem key={c} value={c}>
                  {c}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              label="Buscar descrição"
              value={busca}
              onChange={(e) => setBusca(e.target.value)}
              fullWidth
            />
          </Stack>
          <Stack direction={{ xs: 'column', md: 'row' }} spacing={2} alignItems={{ md: 'center' }}>
            <TextField
              select
              size="small"
              label="Tipo"
              value={tipo}
              onChange={(e) => setTipo(e.target.value)}
              sx={{ minWidth: 170 }}
            >
              <MenuItem value="">Todos</MenuItem>
              {TIPOS.map((t) => (
                <MenuItem key={t.valor} value={t.valor}>
                  {t.rotulo}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              size="small"
              label="Categoria"
              value={categoria}
              onChange={(e) => setCategoria(e.target.value)}
              sx={{ minWidth: 190 }}
            >
              <MenuItem value="">Todas</MenuItem>
              {categorias.map((c) => (
                <MenuItem key={c} value={c}>
                  {c}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              size="small"
              label="Situação"
              value={situacao}
              onChange={(e) => setSituacao(e.target.value)}
              sx={{ minWidth: 170 }}
            >
              <MenuItem value="">Todas</MenuItem>
              {SITUACOES.map((s) => (
                <MenuItem key={s.valor} value={s.valor}>
                  {s.rotulo}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              label="Valor mínimo"
              value={minimo}
              onChange={(e) => setMinimo(e.target.value)}
              inputProps={{ inputMode: 'decimal' }}
            />
            <TextField
              size="small"
              label="Valor máximo"
              value={maximo}
              onChange={(e) => setMaximo(e.target.value)}
              inputProps={{ inputMode: 'decimal' }}
            />
          </Stack>
          <Stack direction="row" justifyContent="space-between" alignItems="center">
            <FormControlLabel
              control={
                <Switch checked={semInternas} onChange={(e) => setSemInternas(e.target.checked)} />
              }
              label="Esconder movimentação interna"
            />
            <Button size="small" onClick={limparFiltros} disabled={!filtrosAtivos}>
              {filtrosAtivos ? `Limpar filtros (${filtrosAtivos})` : 'Limpar filtros'}
            </Button>
          </Stack>

          {erro && <Alert severity="error">{erro}</Alert>}

          <Indicadores
            itens={[
              { titulo: 'Entradas', valor: moeda(dados?.entradas ?? 0) },
              { titulo: 'Saídas', valor: moeda(dados?.saidas ?? 0) },
              { titulo: 'Resultado do período', valor: moeda(dados?.resultado ?? 0) },
            ]}
          />

          <Box>
            <Grid container spacing={3}>
              <Grid item xs={12} lg={8}>
                <Secao
                  titulo="Transações"
                  subtitulo={`${transacoes.length} no filtro · clique para corrigir a categoria`}
                  acao={
                    <Stack direction="row" spacing={1} alignItems="center">
                      {categoria && (
                        <Chip label={categoria} onDelete={() => setCategoria('')} size="small" />
                      )}
                      <TextField
                        select
                        size="small"
                        label="Ordenar por"
                        value={ordem}
                        onChange={(e) => ordenar(e.target.value)}
                        sx={{ minWidth: 170 }}
                      >
                        {ORDENACOES.map((o) => (
                          <MenuItem key={o.valor} value={o.valor}>
                            {o.rotulo}
                          </MenuItem>
                        ))}
                      </TextField>
                    </Stack>
                  }
                >
                  {transacoes.length ? (
                    <>
                      <TableContainer>
                        <Table size="small">
                          <TableHead>
                            <TableRow>
                              <TableCell>
                                <Coluna
                                  campo="data"
                                  rotulo="Data"
                                  ordem={ordem}
                                  aoOrdenar={ordenar}
                                />
                              </TableCell>
                              <TableCell>
                                <Coluna
                                  campo="descricao"
                                  rotulo="Descrição"
                                  ordem={ordem}
                                  aoOrdenar={ordenar}
                                />
                              </TableCell>
                              <TableCell>
                                <Coluna
                                  campo="categoria"
                                  rotulo="Categoria"
                                  ordem={ordem}
                                  aoOrdenar={ordenar}
                                />
                              </TableCell>
                              <TableCell>Conta</TableCell>
                              <TableCell align="right">
                                <Coluna
                                  campo="valor"
                                  rotulo="Valor"
                                  ordem={ordem}
                                  aoOrdenar={ordenar}
                                />
                              </TableCell>
                            </TableRow>
                          </TableHead>
                          <TableBody>
                            {transacoes
                              .slice(pagina * porPagina, (pagina + 1) * porPagina)
                              .map((t) => (
                                <TableRow
                                  key={t.id}
                                  hover
                                  onClick={() => setCorrigindo(t)}
                                  sx={{ cursor: 'pointer', opacity: t.interno ? 0.6 : 1 }}
                                >
                                  <TableCell sx={{ whiteSpace: 'nowrap' }}>
                                    {dataBr(t.data)}
                                  </TableCell>
                                  <TableCell>
                                    {t.parcelas_total > 1
                                      ? `${t.descricao} (${t.parcela}/${t.parcelas_total})`
                                      : t.descricao}
                                    {t.pendente && (
                                      <Chip size="small" label="Pendente" sx={{ ml: 1 }} />
                                    )}
                                  </TableCell>
                                  <TableCell>
                                    {t.corrigida ? `${t.categoria} *` : t.categoria}
                                  </TableCell>
                                  <TableCell sx={{ maxWidth: 140 }}>
                                    <Typography variant="body2" noWrap>
                                      {t.conta}
                                    </Typography>
                                  </TableCell>
                                  <TableCell align="right" sx={{ whiteSpace: 'nowrap' }}>
                                    {moeda(t.valor)}
                                  </TableCell>
                                </TableRow>
                              ))}
                          </TableBody>
                        </Table>
                      </TableContainer>
                      <TablePagination
                        component="div"
                        count={transacoes.length}
                        page={pagina}
                        rowsPerPage={porPagina}
                        rowsPerPageOptions={[25, 50, 100]}
                        labelRowsPerPage="Por página"
                        labelDisplayedRows={({ from, to, count }) => `${from}–${to} de ${count}`}
                        onPageChange={(_, nova) => setPagina(nova)}
                        onRowsPerPageChange={(e) => {
                          setPorPagina(Number(e.target.value));
                          setPagina(0);
                        }}
                      />
                      <Typography variant="caption" color="text.secondary">
                        * categoria corrigida por você. Linhas apagadas são movimentação interna e
                        não entram nos totais.
                      </Typography>
                    </>
                  ) : (
                    <Vazio texto="Nenhuma transação neste filtro." />
                  )}
                </Secao>
              </Grid>
              <Grid item xs={12} lg={4}>
                <Secao
                  titulo="Gastos por categoria"
                  acao={
                    categoria && (
                      <Button size="small" onClick={() => setCategoria('')}>
                        Limpar
                      </Button>
                    )
                  }
                >
                  {dados?.por_categoria.length ? (
                    <List disablePadding>
                      {dados.por_categoria.map((c) => (
                        <ListItemButton
                          key={c.categoria}
                          selected={c.categoria === categoria}
                          onClick={() => setCategoria(c.categoria === categoria ? '' : c.categoria)}
                          sx={{ borderRadius: 1 }}
                        >
                          <ListItemText primary={c.categoria} />
                          <Typography variant="body2" fontWeight={600} ml={2}>
                            {moeda(c.total)}
                          </Typography>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            ml={1}
                            width={36}
                            textAlign="right"
                          >
                            {dados.total_categorias
                              ? porcento(c.total / dados.total_categorias)
                              : '—'}
                          </Typography>
                        </ListItemButton>
                      ))}
                    </List>
                  ) : (
                    <Vazio texto="Sem gastos no período." />
                  )}
                </Secao>
              </Grid>
            </Grid>
          </Box>
        </Stack>
        {corrigindo && (
          <CorrigirCategoria transacao={corrigindo} aoFechar={() => setCorrigindo(null)} />
        )}
      </>
    </PageContainer>
  );
};

export default Extrato;
