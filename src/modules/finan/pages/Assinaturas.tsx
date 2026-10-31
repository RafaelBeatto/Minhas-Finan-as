import { useState } from 'react';
import {
  Alert,
  Button,
  Chip,
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
import { Indicadores, Secao, Vazio } from '../components/Visual';
import { useFinan } from '../hooks/useFinan';
import { ignorarAssinatura, restaurarAssinaturas } from '../services/api';
import { dataBr } from '../services/formato';
import { Assinatura } from '../types';

const Assinaturas = () => {
  const { painel, moeda, recarregar } = useFinan();
  const [erro, setErro] = useState('');
  const [filtro, setFiltro] = useState('');
  if (!painel) return null;
  const custo = painel.custo_assinaturas;
  const visiveis = painel.assinaturas.filter(
    (a) =>
      !filtro ||
      (filtro === 'ativas' && a.ativa) ||
      (filtro === 'paradas' && !a.ativa) ||
      (filtro === 'aumentaram' && a.ativa && a.aumento > 0),
  );

  const executar = async (acao: Promise<unknown>) => {
    try {
      await acao;
      await recarregar();
      setErro('');
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  const situacao = (a: Assinatura) => {
    if (!a.ativa) return <Chip size="small" variant="outlined" label="Sem cobrança recente" />;
    if (a.aumento) {
      return (
        <Chip
          size="small"
          variant="outlined"
          color="warning"
          label={`Aumentou ${moeda(a.aumento)}`}
        />
      );
    }
    return <Chip size="small" variant="outlined" color="success" label="Ativa" />;
  };

  return (
    <PageContainer title="Assinaturas · Finan">
      <Stack spacing={3}>
        {erro && <Alert severity="error">{erro}</Alert>}
        <Indicadores
          itens={[
            { titulo: 'Custo por mês', valor: moeda(custo) },
            { titulo: 'Custo em 12 meses', valor: moeda(custo * 12) },
            {
              titulo: 'Cobranças ativas',
              valor: painel.assinaturas.filter((a) => a.ativa).length,
            },
          ]}
        />
        <Secao
          titulo="Cobranças recorrentes"
          subtitulo="Detectadas pelo app: mesma cobrança mensal em pelo menos 3 meses"
          acao={
            <Stack direction="row" spacing={1} alignItems="center">
              {painel.ignoradas > 0 && (
                <Button size="small" onClick={() => executar(restaurarAssinaturas())}>
                  {`Restaurar ignoradas (${painel.ignoradas})`}
                </Button>
              )}
              <TextField
                select
                size="small"
                label="Situação"
                value={filtro}
                onChange={(e) => setFiltro(e.target.value)}
                sx={{ minWidth: 170 }}
              >
                <MenuItem value="">Todas</MenuItem>
                <MenuItem value="ativas">Ativas</MenuItem>
                <MenuItem value="aumentaram">Aumentaram</MenuItem>
                <MenuItem value="paradas">Sem cobrança recente</MenuItem>
              </TextField>
            </Stack>
          }
        >
          {visiveis.length ? (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Cobrança</TableCell>
                    <TableCell>Categoria</TableCell>
                    <TableCell align="right">Valor</TableCell>
                    <TableCell align="right">Última</TableCell>
                    <TableCell align="right">Próxima</TableCell>
                    <TableCell>Situação</TableCell>
                    <TableCell />
                  </TableRow>
                </TableHead>
                <TableBody>
                  {visiveis.map((a) => (
                    <TableRow key={a.chave}>
                      <TableCell>{a.descricao}</TableCell>
                      <TableCell>{a.categoria}</TableCell>
                      <TableCell align="right">{moeda(a.valor)}</TableCell>
                      <TableCell align="right">{dataBr(a.ultima)}</TableCell>
                      <TableCell align="right">{a.ativa ? dataBr(a.proxima) : '—'}</TableCell>
                      <TableCell>{situacao(a)}</TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          color="inherit"
                          onClick={() => executar(ignorarAssinatura(a.chave))}
                        >
                          Não é assinatura
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          ) : (
            <Vazio
              texto={
                painel.assinaturas.length
                  ? 'Nenhuma cobrança neste filtro.'
                  : 'Nenhuma cobrança recorrente encontrada.'
              }
            />
          )}
        </Secao>
      </Stack>
    </PageContainer>
  );
};

export default Assinaturas;
