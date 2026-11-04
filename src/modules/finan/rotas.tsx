import { lazy } from 'react';
import Loadable from 'src/layouts/full/shared/loadable/Loadable';

const FinanLayout = Loadable(lazy(() => import('./components/FinanLayout')));
const VisaoGeral = Loadable(lazy(() => import('./pages/VisaoGeral')));
const Extrato = Loadable(lazy(() => import('./pages/Extrato')));
const Historico = Loadable(lazy(() => import('./pages/Historico')));
const Cartao = Loadable(lazy(() => import('./pages/Cartao')));
const Comparacao = Loadable(lazy(() => import('./pages/Comparacao')));
const Orcamento = Loadable(lazy(() => import('./pages/Orcamento')));
const Caixinha = Loadable(lazy(() => import('./pages/Caixinha')));
const Categorias = Loadable(lazy(() => import('./pages/Categorias')));
const Assinaturas = Loadable(lazy(() => import('./pages/Assinaturas')));

const rotasFinan = {
  path: '/finan',
  element: <FinanLayout />,
  children: [
    { path: '', element: <VisaoGeral /> },
    { path: 'extrato', element: <Extrato /> },
    { path: 'historico', element: <Historico /> },
    { path: 'comparacao', element: <Comparacao /> },
    { path: 'cartao', element: <Cartao /> },
    { path: 'orcamento', element: <Orcamento /> },
    { path: 'caixinha', element: <Caixinha /> },
    { path: 'categorias', element: <Categorias /> },
    { path: 'assinaturas', element: <Assinaturas /> },
  ],
};

export default rotasFinan;
