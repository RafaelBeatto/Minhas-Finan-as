import { uniqueId } from 'lodash';

interface MenuitemsType {
  [x: string]: any;
  id?: string;
  navlabel?: boolean;
  subheader?: string;
  title?: string;
  icon?: any;
  href?: string;
  children?: MenuitemsType[];
  chip?: string;
  chipColor?: string;
  variant?: string;
  external?: boolean;
}
import {
  IconWallet,
  IconListDetails,
  IconHistory,
  IconArrowsDiff,
  IconCreditCard,
  IconTargetArrow,
  IconTags,
  IconRepeat,
  IconPigMoney,
} from '@tabler/icons-react';

const Menuitems: MenuitemsType[] = [
  {
    navlabel: true,
    subheader: 'Resumo',
  },
  {
    id: uniqueId(),
    title: 'Visão geral',
    icon: IconWallet,
    href: '/finan',
  },
  {
    navlabel: true,
    subheader: 'Movimentações',
  },
  {
    id: uniqueId(),
    title: 'Extrato',
    icon: IconListDetails,
    href: '/finan/extrato',
  },
  {
    id: uniqueId(),
    title: 'Cartão de crédito',
    icon: IconCreditCard,
    href: '/finan/cartao',
  },
  {
    id: uniqueId(),
    title: 'Histórico',
    icon: IconHistory,
    href: '/finan/historico',
  },
  {
    navlabel: true,
    subheader: 'Planejamento',
  },
  {
    id: uniqueId(),
    title: 'Caixinha',
    icon: IconPigMoney,
    href: '/finan/caixinha',
  },
  {
    id: uniqueId(),
    title: 'Orçamento',
    icon: IconTargetArrow,
    href: '/finan/orcamento',
  },
  {
    id: uniqueId(),
    title: 'Assinaturas',
    icon: IconRepeat,
    href: '/finan/assinaturas',
  },
  {
    navlabel: true,
    subheader: 'Análise',
  },
  {
    id: uniqueId(),
    title: 'Comparação de meses',
    icon: IconArrowsDiff,
    href: '/finan/comparacao',
  },
  {
    id: uniqueId(),
    title: 'Categorias',
    icon: IconTags,
    href: '/finan/categorias',
  },
];

export default Menuitems;
