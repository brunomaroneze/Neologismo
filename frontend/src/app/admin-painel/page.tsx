"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  Check,
  ExternalLink,
  Heart,
  Loader2,
  RotateCcw,
  Search,
  X,
} from "lucide-react";
import { useToast } from "@/components/Toast";
import { useAuth } from "@/hooks/useAuth";
import { useDebounce } from "@/hooks/useNeologismos";
import {
  ApiError,
  aprovarNeologismo,
  buscarResumoModeracao,
  listarNeologismos,
  reativarNeologismo,
  rejeitarNeologismo,
} from "@/lib/api";
import type { Neologismo, NeologismoStatus, ResumoModeracao } from "@/types";

const ABAS: { id: NeologismoStatus; label: string }[] = [
  { id: "pendente", label: "Pendentes" },
  { id: "aprovado", label: "Publicados" },
  { id: "rejeitado", label: "Rejeitados" },
];

export default function AdminPainel() {
  const router = useRouter();
  const { isAuthenticated, isAdmin, ready } = useAuth();
  const { avisar } = useToast();

  const [aba, setAba] = useState<NeologismoStatus>("pendente");
  const [itens, setItens] = useState<Neologismo[]>([]);
  const [resumo, setResumo] = useState<ResumoModeracao | null>(null);
  const [busca, setBusca] = useState("");
  const [carregando, setCarregando] = useState(true);
  const [erro, setErro] = useState<string | null>(null);
  const [acaoId, setAcaoId] = useState<number | null>(null);
  const [rejeitandoId, setRejeitandoId] = useState<number | null>(null);
  const [motivo, setMotivo] = useState("");

  const buscaAtrasada = useDebounce(busca);

  const [gatilho, setGatilho] = useState(0);
  const recarregar = useCallback(() => setGatilho((g) => g + 1), []);

  useEffect(() => {
    if (!ready) return;
    if (!isAuthenticated || !isAdmin) {
      router.replace("/");
      return;
    }

    let cancelado = false;

    async function buscar() {
      setCarregando(true);
      setErro(null);
      try {
        const [lista, contadores] = await Promise.all([
          listarNeologismos({ status: aba, search: buscaAtrasada, page_size: 50 }),
          buscarResumoModeracao(),
        ]);
        if (cancelado) return;
        setItens(lista.results);
        setResumo(contadores);
      } catch (e) {
        if (cancelado) return;
        setErro(e instanceof ApiError ? e.message : "Erro ao carregar.");
      } finally {
        if (!cancelado) setCarregando(false);
      }
    }

    buscar();

    return () => {
      cancelado = true;
    };
  }, [ready, isAuthenticated, isAdmin, router, aba, buscaAtrasada, gatilho]);

  /** Remove o item da aba atual e atualiza os contadores sem refazer o fetch. */
  function moverDaAba(id: number, de: NeologismoStatus, para: NeologismoStatus) {
    setItens((atuais) => atuais.filter((n) => n.id !== id));
    setResumo((atual) =>
      atual
        ? { ...atual, [de]: Math.max(0, atual[de] - 1), [para]: atual[para] + 1 }
        : atual
    );
  }

  async function aprovar(verbete: Neologismo) {
    setAcaoId(verbete.id);
    try {
      await aprovarNeologismo(verbete.id);
      moverDaAba(verbete.id, verbete.status, "aprovado");
      avisar(`"${verbete.titulo}" foi publicado.`, "sucesso");
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "Falha ao aprovar.", "erro");
    } finally {
      setAcaoId(null);
    }
  }

  async function rejeitar(verbete: Neologismo) {
    const texto = motivo.trim();
    if (texto.length < 5) {
      avisar("Escreva um motivo com pelo menos 5 caracteres.", "info");
      return;
    }

    setAcaoId(verbete.id);
    try {
      await rejeitarNeologismo(verbete.id, texto);
      moverDaAba(verbete.id, verbete.status, "rejeitado");
      setRejeitandoId(null);
      setMotivo("");
      avisar(`"${verbete.titulo}" foi rejeitado.`, "sucesso");
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "Falha ao rejeitar.", "erro");
    } finally {
      setAcaoId(null);
    }
  }

  async function reativar(verbete: Neologismo) {
    setAcaoId(verbete.id);
    try {
      await reativarNeologismo(verbete.id);
      moverDaAba(verbete.id, verbete.status, "aprovado");
      avisar(`"${verbete.titulo}" voltou para o dicionário.`, "sucesso");
    } catch (e) {
      avisar(e instanceof ApiError ? e.message : "Falha ao reativar.", "erro");
    } finally {
      setAcaoId(null);
    }
  }

  if (!ready || !isAuthenticated || !isAdmin) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="h-8 w-8 animate-spin text-marca" aria-hidden="true" />
        <span className="sr-only">Verificando acesso</span>
      </div>
    );
  }

  return (
    <section className="mx-auto max-w-5xl px-4 py-10 sm:px-6 lg:px-8">
      <span className="inline-block rounded-full border border-marca/30 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-marca">
        Administração
      </span>
      <h1 className="mt-4 font-display text-4xl font-black text-texto">
        Moderação
      </h1>

      {resumo && (
        <dl className="mt-6 grid grid-cols-2 gap-3 sm:grid-cols-4">
          {[
            { rotulo: "Pendentes", valor: resumo.pendente, destaque: true },
            { rotulo: "Publicados", valor: resumo.aprovado },
            { rotulo: "Rejeitados", valor: resumo.rejeitado },
            { rotulo: "Total", valor: resumo.total },
          ].map((item) => (
            <div
              key={item.rotulo}
              className={`cartao px-4 py-3 ${
                item.destaque && item.valor > 0 ? "border-marca/50" : ""
              }`}
            >
              <dt className="text-xs font-medium uppercase tracking-wider text-tenue">
                {item.rotulo}
              </dt>
              <dd
                className={`mt-1 font-display text-2xl font-black tabular-nums ${
                  item.destaque && item.valor > 0 ? "text-marca" : "text-texto"
                }`}
              >
                {item.valor}
              </dd>
            </div>
          ))}
        </dl>
      )}

      <div
        role="tablist"
        aria-label="Filtrar por status"
        className="mt-8 flex flex-wrap gap-2"
      >
        {ABAS.map((item) => (
          <button
            key={item.id}
            role="tab"
            aria-selected={aba === item.id}
            onClick={() => {
              setAba(item.id);
              setRejeitandoId(null);
              setMotivo("");
            }}
            className={`rounded-full px-4 py-2 text-sm font-medium transition-colors ${
              aba === item.id
                ? "bg-marca text-marca-contraste"
                : "border border-borda-forte text-suave hover:bg-superficie-alta"
            }`}
          >
            {item.label}
            {resumo && (
              <span className="ml-1.5 text-xs opacity-70">{resumo[item.id]}</span>
            )}
          </button>
        ))}
      </div>

      <div className="relative mt-5">
        <label htmlFor="busca-admin" className="sr-only">
          Filtrar verbetes
        </label>
        <Search
          className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-tenue"
          aria-hidden="true"
        />
        <input
          id="busca-admin"
          type="search"
          value={busca}
          onChange={(e) => setBusca(e.target.value)}
          placeholder="Filtrar por título, definição ou tag…"
          className="campo !py-3 !pl-12"
        />
      </div>

      {erro && (
        <div
          role="alert"
          className="mt-6 flex items-center justify-between gap-4 rounded-xl border border-red-500/30 bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-200"
        >
          <span>{erro}</span>
          <button onClick={recarregar} className="font-semibold hover:underline">
            Tentar de novo
          </button>
        </div>
      )}

      {carregando && (
        <div className="mt-6 space-y-4">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="cartao h-44 esqueleto" aria-hidden="true" />
          ))}
        </div>
      )}

      {!carregando && !erro && itens.length === 0 && (
        <div className="py-20 text-center">
          <p className="font-display text-xl font-bold text-texto">
            {busca
              ? "Nenhum resultado para essa busca"
              : aba === "pendente"
                ? "Fila de moderação zerada"
                : "Nada neste status"}
          </p>
          <p className="mt-2 text-sm text-suave">
            {aba === "pendente" && !busca
              ? "Nenhum verbete aguardando revisão. Bom trabalho."
              : "Ajuste os filtros para ver outros verbetes."}
          </p>
        </div>
      )}

      <div className="mt-6 space-y-4">
        {itens.map((verbete) => (
          <article key={verbete.id} className="cartao p-6">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0">
                <h2 className="font-display text-2xl font-bold text-texto">
                  {verbete.titulo.toLocaleLowerCase("pt-BR")}
                </h2>
                <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-xs text-tenue">
                  <span>
                    por{" "}
                    <strong className="font-medium text-suave">
                      {verbete.autor_nome}
                    </strong>
                  </span>
                  <span aria-hidden="true">·</span>
                  <span className="rounded-full bg-marca-suave px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider text-marca">
                    {verbete.classe_gramatical}
                  </span>
                  {verbete.tipologia && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span>{verbete.tipologia}</span>
                    </>
                  )}
                  {verbete.elaborado_por && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span>elaborado por {verbete.elaborado_por}</span>
                    </>
                  )}
                  <span aria-hidden="true">·</span>
                  <time dateTime={verbete.data_criacao}>
                    {new Date(verbete.data_criacao).toLocaleDateString("pt-BR")}
                  </time>
                  {verbete.moderado_por_nome && (
                    <>
                      <span aria-hidden="true">·</span>
                      <span>moderado por {verbete.moderado_por_nome}</span>
                    </>
                  )}
                </p>
              </div>

              <div className="flex shrink-0 items-center gap-3 text-xs text-tenue">
                <span className="flex items-center gap-1">
                  <Heart className="h-3.5 w-3.5" aria-hidden="true" />
                  {verbete.total_likes}
                </span>
                {verbete.status === "aprovado" && (
                  <Link
                    href={`/neologismo/${verbete.id}`}
                    className="inline-flex items-center gap-1 font-medium text-marca hover:underline"
                  >
                    Ver
                    <ExternalLink className="h-3 w-3" aria-hidden="true" />
                  </Link>
                )}
              </div>
            </div>

            <p className="mt-3 text-sm leading-relaxed text-suave">
              {verbete.definicao}
            </p>

            {verbete.contexto_uso && (
              <blockquote className="mt-3 rounded-xl bg-superficie-alta p-3">
                <p className="text-xs italic leading-relaxed text-suave">
                  &ldquo;{verbete.contexto_uso}&rdquo;
                </p>
              </blockquote>
            )}

            {verbete.contextos.length > 0 && (
              <ul className="mt-3 space-y-2">
                {verbete.contextos.map((contexto) => (
                  <li
                    key={contexto.id}
                    className="rounded-xl border border-borda p-3 text-xs"
                  >
                    <p className="leading-relaxed text-suave">{contexto.citacao}</p>
                    {(contexto.fonte || contexto.link) && (
                      <p className="mt-1.5 flex flex-wrap items-center gap-2 text-tenue">
                        {contexto.fonte}
                        {contexto.link && (
                          <a
                            href={contexto.link}
                            target="_blank"
                            rel="noopener noreferrer nofollow"
                            className="font-medium text-marca hover:underline"
                          >
                            abrir fonte
                          </a>
                        )}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            )}

            {verbete.tags.length > 0 && (
              <ul className="mt-4 flex flex-wrap gap-1.5">
                {verbete.tags.map((tag) => (
                  <li
                    key={tag}
                    className="rounded-full bg-superficie-alta px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-suave"
                  >
                    {tag}
                  </li>
                ))}
              </ul>
            )}

            {verbete.status === "rejeitado" && verbete.motivo_rejeicao && (
              <div className="mt-4 rounded-xl bg-red-50 p-3 dark:bg-red-950/40">
                <p className="text-xs font-semibold text-red-800 dark:text-red-200">
                  Motivo registrado
                </p>
                <p className="mt-0.5 text-xs leading-relaxed text-red-700 dark:text-red-300">
                  {verbete.motivo_rejeicao}
                </p>
              </div>
            )}

            {/* --- Ações --- */}
            {rejeitandoId === verbete.id ? (
              <div className="mt-5 space-y-3 border-t border-borda pt-4">
                <label
                  htmlFor={`motivo-${verbete.id}`}
                  className="block text-sm font-medium text-texto"
                >
                  Motivo da rejeição{" "}
                  <span className="font-normal text-tenue">
                    (o autor vai ler isto)
                  </span>
                </label>
                <textarea
                  id={`motivo-${verbete.id}`}
                  value={motivo}
                  onChange={(e) => setMotivo(e.target.value)}
                  rows={2}
                  autoFocus
                  placeholder="Ex.: já existe um verbete equivalente; falta fonte de uso real."
                  className="campo resize-y"
                />
                <div className="flex flex-wrap items-center gap-2">
                  <button
                    onClick={() => rejeitar(verbete)}
                    disabled={acaoId === verbete.id || motivo.trim().length < 5}
                    className="inline-flex items-center gap-1.5 rounded-full bg-red-600 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-red-700 disabled:opacity-50"
                  >
                    {acaoId === verbete.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : (
                      <X className="h-4 w-4" aria-hidden="true" />
                    )}
                    Confirmar rejeição
                  </button>
                  <button
                    onClick={() => {
                      setRejeitandoId(null);
                      setMotivo("");
                    }}
                    className="rounded-full border border-borda-forte px-5 py-2 text-sm font-medium text-suave transition-colors hover:bg-superficie-alta"
                  >
                    Cancelar
                  </button>
                </div>
              </div>
            ) : (
              <div className="mt-5 flex flex-wrap items-center gap-2 border-t border-borda pt-4">
                {verbete.status !== "aprovado" && (
                  <button
                    onClick={() =>
                      verbete.status === "rejeitado"
                        ? reativar(verbete)
                        : aprovar(verbete)
                    }
                    disabled={acaoId === verbete.id}
                    className="inline-flex items-center gap-1.5 rounded-full bg-emerald-600 px-5 py-2 text-sm font-semibold text-white transition-colors hover:bg-emerald-700 disabled:opacity-50"
                  >
                    {acaoId === verbete.id ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : verbete.status === "rejeitado" ? (
                      <RotateCcw className="h-4 w-4" aria-hidden="true" />
                    ) : (
                      <Check className="h-4 w-4" aria-hidden="true" />
                    )}
                    {verbete.status === "rejeitado" ? "Reativar" : "Aprovar"}
                  </button>
                )}

                {verbete.status !== "rejeitado" && (
                  <button
                    onClick={() => {
                      setRejeitandoId(verbete.id);
                      setMotivo("");
                    }}
                    disabled={acaoId === verbete.id}
                    className="inline-flex items-center gap-1.5 rounded-full border border-red-400/60 px-5 py-2 text-sm font-semibold text-red-600 transition-colors hover:bg-red-50 disabled:opacity-50 dark:text-red-400 dark:hover:bg-red-950/50"
                  >
                    <X className="h-4 w-4" aria-hidden="true" />
                    Rejeitar
                  </button>
                )}
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  );
}
