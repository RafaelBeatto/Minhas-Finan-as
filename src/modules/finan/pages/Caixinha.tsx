import { useState } from 'react';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  MenuItem,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from '@mui/material';
import { IconPigMoney, IconTarget } from '@tabler/icons-react';
import Chart from 'react-apexcharts';
import { ApexOptions } from 'apexcharts';
import PageContainer from 'src/components/container/PageContainer';
import { Indicadores, Secao, Vazio } from '../components/Visual';
import { useFinan } from '../hooks/useFinan';
import { dataBr, porcento } from '../services/formato';
import { Investimento } from '../types';

interface MetaCaixinha {
  valor: number;
}

const CHAVE_METAS = 'caixinha-metas';
const CHAVE_NOMES = 'caixinha-nomes';

const lerSalvo = <T,>(chave: string): Record<string, T> => {
  try {
    return JSON.parse(localStorage.getItem(chave) ?? '{}');
  } catch {
    return {};
  }
};

const gravar = (chave: string, valor: unknown) => {
  try {
    localStorage.setItem(chave, JSON.stringify(valor));
  } catch {
    // sem armazenamento disponível: a alteração vale só até recarregar
  }
};

const Caixinha = () => {
  const { painel, moeda } = useFinan();

  const [metas, setMetas] = useState(() => lerSalvo<MetaCaixinha>(CHAVE_METAS));
  const [nomes, setNomes] = useState(() => lerSalvo<string>(CHAVE_NOMES));
  const [busca, setBusca] = useState('');
  const [tipoFiltro, setTipoFiltro] = useState('');
  const [ordenacao, setOrdenacao] = useState('saldo-desc');
  const [editando, setEditando] = useState<Investimento | null>(null);
  const [nomeCustomizado, setNomeCustomizado] = useState('');
  const [metaValor, setMetaValor] = useState('');
  const [visaoRendimento, setVisaoRendimento] = useState<'meses' | 'semanas'>('meses');

  if (!painel) return null;
  const { investimentos, investido, investimentos_encerrados: encerrados } = painel;
  const rendimento = painel.rendimento;
  const periodos = rendimento[visaoRendimento];
  const maior = Math.max(0, ...investimentos.map((i) => i.saldo));
  const tipos = [...new Set(investimentos.map((i) => i.tipo).filter(Boolean))];

  const nomeDe = (i: Investimento) => nomes[i.id] || i.nome;
  const termo = busca.toLowerCase();

  const filtrados = investimentos
    .filter(
      (i) =>
        nomeDe(i).toLowerCase().includes(termo) && (!tipoFiltro || (i.tipo || '—') === tipoFiltro),
    )
    .sort((a, b) => {
      if (ordenacao === 'saldo-desc') return b.saldo - a.saldo;
      if (ordenacao === 'saldo-asc') return a.saldo - b.saldo;
      const porNome = nomeDe(a).localeCompare(nomeDe(b), 'pt-BR', { sensitivity: 'base' });
      return ordenacao === 'nome-desc' ? -porNome : porNome;
    });

  const valorDigitado = parseFloat(metaValor.replace(',', '.'));

  const salvar = () => {
    if (!editando) return;
    const novasMetas = { ...metas };
    if (valorDigitado > 0) novasMetas[editando.id] = { valor: valorDigitado };
    else delete novasMetas[editando.id];

    const novosNomes = { ...nomes };
    const nome = nomeCustomizado.trim();
    if (nome && nome !== editando.nome) novosNomes[editando.id] = nome;
    else delete novosNomes[editando.id];

    setMetas(novasMetas);
    setNomes(novosNomes);
    gravar(CHAVE_METAS, novasMetas);
    gravar(CHAVE_NOMES, novosNomes);
    setEditando(null);
  };

  const abrirEdicao = (inv: Investimento) => {
    setEditando(inv);
    setNomeCustomizado(nomeDe(inv));
    setMetaValor(metas[inv.id]?.valor.toString() ?? '');
  };

  const percentualMeta = (inv: Investimento) => {
    const meta = metas[inv.id];
    if (!meta) return null;
    return Math.min((inv.saldo / meta.valor) * 100, 100);
  };

  const graficoComposicao =
    filtrados.length > 0
      ? {
          series: filtrados.map((i) => i.saldo),
          options: {
            chart: { type: 'donut' as const },
            labels: filtrados.map(nomeDe),
            responsive: [{ breakpoint: 600, options: { chart: { height: 300 } } }],
          } as ApexOptions,
        }
      : null;

  return (
    <PageContainer title="Caixinha · Finan">
      <Stack spacing={{ xs: 1.5, sm: 3 }}>
        <Indicadores
          itens={[
            { titulo: 'Total guardado', valor: moeda(investido) },
            {
              titulo: 'Posições',
              valor: investimentos.length,
              detalhe: encerrados > 0 ? `${encerrados} resgatadas ocultas` : undefined,
            },
            { titulo: 'Maior posição', valor: moeda(maior) },
          ]}
        />

        {graficoComposicao && (
          <Secao titulo="Composição do portfólio">
            <Chart
              type="donut"
              series={graficoComposicao.series}
              options={graficoComposicao.options}
              height={300}
            />
          </Secao>
        )}

        <Secao titulo="Rendimento da caixinha">
          <Stack spacing={2}>
            <ToggleButtonGroup
              size="small"
              exclusive
              value={visaoRendimento}
              onChange={(_, v) => v && setVisaoRendimento(v)}
            >
              <ToggleButton value="meses">Por mês</ToggleButton>
              <ToggleButton value="semanas">Por semana</ToggleButton>
            </ToggleButtonGroup>

            {periodos.length ? (
              <>
                <Chart
                  type="bar"
                  height={240}
                  series={[{ name: 'Rendimento', data: [...periodos].reverse().map((p) => +p.rendimento.toFixed(2)) }]}
                  options={
                    {
                      chart: { toolbar: { show: false } },
                      xaxis: { categories: [...periodos].reverse().map((p) => p.rotulo) },
                      yaxis: { labels: { formatter: (v: number) => moeda(v) } },
                      dataLabels: { enabled: false },
                      tooltip: { y: { formatter: (v: number) => moeda(v) } },
                    } as ApexOptions
                  }
                />
                <Stack divider={<Divider flexItem />} spacing={1}>
                  {periodos.map((p) => (
                    <Stack key={p.rotulo} direction="row" alignItems="center" spacing={1}>
                      <Stack flex={1} minWidth={0}>
                        <Typography variant="body2" fontWeight={500}>
                          {p.rotulo}
                          {p.parcial && ' (parcial)'}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {p.percentual !== null ? `${porcento(p.percentual)} sobre ${moeda(p.saldo_inicial)}` : '—'}
                          {p.variacao !== null &&
                            ` · ${p.variacao >= 0 ? '▲' : '▼'} ${moeda(Math.abs(p.variacao))} vs. anterior`}
                        </Typography>
                      </Stack>
                      <Typography
                        fontWeight={600}
                        color={p.rendimento >= 0 ? 'success.main' : 'error.main'}
                        sx={{ whiteSpace: 'nowrap' }}
                      >
                        {p.rendimento >= 0 ? '+' : ''}
                        {moeda(p.rendimento)}
                      </Typography>
                    </Stack>
                  ))}
                </Stack>
              </>
            ) : (
              <Vazio texto="Ainda não há dois saldos guardados para comparar. Clique em Atualizar em dias diferentes: o histórico começa a ser registrado agora." />
            )}
            <Typography variant="caption" color="text.secondary">
              Rendimento = variação do saldo menos depósitos e resgates.
              {rendimento.desde && ` Saldos registrados desde ${dataBr(rendimento.desde)}.`}
              {!rendimento.tem_aportes &&
                ' Os aportes não vieram da Pluggy: depósitos podem aparecer como rendimento.'}
            </Typography>
          </Stack>
        </Secao>

        <Secao titulo="Caixinhas e investimentos">
          {investimentos.length ? (
            <Stack spacing={2}>
              <Stack
                direction={{ xs: 'column', sm: 'row' }}
                spacing={1.5}
                sx={{ mb: 1, flexWrap: 'wrap' }}
              >
                <TextField
                  size="small"
                  label="Buscar"
                  value={busca}
                  onChange={(e) => setBusca(e.target.value)}
                  sx={{ flex: 1, minWidth: 150 }}
                />
                {tipos.length > 0 && (
                  <TextField
                    select
                    size="small"
                    label="Tipo"
                    value={tipoFiltro}
                    onChange={(e) => setTipoFiltro(e.target.value)}
                    sx={{ minWidth: 150 }}
                  >
                    <MenuItem value="">Todos</MenuItem>
                    {tipos.map((tipo) => (
                      <MenuItem key={tipo} value={tipo}>
                        {tipo}
                      </MenuItem>
                    ))}
                  </TextField>
                )}
                <TextField
                  select
                  size="small"
                  label="Ordenar"
                  value={ordenacao}
                  onChange={(e) => setOrdenacao(e.target.value)}
                  sx={{ minWidth: 180 }}
                >
                  <MenuItem value="saldo-desc">Maior saldo</MenuItem>
                  <MenuItem value="saldo-asc">Menor saldo</MenuItem>
                  <MenuItem value="nome-asc">Nome A–Z</MenuItem>
                  <MenuItem value="nome-desc">Nome Z–A</MenuItem>
                </TextField>
              </Stack>

              {filtrados.length ? (
                <Stack divider={<Divider flexItem />} spacing={1.5}>
                  {filtrados.map((i) => {
                    const meta = metas[i.id];
                    const percentual = percentualMeta(i);
                    const nome = nomeDe(i);
                    const faltaParaMeta = meta ? Math.max(meta.valor - i.saldo, 0) : null;
                    return (
                      <Box
                        key={i.id}
                        onClick={() => abrirEdicao(i)}
                        sx={{
                          p: 1.5,
                          border: '1px solid',
                          borderColor: 'divider',
                          borderRadius: 1,
                          cursor: 'pointer',
                          transition: 'all 0.2s',
                          '&:hover': {
                            bgcolor: 'action.hover',
                            borderColor: 'primary.main',
                          },
                        }}
                      >
                        <Stack direction="row" spacing={1.5} alignItems="flex-start" mb={1}>
                          <IconPigMoney size={24} style={{ marginTop: 2 }} />
                          <Stack flex={1} minWidth={0}>
                            <Typography variant="body2" fontWeight={500}>
                              {nome}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {i.tipo || '—'}
                              {i.data && ` · ${dataBr(i.data)}`}
                            </Typography>
                          </Stack>
                          <Typography fontWeight={600} sx={{ whiteSpace: 'nowrap' }}>
                            {moeda(i.saldo)}
                          </Typography>
                        </Stack>
                        {meta && percentual !== null && (
                          <Stack spacing={0.5}>
                            <Stack direction="row" alignItems="center" spacing={1}>
                              <IconTarget size={16} />
                              <Typography variant="caption" color="text.secondary" flex={1}>
                                Meta: {moeda(meta.valor)}
                              </Typography>
                              <Typography variant="caption" fontWeight={600}>
                                {porcento(percentual / 100)}
                              </Typography>
                            </Stack>
                            <Box
                              sx={{
                                height: 6,
                                bgcolor: 'action.disabled',
                                borderRadius: 3,
                                overflow: 'hidden',
                              }}
                            >
                              <Box
                                sx={{
                                  height: '100%',
                                  width: `${percentual}%`,
                                  bgcolor:
                                    percentual === 100
                                      ? 'success.main'
                                      : percentual > 75
                                        ? 'primary.main'
                                        : 'warning.main',
                                  transition: 'width 0.3s',
                                }}
                              />
                            </Box>
                            {faltaParaMeta !== null && faltaParaMeta > 0 && (
                              <Typography variant="caption" color="text.secondary">
                                Faltam {moeda(faltaParaMeta)}
                              </Typography>
                            )}
                          </Stack>
                        )}
                      </Box>
                    );
                  })}
                  <Typography variant="caption" color="text.secondary">
                    O Nubank não informa o nome de cada caixinha, por isso aparecem como CDB. Clique
                    para editar nomes e definir metas.
                  </Typography>
                </Stack>
              ) : (
                <Vazio texto="Nenhuma caixinha corresponde aos filtros." />
              )}
            </Stack>
          ) : (
            <Vazio
              texto={
                painel.investimentos_status === 'vazio'
                  ? 'A Pluggy não devolveu caixinhas nem investimentos para esta conexão.'
                  : painel.investimentos_status === 'falhou'
                    ? 'A Pluggy recusou a consulta de investimentos (plano ou banco sem esse dado).'
                    : 'Clique em Atualizar para buscar caixinhas e investimentos.'
              }
            />
          )}
        </Secao>
      </Stack>

      <Dialog open={!!editando} onClose={() => setEditando(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Editar caixinha</DialogTitle>
        <DialogContent sx={{ pt: 2 }}>
          <Stack spacing={2}>
            <TextField
              fullWidth
              label="Nome personalizado"
              value={nomeCustomizado}
              onChange={(e) => setNomeCustomizado(e.target.value)}
              placeholder={editando?.nome}
            />
            <TextField
              fullWidth
              label="Meta (valor em R$)"
              type="number"
              value={metaValor}
              onChange={(e) => setMetaValor(e.target.value)}
              placeholder="0"
              inputProps={{ step: 100 }}
            />
            {valorDigitado > 0 && editando && (
              <Box
                sx={{
                  p: 1.5,
                  bgcolor: 'action.hover',
                  borderRadius: 1,
                  border: '1px solid',
                  borderColor: 'divider',
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  Saldo atual: <strong>{moeda(editando.saldo)}</strong>
                </Typography>
                <Typography variant="caption" color="text.secondary" display="block">
                  Progresso:{' '}
                  <strong>{porcento(Math.min(editando.saldo / valorDigitado, 1))}</strong>
                </Typography>
                {valorDigitado > editando.saldo && (
                  <Typography variant="caption" color="text.secondary" display="block">
                    Faltam: <strong>{moeda(valorDigitado - editando.saldo)}</strong>
                  </Typography>
                )}
              </Box>
            )}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setEditando(null)}>Cancelar</Button>
          <Button onClick={salvar} variant="contained">
            Salvar
          </Button>
        </DialogActions>
      </Dialog>
    </PageContainer>
  );
};

export default Caixinha;
