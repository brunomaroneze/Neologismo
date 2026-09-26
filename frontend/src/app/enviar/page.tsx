"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import {
  CheckCircle2,
  Loader2,
  Plus,
  Trash2,
  X,
} from "lucide-react";
import { useToast } from "@/components/Toast";
import { useAuth } from "@/hooks/useAuth";
import { ApiError, buscarFacetas, criarNeologismo } from "@/lib/api";
import type { ContextoCreate } from "@/types";

const CLASSES = [
  "Substantivo",
  "Substantivo uniforme",
  "Verbo transitivo direto",
  "Verbo intransitivo",
  "Adjetivo",
  "Adjetivo uniforme",
  "Advérbio",
  "Interjeição",
  "Locução",
];

const MAX_TAGS = 8;
const MAX_TITULO = 50;
const MAX_CITACOES = 10;

interface CitacaoForm extends ContextoCreate {
  chave: number;
}

export default function EnviarPage() {
  const { isAuthenticated, ready } = useAuth();
  const router = useRouter();
  const { avisar } = useToast();

  const [titulo, setTitulo] = useState("");
  const [classe, setClasse] = useState("");
  const [definicao, setDefinicao] = useState("");
  const [contextoUso, setContextoUso] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [tagAtual, setTagAtual] = useState("");
  const [sugestoes, setSugestoes] = useState<string[]>([]);
  const [citacoes, setCitacoes] = useState<CitacaoForm[]>([]);

  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [errosCampo, setErrosCampo] = useState<Record<string, string>>({});
  const [enviando, setEnviando] = useState(false);
  const [sucesso, setSucesso] = useState(false);

  useEffect(() => {
    buscarFacetas()
      .then((facetas) => setSugestoes(facetas.tags.slice(0, 10).map((t) => t.nome)))
      .catch(() => {
        // Sugestões são um extra; o campo continua aceitando texto livre.
      });
  }, []);

  function adicionarTag(bruta: string) {
    const tag = bruta.trim().replace(/,+$/, "");
    if (!tag) return;
    if (tags.length >= MAX_TAGS) {
      avisar(`Use no máximo ${MAX_TAGS} tags.`, "info");
      return;
    }
    // Comparação sem caixa: evita "Gíria" e "gíria" como tags distintas.
    if (tags.some((t) => t.toLocaleLowerCase() === tag.toLocaleLowerCase())) {
      setTagAtual("");
      return;
    }
    setTags((atuais) => [...atuais, tag]);
    setTagAtual("");
  }

  function aoTeclarTag(evento: React.KeyboardEvent<HTMLInputElement>) {
    if (evento.key === "Enter" || evento.key === ",") {
      evento.preventDefault();
      adicionarTag(tagAtual);
    } else if (evento.key === "Backspace" && tagAtual === "" && tags.length) {
      // Backspace no campo vazio remove a última tag, como em qualquer
      // campo de chips.
      setTags((atuais) => atuais.slice(0, -1));
    }
  }

  function atualizarCitacao(chave: number, campo: keyof ContextoCreate, valor: string) {
    setCitacoes((atuais) =>
      atuais.map((c) => (c.chave === chave ? { ...c, [campo]: valor } : c))
    );
  }

  function validar(): boolean {
    const erros: Record<string, string> = {};
    if (titulo.trim().length < 2) erros.titulo = "Informe a palavra (mínimo 2 caracteres).";
    if (!classe.trim()) erros.classe_gramatical = "Escolha a classe gramatical.";
    if (definicao.trim().length < 10)
      erros.definicao = "Descreva o significado com pelo menos 10 caracteres.";

    setErrosCampo(erros);
    return Object.keys(erros).length === 0;
  }

  async function enviar(evento: React.FormEvent) {
    evento.preventDefault();
    setErroGeral(null);

    if (!validar()) {
      setErroGeral("Revise os campos destacados abaixo.");
      return;
    }

    // Tag ainda digitada, sem Enter, entra no envio — perder o que a pessoa
    // escreveu por causa de uma tecla não apertada é frustrante.
    const tagsFinais = tagAtual.trim()
      ? [...tags, tagAtual.trim()].slice(0, MAX_TAGS)
      : tags;

    setEnviando(true);
    try {
      await criarNeologismo({
        titulo: titulo.trim(),
        classe_gramatical: classe.trim(),
        definicao: definicao.trim(),
        contexto_uso: contextoUso.trim(),
        tags: tagsFinais,
        contextos: citacoes
          .filter((c) => c.citacao.trim())
          .map(({ citacao, fonte, link }) => ({
            citacao: citacao.trim(),
            fonte: fonte?.trim() || "",
            link: link?.trim() || "",
          })),
      });
      setSucesso(true);
      window.scrollTo({ top: 0, behavior: "smooth" });
    } catch (e) {
      if (e instanceof ApiError) {
        setErroGeral(e.message);
        // Mapeia os erros por campo devolvidos pelo DRF para os inputs.
        const doServidor: Record<string, string> = {};
        for (const [campo, mensagens] of Object.entries(e.campos)) {
          doServidor[campo] = mensagens[0];
        }
        setErrosCampo(doServidor);

        if (e.precisaLogin) {
          router.push("/login?next=/enviar");
        }
      } else {
        setErroGeral("Erro inesperado ao enviar.");
      }
    } finally {
      setEnviando(false);
    }
  }

  function novoEnvio() {
    setTitulo("");
    setClasse("");
    setDefinicao("");
    setContextoUso("");
    setTags([]);
    setTagAtual("");
    setCitacoes([]);
    setErrosCampo({});
    setErroGeral(null);
    setSucesso(false);
  }

  if (!ready) {
    return (
      <div className="flex items-center justify-center py-32">
        <Loader2 className="h-8 w-8 animate-spin text-marca" aria-hidden="true" />
        <span className="sr-only">Carregando</span>
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <section className="mx-auto max-w-md px-4 py-24 text-center">
        <h1 className="font-display text-3xl font-black text-texto">
          Entre para enviar
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-suave">
          Só quem tem conta pode sugerir um verbete — assim conseguimos dar
          crédito à autoria e acompanhar a moderação.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/login?next=/enviar"
            className="w-full rounded-full bg-marca px-6 py-2.5 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90 sm:w-auto"
          >
            Entrar
          </Link>
          <Link
            href="/cadastro?next=/enviar"
            className="w-full rounded-full border border-borda-forte px-6 py-2.5 text-sm font-semibold text-texto transition-colors hover:bg-superficie-alta sm:w-auto"
          >
            Criar conta
          </Link>
        </div>
      </section>
    );
  }

  if (sucesso) {
    return (
      <section className="mx-auto max-w-md px-4 py-24 text-center">
        <CheckCircle2
          className="mx-auto mb-5 h-14 w-14 text-emerald-500"
          aria-hidden="true"
        />
        <h1 className="font-display text-3xl font-black text-texto">
          Neologismo enviado!
        </h1>
        <p className="mt-3 text-sm leading-relaxed text-suave">
          Ele entra na fila de moderação e aparece no dicionário assim que for
          aprovado. Você acompanha o andamento em Minhas palavras.
        </p>
        <div className="mt-8 flex flex-col items-center justify-center gap-3 sm:flex-row">
          <Link
            href="/minhas-palavras"
            className="w-full rounded-full bg-marca px-6 py-2.5 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90 sm:w-auto"
          >
            Ver meus envios
          </Link>
          <button
            onClick={novoEnvio}
            className="w-full rounded-full border border-borda-forte px-6 py-2.5 text-sm font-semibold text-texto transition-colors hover:bg-superficie-alta sm:w-auto"
          >
            Enviar outra
          </button>
        </div>
      </section>
    );
  }

  const erroDe = (campo: string) => errosCampo[campo];

  return (
    <section className="mx-auto max-w-2xl px-4 py-12 sm:px-6">
      <span className="inline-block rounded-full border border-marca/30 px-4 py-1.5 text-xs font-bold uppercase tracking-wider text-marca">
        Enviar neologismo
      </span>
      <h1 className="mt-4 font-display text-4xl font-black leading-tight text-texto">
        Registre uma nova palavra
      </h1>
      <p className="mt-2 text-sm text-suave">
        Sua sugestão passa por moderação antes de ser publicada. Campos com{" "}
        <span className="text-marca">*</span> são obrigatórios.
      </p>

      {erroGeral && (
        <div
          role="alert"
          className="mt-6 rounded-xl border border-red-500/30 bg-red-50 px-4 py-3 text-sm text-red-700 dark:bg-red-950/40 dark:text-red-200"
        >
          {erroGeral}
        </div>
      )}

      <form onSubmit={enviar} noValidate className="mt-8 space-y-6">
        <Campo
          id="titulo"
          rotulo="Palavra"
          obrigatorio
          erro={erroDe("titulo")}
          ajuda={`${titulo.length}/${MAX_TITULO}`}
        >
          <input
            id="titulo"
            value={titulo}
            maxLength={MAX_TITULO}
            onChange={(e) => setTitulo(e.target.value)}
            placeholder="Ex.: biscoitar"
            aria-invalid={!!erroDe("titulo")}
            className="campo"
          />
        </Campo>

        <Campo
          id="classe"
          rotulo="Classe gramatical"
          obrigatorio
          erro={erroDe("classe_gramatical")}
        >
          <input
            id="classe"
            list="classes-gramaticais"
            value={classe}
            onChange={(e) => setClasse(e.target.value)}
            placeholder="Verbo, substantivo, adjetivo…"
            aria-invalid={!!erroDe("classe_gramatical")}
            className="campo"
          />
          <datalist id="classes-gramaticais">
            {CLASSES.map((c) => (
              <option key={c} value={c} />
            ))}
          </datalist>
        </Campo>

        <Campo
          id="definicao"
          rotulo="Definição"
          obrigatorio
          erro={erroDe("definicao")}
          ajuda={`${definicao.trim().length} caracteres (mínimo 10)`}
        >
          <textarea
            id="definicao"
            value={definicao}
            onChange={(e) => setDefinicao(e.target.value)}
            rows={4}
            placeholder="O que a palavra significa? De onde ela parece ter vindo?"
            aria-invalid={!!erroDe("definicao")}
            className="campo resize-y"
          />
        </Campo>

        <Campo
          id="contexto"
          rotulo="Frase de exemplo"
          erro={erroDe("contexto_uso")}
          ajuda="Uma frase curta mostrando a palavra em uso."
        >
          <textarea
            id="contexto"
            value={contextoUso}
            onChange={(e) => setContextoUso(e.target.value)}
            rows={2}
            placeholder="Ela passou a tarde biscoitando no Instagram."
            className="campo resize-y"
          />
        </Campo>

        <Campo
          id="tags"
          rotulo="Tags"
          erro={erroDe("tags")}
          ajuda={`Enter ou vírgula para adicionar. ${tags.length}/${MAX_TAGS}`}
        >
          <div className="flex flex-wrap items-center gap-2 rounded-xl border border-borda-forte bg-superficie p-2 focus-within:border-marca">
            {tags.map((tag) => (
              <span
                key={tag}
                className="inline-flex items-center gap-1 rounded-full bg-marca-suave py-1 pl-3 pr-1.5 text-xs font-semibold text-marca"
              >
                {tag}
                <button
                  type="button"
                  onClick={() => setTags((a) => a.filter((t) => t !== tag))}
                  aria-label={`Remover a tag ${tag}`}
                  className="rounded-full p-0.5 transition-colors hover:bg-marca/20"
                >
                  <X className="h-3 w-3" />
                </button>
              </span>
            ))}
            <input
              id="tags"
              value={tagAtual}
              onChange={(e) => setTagAtual(e.target.value)}
              onKeyDown={aoTeclarTag}
              onBlur={() => adicionarTag(tagAtual)}
              placeholder={tags.length ? "" : "Internetês, anglicismo…"}
              className="min-w-[10rem] flex-1 bg-transparent px-2 py-1 text-sm text-texto outline-none placeholder:text-tenue"
            />
          </div>

          {sugestoes.length > 0 && tags.length < MAX_TAGS && (
            <div className="mt-2 flex flex-wrap gap-1.5">
              {sugestoes
                .filter(
                  (s) =>
                    !tags.some(
                      (t) => t.toLocaleLowerCase() === s.toLocaleLowerCase()
                    )
                )
                .slice(0, 6)
                .map((sugestao) => (
                  <button
                    key={sugestao}
                    type="button"
                    onClick={() => adicionarTag(sugestao)}
                    className="rounded-full border border-borda px-2.5 py-1 text-xs text-suave transition-colors hover:border-marca hover:text-marca"
                  >
                    + {sugestao}
                  </button>
                ))}
            </div>
          )}
        </Campo>

        <fieldset className="rounded-2xl border border-borda p-5">
          <legend className="px-2 text-sm font-semibold text-texto">
            Citações com fonte{" "}
            <span className="font-normal text-tenue">(opcional)</span>
          </legend>
          <p className="mb-4 text-xs text-suave">
            Trechos reais onde a palavra aparece — post, matéria, conversa.
            Fortalecem muito o verbete na revisão.
          </p>

          <div className="space-y-4">
            {citacoes.map((citacao, indice) => (
              <div
                key={citacao.chave}
                className="animate-surgir rounded-xl bg-superficie-alta p-4"
              >
                <div className="mb-2 flex items-center justify-between">
                  <span className="text-xs font-semibold text-suave">
                    Citação {indice + 1}
                  </span>
                  <button
                    type="button"
                    onClick={() =>
                      setCitacoes((a) => a.filter((c) => c.chave !== citacao.chave))
                    }
                    aria-label={`Remover a citação ${indice + 1}`}
                    className="rounded-lg p-1.5 text-tenue transition-colors hover:bg-red-100 hover:text-red-600 dark:hover:bg-red-950"
                  >
                    <Trash2 className="h-4 w-4" />
                  </button>
                </div>

                <textarea
                  value={citacao.citacao}
                  onChange={(e) =>
                    atualizarCitacao(citacao.chave, "citacao", e.target.value)
                  }
                  rows={2}
                  placeholder="Trecho onde a palavra aparece."
                  aria-label={`Texto da citação ${indice + 1}`}
                  className="campo resize-y"
                />

                <div className="mt-3 grid grid-cols-1 gap-3 sm:grid-cols-2">
                  <input
                    value={citacao.fonte ?? ""}
                    onChange={(e) =>
                      atualizarCitacao(citacao.chave, "fonte", e.target.value)
                    }
                    placeholder="Fonte — @usuario no X"
                    aria-label={`Fonte da citação ${indice + 1}`}
                    className="campo"
                  />
                  <input
                    type="url"
                    value={citacao.link ?? ""}
                    onChange={(e) =>
                      atualizarCitacao(citacao.chave, "link", e.target.value)
                    }
                    placeholder="https://…"
                    aria-label={`Link da citação ${indice + 1}`}
                    className="campo"
                  />
                </div>
              </div>
            ))}
          </div>

          {citacoes.length < MAX_CITACOES && (
            <button
              type="button"
              onClick={() =>
                setCitacoes((a) => [
                  ...a,
                  { chave: Date.now(), citacao: "", fonte: "", link: "" },
                ])
              }
              className="mt-4 inline-flex items-center gap-1.5 rounded-full border border-dashed border-borda-forte px-4 py-2 text-sm font-medium text-suave transition-colors hover:border-marca hover:text-marca"
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              Adicionar citação
            </button>
          )}
        </fieldset>

        <div className="flex flex-col gap-3 border-t border-borda pt-6 sm:flex-row sm:items-center">
          <button
            type="submit"
            disabled={enviando}
            className="inline-flex items-center justify-center gap-2 rounded-full bg-marca px-8 py-3 text-sm font-semibold text-marca-contraste transition-opacity hover:opacity-90 disabled:opacity-60"
          >
            {enviando && (
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            )}
            {enviando ? "Enviando…" : "Enviar neologismo"}
          </button>
          <Link
            href="/"
            className="text-center text-sm font-medium text-suave transition-colors hover:text-marca sm:text-left"
          >
            Cancelar
          </Link>
        </div>
      </form>
    </section>
  );
}

function Campo({
  id,
  rotulo,
  obrigatorio,
  erro,
  ajuda,
  children,
}: {
  id: string;
  rotulo: string;
  obrigatorio?: boolean;
  erro?: string;
  ajuda?: string;
  children: React.ReactNode;
}) {
  return (
    <div>
      <div className="mb-1.5 flex items-baseline justify-between gap-3">
        <label htmlFor={id} className="text-sm font-medium text-texto">
          {rotulo}
          {obrigatorio && (
            <span className="text-marca" aria-hidden="true">
              {" "}
              *
            </span>
          )}
        </label>
        {ajuda && !erro && (
          <span className="text-xs text-tenue">{ajuda}</span>
        )}
      </div>
      {children}
      {erro && (
        <p role="alert" className="mt-1.5 text-xs font-medium text-red-600 dark:text-red-400">
          {erro}
        </p>
      )}
    </div>
  );
}
