"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { AlertCircle, CheckCircle2, Info, X } from "lucide-react";

type Tipo = "sucesso" | "erro" | "info";

interface Aviso {
  id: number;
  tipo: Tipo;
  texto: string;
  acao?: { rotulo: string; href: string };
}

interface ToastContexto {
  avisar: (
    texto: string,
    tipo?: Tipo,
    acao?: { rotulo: string; href: string }
  ) => void;
}

const Contexto = createContext<ToastContexto | null>(null);

const DURACAO_MS = 5000;

const estilos: Record<Tipo, { icone: typeof Info; classe: string }> = {
  sucesso: {
    icone: CheckCircle2,
    classe: "border-emerald-500/30 bg-emerald-50 text-emerald-900 dark:bg-emerald-950 dark:text-emerald-100",
  },
  erro: {
    icone: AlertCircle,
    classe: "border-red-500/30 bg-red-50 text-red-900 dark:bg-red-950 dark:text-red-100",
  },
  info: {
    icone: Info,
    classe: "border-borda bg-superficie text-texto",
  },
};

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [avisos, setAvisos] = useState<Aviso[]>([]);
  const proximoId = useRef(0);
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>());

  const remover = useCallback((id: number) => {
    setAvisos((atuais) => atuais.filter((a) => a.id !== id));
    const timer = timers.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timers.current.delete(id);
    }
  }, []);

  const avisar = useCallback<ToastContexto["avisar"]>(
    (texto, tipo = "info", acao) => {
      const id = proximoId.current++;
      setAvisos((atuais) => [...atuais.slice(-2), { id, tipo, texto, acao }]);
      timers.current.set(
        id,
        setTimeout(() => remover(id), DURACAO_MS)
      );
    },
    [remover]
  );

  // Limpa os timers pendentes ao desmontar, para não chamar setState depois.
  useEffect(() => {
    const pendentes = timers.current;
    return () => {
      pendentes.forEach(clearTimeout);
      pendentes.clear();
    };
  }, []);

  const valor = useMemo(() => ({ avisar }), [avisar]);

  return (
    <Contexto.Provider value={valor}>
      {children}

      <div
        // `polite` para o leitor de tela anunciar sem interromper o que a
        // pessoa está fazendo.
        aria-live="polite"
        aria-atomic="false"
        className="pointer-events-none fixed inset-x-0 bottom-0 z-50 flex flex-col items-center gap-2 p-4 sm:items-end sm:p-6"
      >
        {avisos.map((aviso) => {
          const { icone: Icone, classe } = estilos[aviso.tipo];
          return (
            <div
              key={aviso.id}
              role="status"
              className={`animate-surgir pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-xl border px-4 py-3 shadow-lg ${classe}`}
            >
              <Icone className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              <p className="flex-1 text-sm leading-snug">{aviso.texto}</p>
              {aviso.acao && (
                <a
                  href={aviso.acao.href}
                  className="shrink-0 text-sm font-semibold underline underline-offset-2"
                >
                  {aviso.acao.rotulo}
                </a>
              )}
              <button
                onClick={() => remover(aviso.id)}
                aria-label="Fechar aviso"
                className="shrink-0 opacity-60 transition-opacity hover:opacity-100"
              >
                <X className="h-4 w-4" />
              </button>
            </div>
          );
        })}
      </div>
    </Contexto.Provider>
  );
}

export function useToast(): ToastContexto {
  const contexto = useContext(Contexto);
  if (!contexto) {
    throw new Error("useToast precisa estar dentro de <ToastProvider>.");
  }
  return contexto;
}
