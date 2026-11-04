import { FormEvent, useState } from 'react';
import {
  Alert,
  Autocomplete,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { useFinan } from '../hooks/useFinan';
import { excluirCategoria, renomearCategoria } from '../services/api';
import { LinhaCategoria } from '../types';

const EditarCategoria = ({
  linha,
  nomes,
  aoFechar,
}: {
  linha: LinhaCategoria;
  nomes: string[];
  aoFechar: () => void;
}) => {
  const { moeda, recarregar } = useFinan();
  const [nome, setNome] = useState(linha.categoria);
  const [erro, setErro] = useState('');
  const outras = nomes.filter((n) => n !== linha.categoria);
  const juntar = outras.includes(nome.trim());

  const concluir = async (acao: () => Promise<unknown>) => {
    try {
      await acao();
      await recarregar();
      aoFechar();
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  const enviar = (evento: FormEvent) => {
    evento.preventDefault();
    concluir(() => renomearCategoria(linha.categoria, nome));
  };

  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="xs">
      <form onSubmit={enviar}>
        <DialogTitle>{linha.categoria}</DialogTitle>
        <DialogContent>
          {erro && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {erro}
            </Alert>
          )}
          {linha.principais.length > 0 && (
            <Stack spacing={0.5} mb={2}>
              <Typography variant="subtitle2" color="text.secondary">
                Principais lançamentos no período
              </Typography>
              {linha.principais.map((p) => (
                <Stack key={p.descricao} direction="row" justifyContent="space-between" gap={2}>
                  <Typography variant="body2" noWrap>
                    {p.descricao} ({p.quantidade})
                  </Typography>
                  <Typography variant="body2" fontWeight={600} flexShrink={0}>
                    {moeda(p.total)}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          )}
          <Autocomplete
            freeSolo
            options={outras}
            value={nome}
            onInputChange={(_, valor) => setNome(valor)}
            renderInput={(params) => (
              <TextField
                {...params}
                autoFocus
                label="Nome"
                helperText={
                  juntar
                    ? `Os lançamentos passam para ${nome.trim()}. Dá para desfazer em Nomes alterados.`
                    : 'Digite um novo nome ou escolha outra categoria para juntar as duas.'
                }
              />
            )}
          />
        </DialogContent>
        <DialogActions>
          {linha.personalizada && !linha.em_uso && (
            <Button
              color="error"
              onClick={() => concluir(() => excluirCategoria(linha.categoria))}
              sx={{ mr: 'auto' }}
            >
              Excluir
            </Button>
          )}
          <Button color="inherit" onClick={aoFechar}>
            Cancelar
          </Button>
          <Button variant="contained" type="submit">
            {juntar ? 'Juntar' : 'Salvar'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default EditarCategoria;
