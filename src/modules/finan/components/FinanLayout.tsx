import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import {
  Alert,
  Box,
  Button,
  CircularProgress,
  IconButton,
  Stack,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material';
import { IconDownload, IconEye, IconEyeOff, IconRefresh } from '@tabler/icons-react';
import { FinanProvider, useFinan } from '../hooks/useFinan';
import { ENDERECO_PLANILHA } from '../services/api';
import { dataHoraBr } from '../services/formato';

const ABAS = [
  { rotulo: 'Visão geral', href: '/finan' },
  { rotulo: 'Extrato', href: '/finan/extrato' },
  { rotulo: 'Histórico', href: '/finan/historico' },
  { rotulo: 'Cartão', href: '/finan/cartao' },
  { rotulo: 'Orçamento', href: '/finan/orcamento' },
  { rotulo: 'Assinaturas', href: '/finan/assinaturas' },
];

const Conteudo = () => {
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const { painel, erro, aviso, atualizando, atualizar, ocultar, alternarOcultar, limparMensagens } =
    useFinan();
  const atualizadoEm = painel?.atualizado_em
    ? `Saldos de ${dataHoraBr(painel.atualizado_em)}`
    : 'Saldos ainda não atualizados';

  return (
    <Box>
      <Stack
        direction={{ xs: 'column', sm: 'row' }}
        justifyContent="space-between"
        alignItems={{ sm: 'center' }}
        spacing={2}
        mb={2}
      >
        <Box>
          <Typography variant="h3">Finan</Typography>
          <Typography variant="subtitle2" color="text.secondary">
            {atualizando ? 'Buscando dados na Pluggy…' : atualizadoEm} · somente leitura
          </Typography>
        </Box>
        <Stack direction="row" spacing={1} alignItems="center">
          <Tooltip title={ocultar ? 'Mostrar valores' : 'Ocultar valores'}>
            <IconButton onClick={alternarOcultar} aria-label="Ocultar ou mostrar valores">
              {ocultar ? <IconEyeOff size={20} /> : <IconEye size={20} />}
            </IconButton>
          </Tooltip>
          <Button
            variant="outlined"
            startIcon={<IconDownload size={18} />}
            href={ENDERECO_PLANILHA}
            disabled={!painel}
          >
            Excel
          </Button>
          <Button
            variant="contained"
            startIcon={
              atualizando ? (
                <CircularProgress size={16} color="inherit" />
              ) : (
                <IconRefresh size={18} />
              )
            }
            onClick={atualizar}
            disabled={atualizando || !painel?.configurado}
          >
            Atualizar
          </Button>
        </Stack>
      </Stack>

      {erro && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={limparMensagens}>
          {erro}
        </Alert>
      )}
      {aviso && (
        <Alert severity="warning" sx={{ mb: 2 }} onClose={limparMensagens}>
          {aviso}
        </Alert>
      )}
      {painel && !painel.configurado && (
        <Alert severity="info" sx={{ mb: 2 }}>
          A conexão com a Pluggy não está configurada. Copie .env.example para
          finan-servidor/dados/.env, preencha e reinicie o servidor. O histórico salvo continua
          disponível.
        </Alert>
      )}

      <Tabs
        value={ABAS.some((a) => a.href === pathname) ? pathname : false}
        onChange={(_, destino) => navigate(destino)}
        variant="scrollable"
        allowScrollButtonsMobile
        sx={{ mb: 3, borderBottom: 1, borderColor: 'divider' }}
      >
        {ABAS.map((a) => (
          <Tab key={a.href} label={a.rotulo} value={a.href} />
        ))}
      </Tabs>

      {painel ? (
        <Outlet />
      ) : (
        !erro && (
          <Box textAlign="center" py={6}>
            <CircularProgress />
          </Box>
        )
      )}
    </Box>
  );
};

/** Tudo do módulo fica aqui dentro: ele não lê nem altera nada do resto do sistema. */
const FinanLayout = () => (
  <FinanProvider>
    <Conteudo />
  </FinanProvider>
);

export default FinanLayout;
