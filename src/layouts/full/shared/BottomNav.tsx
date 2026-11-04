import { useState } from 'react';
import {
  BottomNavigation,
  BottomNavigationAction,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Paper,
  useMediaQuery,
  Theme,
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  IconArrowsDiff,
  IconCreditCard,
  IconHistory,
  IconListDetails,
  IconMenu2,
  IconPigMoney,
  IconRepeat,
  IconTags,
  IconTargetArrow,
  IconWallet,
} from '@tabler/icons-react';

const ABAS = [
  { rotulo: 'Início', href: '/finan', icone: IconWallet },
  { rotulo: 'Extrato', href: '/finan/extrato', icone: IconListDetails },
  { rotulo: 'Cartão', href: '/finan/cartao', icone: IconCreditCard },
  { rotulo: 'Caixinha', href: '/finan/caixinha', icone: IconPigMoney },
  { rotulo: 'Orçamento', href: '/finan/orcamento', icone: IconTargetArrow },
  { rotulo: 'Histórico', href: '/finan/historico', icone: IconHistory },
  { rotulo: 'Assinaturas', href: '/finan/assinaturas', icone: IconRepeat },
  { rotulo: 'Comparar', href: '/finan/comparacao', icone: IconArrowsDiff },
  { rotulo: 'Categorias', href: '/finan/categorias', icone: IconTags },
];

const PRINCIPAIS = ABAS.slice(0, 4);
const RESTO = ABAS.slice(4);

/** Quatro módulos fixos no rodapé e um hambúrguer que abre os demais. Só no celular. */
const BottomNav = () => {
  const desktop = useMediaQuery((theme: Theme) => theme.breakpoints.up('lg'));
  const { pathname } = useLocation();
  const navigate = useNavigate();
  const [aberto, setAberto] = useState(false);
  if (desktop) return null;

  const rota = pathname.replace(/\/$/, '');
  const principal = PRINCIPAIS.findIndex((a) => a.href === rota);
  const noMenu = RESTO.some((a) => a.href === rota);
  const valor = principal !== -1 ? principal : noMenu ? PRINCIPAIS.length : false;
  const ir = (href: string) => {
    setAberto(false);
    navigate(href);
  };

  return (
    <>
      <Paper
        elevation={8}
        sx={{
          position: 'fixed',
          left: 0,
          right: 0,
          bottom: 0,
          zIndex: (t) => t.zIndex.appBar,
          borderRadius: 0,
          pb: 'env(safe-area-inset-bottom)',
        }}
      >
        <BottomNavigation
          showLabels
          value={valor}
          sx={{ height: 60, '& .MuiBottomNavigationAction-root': { minWidth: 0, px: 0.5 } }}
        >
          {PRINCIPAIS.map((a) => (
            <BottomNavigationAction
              key={a.href}
              label={a.rotulo}
              icon={<a.icone size={22} />}
              onClick={() => ir(a.href)}
            />
          ))}
          <BottomNavigationAction
            label="Menu"
            icon={<IconMenu2 size={22} />}
            onClick={() => setAberto(true)}
          />
        </BottomNavigation>
      </Paper>
      <Drawer
        anchor="bottom"
        open={aberto}
        onClose={() => setAberto(false)}
        PaperProps={{
          sx: { borderRadius: '16px 16px 0 0', pb: 'env(safe-area-inset-bottom)' },
        }}
      >
        <List sx={{ py: 1 }}>
          {RESTO.map((a) => (
            <ListItemButton key={a.href} selected={a.href === rota} onClick={() => ir(a.href)}>
              <ListItemIcon sx={{ minWidth: 40 }}>
                <a.icone size={22} />
              </ListItemIcon>
              <ListItemText primary={a.rotulo === 'Comparar' ? 'Comparação de meses' : a.rotulo} />
            </ListItemButton>
          ))}
        </List>
      </Drawer>
    </>
  );
};

export default BottomNav;
