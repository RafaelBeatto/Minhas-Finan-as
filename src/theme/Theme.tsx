import _ from 'lodash';
import { createTheme } from '@mui/material/styles';
import { useSelector } from 'src/store/Store';
import { useEffect } from 'react';
import { AppState } from '../store/Store';
import components from './Components';
import typography from './Typography';
import { shadows, darkshadows } from './Shadows';
import { DarkThemeColors } from './DarkThemeColors';
import { LightThemeColors } from './LightThemeColors';
import { baseDarkTheme, baselightTheme, baseNuTheme } from './DefaultColors';
import * as locales from '@mui/material/locale';

export const BuildTheme = (config: any = {}) => {
  const themeOptions = LightThemeColors.find((theme) => theme.name === config.theme);
  const darkthemeOptions = DarkThemeColors.find((theme) => theme.name === config.theme);
  const customizer = useSelector((state: AppState) => state.customizer);
  const isNu = customizer.activeMode === 'nu';
  const isDark = customizer.activeMode === 'dark' || isNu;
  const defaultTheme = isNu ? baseNuTheme : isDark ? baseDarkTheme : baselightTheme;
  const defaultShadow = isDark ? darkshadows : shadows;
  // O tema Nu usa a própria paleta; não deixa a cor do tema escuro sobrescrevê-la.
  const themeSelect = isNu ? undefined : isDark ? darkthemeOptions : themeOptions;
  const baseMode = {
    palette: {
      mode: isDark ? 'dark' : 'light',
    },
    shape: {
      borderRadius: customizer.borderRadius,
    },
    shadows: defaultShadow,
    typography: typography,
  };
  const theme = createTheme(
    _.merge({}, baseMode, defaultTheme, locales, themeSelect, {
      direction: config.direction,
    }),
  );
  theme.components = components(theme);

  return theme;
};

const ThemeSettings = () => {
  const activDir = useSelector((state: AppState) => state.customizer.activeDir);
  const activeTheme = useSelector((state: AppState) => state.customizer.activeTheme);
  const theme = BuildTheme({
    direction: activDir,
    theme: activeTheme,
  });
  useEffect(() => {
    document.dir = activDir;
  }, [activDir]);

  return theme;
};

export { ThemeSettings };
