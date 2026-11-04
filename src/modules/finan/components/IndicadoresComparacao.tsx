import {
  Box,
  Chip,
  ChipProps,
  Grid,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import { useFinan } from '../hooks/useFinan';
import { nomeMes, variacao } from '../services/formato';
import { CategoriaComparada, ComparacaoMeses, SituacaoCategoria, ValorComparado } from '../types';
import { Secao, Vazio } from './Visual';

const CORES_SITUACAO: Record<SituacaoCategoria, ChipProps['color']> = {
  Aumentou: 'error',
  Diminuiu: 'success',
  'Permaneceu igual': 'default',
  'Nova categoria': 'warning',
  'Sem movimentação': 'default',
};

const corDiferenca = (valor: number, subirEBom = false) => {
  if (Math.abs(valor) < 0.005) return 'text.primary';
  return valor > 0 === subirEBom ? 'success.main' : 'error.main';
};

const Ranking = ({
  titulo,
  subtitulo,
  linhas,
  vazio,
}: {
  titulo: string;
  subtitulo: string;
  linhas: CategoriaComparada[];
  vazio: string;
}) => {
  const { diferenca } = useFinan();
  return (
    <Secao titulo={titulo} subtitulo={subtitulo}>
      {linhas.length ? (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Categoria</TableCell>
                <TableCell align="right">Variação</TableCell>
                <TableCell align="right">Diferença</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {linhas.map((l) => (
                <TableRow key={l.categoria}>
                  <TableCell>{l.categoria}</TableCell>
                  <TableCell align="right">{variacao(l)}</TableCell>
                  <TableCell align="right" sx={{ color: corDiferenca(l.diferenca) }}>
                    {diferenca(l.diferenca)}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : (
        <Vazio texto={vazio} />
      )}
    </Secao>
  );
};

const IndicadoresComparacao = ({ dados }: { dados: ComparacaoMeses }) => {
  const { moeda, diferenca } = useFinan();
  const a = nomeMes(dados.primeiro);
  const b = nomeMes(dados.segundo);
  const resumo: [string, ValorComparado, boolean][] = [
    ['Receitas', dados.resumo.receitas, true],
    ['Despesas', dados.resumo.despesas, false],
    ['Saldo (receitas - despesas)', dados.resumo.saldo, true],
  ];
  const leitura = (item: ComparacaoMeses['um_periodo'][number]) => {
    const outro = item.ultimo_outro_mes && nomeMes(item.ultimo_outro_mes);
    if (item.tipo === 'nova') return `Só em ${b}: primeiro gasto registrado no histórico`;
    if (item.tipo === 'retomada') return `Só em ${b}: já teve gastos antes (último em ${outro})`;
    return outro
      ? `Só em ${a}: sem lançamentos em ${b}, mas teve gastos em ${outro}`
      : `Só em ${a}: sem gastos em outros meses`;
  };

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Secao titulo="Resumo financeiro">
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell />
                    <TableCell align="right">{a}</TableCell>
                    <TableCell align="right">{b}</TableCell>
                    <TableCell align="right">Diferença</TableCell>
                    <TableCell align="right">Variação</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {resumo.map(([titulo, linha, subirEBom]) => (
                    <TableRow key={titulo}>
                      <TableCell>{titulo}</TableCell>
                      <TableCell align="right">{moeda(linha.a)}</TableCell>
                      <TableCell align="right">{moeda(linha.b)}</TableCell>
                      <TableCell
                        align="right"
                        sx={{ color: corDiferenca(linha.diferenca, subirEBom) }}
                      >
                        {diferenca(linha.diferenca)}
                      </TableCell>
                      <TableCell align="right">{variacao(linha)}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </Secao>
        </Grid>
        <Grid item xs={12}>
          <Secao titulo="Comparação por categoria" subtitulo="Somente despesas">
            {dados.categorias.length ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Categoria</TableCell>
                      <TableCell align="right">{a}</TableCell>
                      <TableCell align="right">{b}</TableCell>
                      <TableCell align="right">Diferença</TableCell>
                      <TableCell align="right">Variação</TableCell>
                      <TableCell>Situação</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {dados.categorias.map((l) => (
                      <TableRow key={l.categoria}>
                        <TableCell>{l.categoria}</TableCell>
                        <TableCell align="right">{moeda(l.a)}</TableCell>
                        <TableCell align="right">{moeda(l.b)}</TableCell>
                        <TableCell align="right" sx={{ color: corDiferenca(l.diferenca) }}>
                          {diferenca(l.diferenca)}
                        </TableCell>
                        <TableCell align="right">{variacao(l)}</TableCell>
                        <TableCell>
                          <Chip
                            size="small"
                            variant="outlined"
                            label={l.situacao}
                            color={CORES_SITUACAO[l.situacao]}
                          />
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Vazio texto="Nenhuma despesa no histórico." />
            )}
          </Secao>
        </Grid>
        <Grid item xs={12} md={6}>
          <Ranking
            titulo="Maiores aumentos"
            subtitulo="Pelo aumento percentual"
            linhas={dados.aumentos}
            vazio="Nenhuma categoria aumentou."
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <Ranking
            titulo="Maiores reduções"
            subtitulo="Pela redução percentual"
            linhas={dados.reducoes}
            vazio="Nenhuma categoria diminuiu."
          />
        </Grid>
        <Grid item xs={12}>
          <Secao titulo="Categorias novas" subtitulo="Com gasto em apenas um dos dois meses">
            {dados.um_periodo.length ? (
              <TableContainer>
                <Table size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell>Categoria</TableCell>
                      <TableCell align="right">Valor</TableCell>
                      <TableCell>O que aconteceu</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {dados.um_periodo.map((c) => (
                      <TableRow key={c.categoria}>
                        <TableCell>{c.categoria}</TableCell>
                        <TableCell align="right">{moeda(c.valor)}</TableCell>
                        <TableCell>{leitura(c)}</TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            ) : (
              <Vazio texto="Todas as categorias tiveram gastos nos dois meses." />
            )}
          </Secao>
        </Grid>
      </Grid>
    </Box>
  );
};

export default IndicadoresComparacao;
