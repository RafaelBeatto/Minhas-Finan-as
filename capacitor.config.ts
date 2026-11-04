import type { CapacitorConfig } from '@capacitor/cli';

// O app Android abre o Finan do servidor na nuvem.
// Defina FINAN_URL antes de gerar o app, por exemplo: https://seu-finan.onrender.com
const urlServidor = process.env.FINAN_URL?.trim();

const config: CapacitorConfig = {
  appId: 'com.rafaelbeatto.finan',
  appName: 'Financeiro',
  webDir: 'dist',
  server: urlServidor
    ? { url: `${urlServidor}/finan`, cleartext: false, androidScheme: 'https' }
    : undefined,
};

export default config;
