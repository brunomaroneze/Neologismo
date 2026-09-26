"use client";

import { useEffect } from "react";
import Link from "next/link";

export default function Erro({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    // Em produção o texto do erro não aparece na tela; o console guarda o
    // `digest`, que é o que permite achar o stack trace no log do servidor.
    console.error(error);
  }, [error]);

  return (
    <section className="mx-auto flex max-w-md flex-col items-center px-4 py-32 text-center">
      <h1 className="font-display text-3xl font-black text-texto">
        Alguma coisa quebrou
      </h1>
      <p className="mt-3 text-sm leading-relaxed text-suave">
        O erro foi registrado. Você pode tentar de novo ou voltar ao início.
      </p>
      {error.digest && (
        <p className="mt-2 font-mono text-xs text-tenue">
          código: {error.digest}
        </p>
      )}
      <div className="mt-8 flex flex-col gap-3 sm:flex-row">
        <button
          onClick={reset}
          className="rounded-full bg-marca px-6 py-2.5 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90"
        >
          Tentar de novo
        </button>
        <Link
          href="/"
          className="rounded-full border border-borda-forte px-6 py-2.5 text-sm font-semibold text-texto transition-colors hover:bg-superficie-alta"
        >
          Voltar ao início
        </Link>
      </div>
    </section>
  );
}
