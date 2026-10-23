"use client";

import { useCallback, useEffect, useState } from "react";
import { useToast } from "@/components/Toast";
import { ApiError, curtirNeologismo, listarNeologismos } from "@/lib/api";
import type { ConsultaNeologismos, Neologismo } from "@/types";

export function useNeologismos(consulta: ConsultaNeologismos = {}) {
  const [itens, setItens] = useState<Neologismo[]>([]);
  const [total, setTotal] = useState(0);
  const [pagina, setPagina] = useState(1);
  const [totalPaginas, setTotalPaginas] = useState(1);
  const [carregando, setCarregando] = useState(true);
  const [carregandoMais, setCarregandoMais] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [curtindo, setCurtindo] = useState<Set<number>>(new Set());

  // `gatilho` força uma nova busca sem que os filtros tenham mudado (botão
  // "tentar de novo").
  const [gatilho, setGatilho] = useState(0);

  const { avisar } = useToast();

  // Serializa os filtros: um objeto literal novo a cada render faria o efeito
  // rodar em loop.
  const chaveFiltros = JSON.stringify(consulta);

  // A página buscada anda junto da chave de filtros no mesmo estado. Guardar
  // as duas separadas exigiria um efeito só para zerar a página quando um
  // filtro muda — e um `setState` solto dentro de efeito provoca um render
  // em cascata. Aqui o ajuste acontece durante o render, que é o padrão que
  // o React recomenda para estado derivado de props.
  const [alvo, setAlvo] = useState({ chave: chaveFiltros, pagina: 1 });
  const paginaAlvo = alvo.chave === chaveFiltros ? alvo.pagina : 1;
  if (alvo.chave !== chaveFiltros) {
    setAlvo({ chave: chaveFiltros, pagina: 1 });
  }

  useEffect(() => {
    // Fetch em efeito é o padrão correto aqui: o token de sessão vive no
    // localStorage, então não há como buscar estes dados de um server
    // component. O `cancelado` descarta respostas fora de ordem.
    let cancelado = false;

    async function buscar() {
      if (paginaAlvo === 1) setCarregando(true);
      else setCarregandoMais(true);
      setErro(null);

      try {
        const filtros = JSON.parse(chaveFiltros) as ConsultaNeologismos;
        const resposta = await listarNeologismos({ ...filtros, page: paginaAlvo });
        if (cancelado) return;

        setItens((atuais) =>
          paginaAlvo === 1 ? resposta.results : [...atuais, ...resposta.results]
        );
        setTotal(resposta.count);
        setPagina(resposta.page);
        setTotalPaginas(resposta.total_pages);
      } catch (e) {
        if (cancelado) return;
        setErro(e instanceof ApiError ? e.message : "Erro inesperado ao carregar.");
      } finally {
        if (!cancelado) {
          setCarregando(false);
          setCarregandoMais(false);
        }
      }
    }

    buscar();

    return () => {
      cancelado = true;
    };
  }, [chaveFiltros, paginaAlvo, gatilho]);

  const carregarMais = useCallback(() => {
    setAlvo((atual) =>
      atual.pagina < totalPaginas
        ? { ...atual, pagina: atual.pagina + 1 }
        : atual
    );
  }, [totalPaginas]);

  const recarregar = useCallback(() => {
    setAlvo((atual) => ({ ...atual, pagina: 1 }));
    setGatilho((g) => g + 1);
  }, []);

  const curtir = useCallback(
    async (id: number) => {
      if (curtindo.has(id)) return;

      const alvo = itens.find((n) => n.id === id);
      if (!alvo) return;

      // Atualização otimista: o coração responde na hora e só é revertido se
      // o servidor recusar. Antes o clique não dava retorno visual nenhum e
      // as falhas eram engolidas por um `catch {}` vazio.
      const anterior = {
        curtido_por_mim: alvo.curtido_por_mim,
        total_likes: alvo.total_likes,
      };

      const aplicar = (mudanca: Partial<Neologismo>) =>
        setItens((atuais) =>
          atuais.map((n) => (n.id === id ? { ...n, ...mudanca } : n))
        );

      aplicar({
        curtido_por_mim: !anterior.curtido_por_mim,
        total_likes: anterior.total_likes + (anterior.curtido_por_mim ? -1 : 1),
      });
      setCurtindo((atuais) => new Set(atuais).add(id));

      try {
        const resposta = await curtirNeologismo(id);
        aplicar({
          curtido_por_mim: resposta.curtido_por_mim,
          total_likes: resposta.total_likes,
        });
      } catch (e) {
        aplicar(anterior);

        if (e instanceof ApiError && e.precisaLogin) {
          const destino =
            typeof window !== "undefined" ? window.location.pathname : "/";
          avisar("Entre na sua conta para curtir verbetes.", "info", {
            rotulo: "Entrar",
            href: `/login?next=${encodeURIComponent(destino)}`,
          });
        } else {
          avisar(
            e instanceof ApiError ? e.message : "Não foi possível curtir.",
            "erro"
          );
        }
      } finally {
        setCurtindo((atuais) => {
          const proximo = new Set(atuais);
          proximo.delete(id);
          return proximo;
        });
      }
    },
    [avisar, curtindo, itens]
  );

  return {
    itens,
    total,
    pagina,
    totalPaginas,
    temMais: pagina < totalPaginas,
    carregando,
    carregandoMais,
    erro,
    curtindo,
    curtir,
    carregarMais,
    recarregar,
  };
}

/** Atrasa a propagação de um valor — usado para não buscar a cada tecla. */
export function useDebounce<T>(valor: T, ms = 350): T {
  const [atrasado, setAtrasado] = useState(valor);

  useEffect(() => {
    const timer = setTimeout(() => setAtrasado(valor), ms);
    return () => clearTimeout(timer);
  }, [valor, ms]);

  return atrasado;
}
