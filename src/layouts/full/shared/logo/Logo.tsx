import { FC } from 'react';
import { useSelector } from 'src/store/Store';
import { Link } from 'react-router-dom';
import { Box, Typography } from '@mui/material';
import { AppState } from 'src/store/Store';

export const LogoIcon: FC<{ size?: number }> = ({ size = 36 }) => (
  <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden="true">
    <defs>
      <linearGradient id="fin-logo-g" x1="0" y1="0" x2="1" y2="1">
        <stop offset="0" stopColor="#13DEB9" />
        <stop offset="1" stopColor="#5D87FF" />
      </linearGradient>
    </defs>
    <rect width="64" height="64" rx="16" fill="url(#fin-logo-g)" />
    <rect x="14" y="36" width="9" height="14" rx="2.5" fill="#fff" fillOpacity=".6" />
    <rect x="27.5" y="27" width="9" height="23" rx="2.5" fill="#fff" fillOpacity=".8" />
    <rect x="41" y="17" width="9" height="33" rx="2.5" fill="#fff" />
  </svg>
);

const Logo: FC = () => {
  const customizer = useSelector((state: AppState) => state.customizer);

  return (
    <Link
      to="/"
      style={{
        height: customizer.TopbarHeight,
        display: 'flex',
        alignItems: 'center',
        gap: 10,
        textDecoration: 'none',
        overflow: 'hidden',
        width: customizer.isCollapse ? 40 : 180,
      }}
    >
      <LogoIcon />
      {!customizer.isCollapse && (
        <Box>
          <Typography variant="h5" fontWeight={700} color="text.primary" noWrap>
            Financeiro
          </Typography>
        </Box>
      )}
    </Link>
  );
};

export default Logo;
