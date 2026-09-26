"use client";

import { useEffect, useRef, useState } from "react";
import { Heart } from "lucide-react";

interface BotaoCurtirProps {
  curtido: boolean;
  total: number;
  onToggle: () => void;
  /** `true` enquanto a requisição está no ar, para evitar cliques repetidos. */
  ocupado?: boolean;
  tamanho?: "sm" | "md";
  titulo: string;
}

export default function BotaoCurtir({
  curtido,
  total,
  onToggle,
  ocupado = false,
  tamanho = "sm",
  titulo,
}: BotaoCurtirProps) {
  const [pulsando, setPulsando] = useState(false);
  const anterior = useRef(curtido);

  // Anima só na transição para "curtido" — não na carga inicial nem ao
  // descurtir, quando a animação de crescimento não faz sentido.
  useEffect(() => {
    if (curtido && !anterior.current) {
      setPulsando(true);
      const timer = setTimeout(() => setPulsando(false), 400);
      return () => clearTimeout(timer);
    }
    anterior.current = curtido;
  }, [curtido]);

  useEffect(() => {
    anterior.current = curtido;
  }, [curtido]);

  const icone = tamanho === "md" ? "h-5 w-5" : "h-4 w-4";
  const texto = tamanho === "md" ? "text-sm" : "text-xs";

  return (
    <button
      type="button"
      onClick={onToggle}
      disabled={ocupado}
      // O estado precisa ser legível por leitor de tela, não só pela cor.
      aria-pressed={curtido}
      aria-label={
        curtido
          ? `Remover curtida de ${titulo}. ${total} curtidas.`
          : `Curtir ${titulo}. ${total} curtidas.`
      }
      className={`group inline-flex items-center gap-1.5 rounded-full px-2 py-1 transition-colors disabled:opacity-60 ${
        curtido
          ? "text-rose-500"
          : "text-tenue hover:bg-superficie-alta hover:text-rose-500"
      }`}
    >
      <Heart
        className={`${icone} transition-transform ${
          pulsando ? "animate-pulsar-curtida" : ""
        } ${curtido ? "fill-current" : "group-hover:scale-110"}`}
        aria-hidden="true"
      />
      <span className={`${texto} font-semibold tabular-nums`}>{total}</span>
    </button>
  );
}
