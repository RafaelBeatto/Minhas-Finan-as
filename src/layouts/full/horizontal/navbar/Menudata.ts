import { IconWallet } from '@tabler/icons-react';
import { uniqueId } from 'lodash';

const Menuitems = [
  {
    id: uniqueId(),
    title: 'Finan',
    icon: IconWallet,
    href: '/finan',
  },
];

export default Menuitems;
