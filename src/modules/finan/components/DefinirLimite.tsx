import { FormEvent, useState } from 'react';
import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from '@mui/material';
import { useFinan } from '../hooks/useFinan';
import { salvarLimite } from '../services/api';
import { LinhaOrcamento } from '../types';

const DefinirLimite = ({ linha, aoFechar }: { linha: LinhaOrcamento; aoFechar: () => void }) => {
  const { moeda, recarregar } = useFinan();
  const sugestao = linha.limite ?? Math.round(linha.media);
  const [valor, setValor] = useState(sugestao ? sugestao.toFixed(2).replace('.', ',') : '');
  const [erro, setErro] = useState('');

  const concluir = async (texto: string) => {
    try {
      await salvarLimite(linha.categoria, texto);
      await recarregar();
      aoFechar();
    } catch (e) {
      setErro((e as Error).message);
    }
  };

  const enviar = (evento: FormEvent) => {
    evento.preventDefault();
    if (!valor.trim()) {
      setErro('Digite um valor. Para tirar o limite, use Remover limite.');
      return;
    }
    concluir(valor);
  };

  return (
    <Dialog open onClose={aoFechar} fullWidth maxWidth="xs">
      <form onSubmit={enviar}>
        <DialogTitle>Limite de {linha.categoria}</DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" mb={2}>
            Gasto no mês: {moeda(linha.gasto)} · Média de 3 meses: {moeda(linha.media)}
          </Typography>
          {erro && (
            <Alert severity="error" sx={{ mb: 2 }}>
              {erro}
            </Alert>
          )}
          <TextField
            autoFocus
            fullWidth
            label="Limite por mês (R$)"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            inputProps={{ inputMode: 'decimal' }}
          />
        </DialogContent>
        <DialogActions>
          {linha.limite !== null && (
            <Button color="error" onClick={() => concluir('')} sx={{ mr: 'auto' }}>
              Remover limite
            </Button>
          )}
          <Button color="inherit" onClick={aoFechar}>
            Cancelar
          </Button>
          <Button variant="contained" type="submit">
            Salvar
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default DefinirLimite;
