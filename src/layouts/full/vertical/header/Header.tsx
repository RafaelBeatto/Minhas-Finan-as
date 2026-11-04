import { IconButton, Box, AppBar, useMediaQuery, Toolbar, styled, Stack } from '@mui/material';

import { useSelector, useDispatch } from 'src/store/Store';
import {
  toggleSidebar,
  toggleMobileSidebar,
  setDarkMode,
} from 'src/store/customizer/CustomizerSlice';
import { IconMenu2, IconMoon, IconPalette, IconSun } from '@tabler/icons-react';
import { AppState } from 'src/store/Store';

const Header = () => {
  const lgUp = useMediaQuery((theme: any) => theme.breakpoints.up('lg'));

  // drawer
  const customizer = useSelector((state: AppState) => state.customizer);
  const dispatch = useDispatch();

  const AppBarStyled = styled(AppBar)(({ theme }) => ({
    boxShadow: 'none',
    background: theme.palette.background.paper,
    justifyContent: 'center',
    backdropFilter: 'blur(4px)',
    [theme.breakpoints.up('lg')]: {
      minHeight: customizer.TopbarHeight,
    },
  }));
  const ToolbarStyled = styled(Toolbar)(({ theme }) => ({
    width: '100%',
    color: theme.palette.text.secondary,
  }));

  return (
    <AppBarStyled position="sticky" color="default">
      <ToolbarStyled>
        {/* ------------------------------------------- */}
        {/* Toggle Button Sidebar */}
        {/* ------------------------------------------- */}
        <IconButton
          color="inherit"
          aria-label="menu"
          onClick={lgUp ? () => dispatch(toggleSidebar()) : () => dispatch(toggleMobileSidebar())}
        >
          <IconMenu2 size="20" />
        </IconButton>

        <Box flexGrow={1} />
        <Stack spacing={1} direction="row" alignItems="center">
          {/* Alterna: claro → escuro (preto) → Nu (roxo) → claro */}
          <IconButton
            size="large"
            color="inherit"
            aria-label="Alternar tema"
            onClick={() =>
              dispatch(
                setDarkMode(
                  customizer.activeMode === 'light'
                    ? 'dark'
                    : customizer.activeMode === 'dark'
                    ? 'nu'
                    : 'light',
                ),
              )
            }
          >
            {customizer.activeMode === 'light' ? (
              <IconMoon size="21" stroke="1.5" />
            ) : customizer.activeMode === 'dark' ? (
              <IconPalette size="21" stroke="1.5" />
            ) : (
              <IconSun size="21" stroke="1.5" />
            )}
          </IconButton>
        </Stack>
      </ToolbarStyled>
    </AppBarStyled>
  );
};

export default Header;
