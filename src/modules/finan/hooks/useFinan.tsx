import {
  createContext,
  ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react';
import dayjs from 'dayjs';
import { atualizarDados, buscarPainel } from '../services/api';
import { brl } from '../services/formato';
import { Painel } from '../types';

const HORAS_DADO_VELHO = 6;
const CHAVE_OCULTAR = 'finan.ocultar';
const OCULTO = 'R$ ••••';
const REAIS_NO_TEXTO = /[+-]?\s?R\$\s?[\d.]+(,\d+)?/g;

interface ContextoFinan {
  painel: Painel | null;
  erro: string;
  aviso: string;
  atualizando: boolean;
  versao: number;
  ocultar: boolean;
  alternarOcultar: () => void;
  moeda: (valor: number) => string;
  diferenca: (valor: number) => string;
  ocultavel: (texto: string) => string;
  recarregar: () => Promise<void>;
  atualizar: () => Promise<void>;
  limparMensagens: () => void;
}

const Contexto = createContext<ContextoFinan | null>(null);

const lerOcultar = () => {
  try {
    return localStorage.getItem(CHAVE_OCULTAR) === '1';
  } catch {
    return false;
  }
};

export const FinanProvider = ({ children }: { children: ReactNode }) => {
  const [painel, setPainel] = useState<Painel | null>(null);
  const [erro, setErro] = useState('');
  const [aviso, setAviso] = useState('');
  const [atualizando, setAtualizando] = useState(false);
  const [versao, setVersao] = useState(0);
  const [ocultar, setOcultar] = useState(lerOcultar);
  const conferiu = useRef(false);

  const recarregar = useCallback(async () => {
    try {
      setPainel(await buscarPainel());
      setVersao((v) => v + 1);
      setErro('');
    } catch (e) {
      setErro((e as Error).message);
    }
  }, []);

  const atualizar = useCallback(async () => {
    setAtualizando(true);
    setAviso('');
    try {
      const { aviso: alerta } = await atualizarDados();
      setAviso(alerta ?? '');
      await recarregar();
    } catch (e) {
      setErro((e as Error).message);
    } finally {
      setAtualizando(false);
    }
  }, [recarregar]);

  useEffect(() => {
    recarregar();
  }, [recarregar]);

  // Ao abrir, busca dados novos só se os salvos já estiverem velhos.
  useEffect(() => {
    if (!painel || conferiu.current) return;
    conferiu.current = true;
    const velho =
      !painel.atualizado_em ||
      dayjs().diff(dayjs(painel.atualizado_em), 'hour') >= HORAS_DADO_VELHO;
    if (painel.configurado && velho) atualizar();
  }, [painel, atualizar]);

  const alternarOcultar = useCallback(() => {
    setOcultar((atual) => {
      try {
        localStorage.setItem(CHAVE_OCULTAR, atual ? '0' : '1');
      } catch {
        // sem armazenamento a preferência vale só nesta visita
      }
      return !atual;
    });
  }, []);

  const valor = useMemo(
    () => ({
      painel,
      erro,
      aviso,
      atualizando,
      versao,
      ocultar,
      alternarOcultar,
      moeda: (numero: number) => (ocultar ? OCULTO : brl(numero)),
      diferenca: (numero: number) => (ocultar ? OCULTO : `${numero > 0 ? '+' : ''}${brl(numero)}`),
      // Textos prontos do servidor citam valores: também somem quando o usuário oculta.
      ocultavel: (texto: string) => (ocultar ? texto.replace(REAIS_NO_TEXTO, OCULTO) : texto),
      recarregar,
      atualizar,
      limparMensagens: () => {
        setErro('');
        setAviso('');
      },
    }),
    [painel, erro, aviso, atualizando, versao, ocultar, alternarOcultar, recarregar, atualizar],
  );

  return <Contexto.Provider value={valor}>{children}</Contexto.Provider>;
};

export const useFinan = () => {
  const contexto = useContext(Contexto);
  if (!contexto) throw new Error('useFinan precisa estar dentro de FinanProvider');
  return contexto;
};
