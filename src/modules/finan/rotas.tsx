import { lazy } from 'react';
import Loadable from 'src/layouts/full/shared/loadable/Loadable';

const FinanLayout = Loadable(lazy(() => import('./components/FinanLayout')));
const VisaoGeral = Loadable(lazy(() => import('./pages/VisaoGeral')));
const Extrato = Loadable(lazy(() => import('./pages/Extrato')));
const Historico = Loadable(lazy(() => import('./pages/Historico')));
const Cartao = Loadable(lazy(() => import('./pages/Cartao')));
const Orcamento = Loadable(lazy(() => import('./pages/Orcamento')));
const Assinaturas = Loadable(lazy(() => import('./pages/Assinaturas')));

const rotasFinan = {
  path: '/finan',
  element: <FinanLayout />,
  children: [
    { path: '', element: <VisaoGeral /> },
    { path: 'extrato', element: <Extrato /> },
    { path: 'historico', element: <Historico /> },
    { path: 'cartao', element: <Cartao /> },
    { path: 'orcamento', element: <Orcamento /> },
    { path: 'assinaturas', element: <Assinaturas /> },
  ],
};

export default rotasFinan;
