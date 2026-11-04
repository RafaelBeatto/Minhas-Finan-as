import { useEffect, useState } from 'react';
import { Alert, Box, MenuItem, Stack, TextField } from '@mui/material';
import PageContainer from 'src/components/container/PageContainer';
import { GraficoBarras, Secao, TabelaAdaptavel, Vazio } from '../components/Visual';
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
      <Stack spacing={{ xs: 1.5, sm: 3 }}>
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
              <TabelaAdaptavel
                linhas={meses}
                chave={(m) => m.mes}
                aoClicar={(m) => setSelecionado(m.mes)}
                selecionada={(m) => m.mes === selecionado}
                colunas={[
                  { rotulo: 'Mês', render: (m) => nomeMes(m.mes) },
                  { rotulo: 'Resultado', align: 'right', render: (m) => moeda(m.resultado) },
                  { rotulo: 'Entradas', align: 'right', render: (m) => moeda(m.entradas) },
                  { rotulo: 'Saídas', align: 'right', render: (m) => moeda(m.saidas) },
                  {
                    rotulo: 'Saídas x mês anterior',
                    align: 'right',
                    render: (m) => (m.variacao === null ? '—' : diferenca(m.variacao)),
                  },
                ]}
              />
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
            <TabelaAdaptavel
              linhas={comparacao.linhas}
              chave={(l) => l.categoria}
              colunas={[
                { rotulo: 'Categoria', render: (l) => l.categoria },
                {
                  rotulo: 'Diferença',
                  align: 'right',
                  render: (l) => (
                    <Box
                      component="span"
                      sx={{ color: l.diferenca > 0 ? 'error.main' : 'success.main' }}
                    >
                      {diferenca(l.diferenca)}
                    </Box>
                  ),
                },
                { rotulo: 'Neste mês', align: 'right', render: (l) => moeda(l.atual) },
                { rotulo: 'Mês anterior', align: 'right', render: (l) => moeda(l.anterior) },
              ]}
            />
          </Secao>
        )}
      </Stack>
    </PageContainer>
  );
};

export default Historico;
