import { useState } from 'react';
import {
  Alert,
  Autocomplete,
  Button,
  Checkbox,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  TextField,
  Typography,
} from '@mui/material';
import { useFinan } from '../hooks/useFinan';
import { removerRegra, salvarRegra } from '../services/api';
import { Transacao } from '../types';

const CorrigirCategoria = ({
  transacao,
  aoFechar,
}: {
  transacao: Transacao;
  aoFechar: () => void;
}) => {
  const { painel, moeda, recarregar } = useFinan();
  const [categoria, setCategoria] = useState(transacao.categoria);
  const [todas, setTodas] = useState(true);
  const [erro, setErro] = useState('');

  const concluir = async (acao: Promise<unknown>) => {
    try {
      await acao;
      await recarregar();
      aoFechar();
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="xs">
      <DialogTitle>Corrigir categoria</DialogTitle>
      <DialogContent>
        <Typography fontWeight={600}>{transacao.descricao}</Typography>
        <Typography variant="body2" color="text.secondary" mb={2}>
          {moeda(transacao.valor)}
        </Typography>
        {erro && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {erro}
          </Alert>
        )}
        <Autocomplete
          freeSolo
          options={painel?.categorias ?? []}
          value={categoria}
          onInputChange={(_, valor) => setCategoria(valor)}
          renderInput={(params) => (
            <TextField
              {...params}
              label="Categoria"
              helperText='Escolha ou digite. "Movimentação interna" tira dos totais.'
            />
          )}
        />
        <FormControlLabel
          sx={{ mt: 1 }}
          control={<Checkbox checked={todas} onChange={(e) => setTodas(e.target.checked)} />}
          label="Aplicar a todas com esta descrição, inclusive as futuras"
        />
      </DialogContent>
      <DialogActions>
        {transacao.corrigida && (
          <Button
            color="inherit"
            onClick={() => concluir(removerRegra(transacao.id))}
            sx={{ mr: 'auto' }}
          >
            Voltar à original
          </Button>
        )}
        <Button color="inherit" onClick={aoFechar}>
          Cancelar
        </Button>
        <Button
          variant="contained"
          onClick={() => concluir(salvarRegra(transacao.id, categoria, todas))}
        >
          Salvar
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default CorrigirCategoria;
