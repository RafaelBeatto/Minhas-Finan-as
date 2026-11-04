// eslint-disable-next-line @typescript-eslint/ban-ts-comment
// @ts-ignore
import * as React from 'react';
import {
  IconButton,
  Box,
  AppBar,
  useMediaQuery,
  Toolbar,
  styled,
  Stack,
  Theme,
} from '@mui/material';

import { useSelector, useDispatch } from 'src/store/Store';
import { toggleMobileSidebar, setDarkMode } from 'src/store/customizer/CustomizerSlice';
import { IconMenu2, IconMoon, IconPalette, IconSun } from '@tabler/icons-react';
import Logo from 'src/layouts/full/shared/logo/Logo';
import { AppState } from 'src/store/Store';

const Header = () => {
  const lgDown = useMediaQuery((theme: Theme) => theme.breakpoints.down('lg'));

  // drawer
  const customizer = useSelector((state: AppState) => state.customizer);
  const dispatch = useDispatch();

  const AppBarStyled = styled(AppBar)(({ theme }) => ({
    background: theme.palette.background.paper,
    justifyContent: 'center',
    backdropFilter: 'blur(4px)',

    [theme.breakpoints.up('lg')]: {
      minHeight: customizer.TopbarHeight,
    },
  }));
  const ToolbarStyled = styled(Toolbar)(({ theme }) => ({
    margin: '0 auto',
    width: '100%',
    color: `${theme.palette.text.secondary} !important`,
  }));

  return (
    <AppBarStyled position="sticky" color="default" elevation={8}>
      <ToolbarStyled
        sx={{
          maxWidth: customizer.isLayout === 'boxed' ? 'lg' : '100%!important',
        }}
      >
        <Box sx={{ width: lgDown ? '45px' : 'auto', overflow: 'hidden' }}>
          <Logo />
        </Box>
        {/* ------------------------------------------- */}
        {/* Toggle Button Sidebar */}
        {/* ------------------------------------------- */}
        {lgDown ? (
          <IconButton
            color="inherit"
            aria-label="menu"
            onClick={() => dispatch(toggleMobileSidebar())}
          >
            <IconMenu2 />
          </IconButton>
        ) : (
          ''
        )}
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
