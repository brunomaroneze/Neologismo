// Melhorias progressivas do site. Tudo aqui é opcional: sem JavaScript, os
// formulários e links continuam funcionando por envio e navegação normais.
(function () {
  "use strict";

  function csrf(form) {
    var campo = form.querySelector("input[name=csrfmiddlewaretoken]");
    return campo ? campo.value : "";
  }

  // --- Menu do celular -------------------------------------------------------
  var botaoMenu = document.querySelector("[data-menu]");
  if (botaoMenu) {
    var navegacao = document.getElementById(botaoMenu.getAttribute("aria-controls"));
    function alternarMenu(aberto) {
      botaoMenu.setAttribute("aria-expanded", aberto ? "true" : "false");
      botaoMenu.textContent = botaoMenu.getAttribute(aberto ? "data-rotulo-fechar" : "data-rotulo-abrir");
      navegacao.setAttribute("data-aberto", aberto ? "true" : "false");
    }
    botaoMenu.addEventListener("click", function () {
      alternarMenu(botaoMenu.getAttribute("aria-expanded") !== "true");
    });
    document.addEventListener("keydown", function (evento) {
      if (evento.key === "Escape" && botaoMenu.getAttribute("aria-expanded") === "true") {
        alternarMenu(false);
        botaoMenu.focus();
      }
    });
  }

  // --- Curtir sem recarregar -------------------------------------------------
  document.addEventListener("submit", function (evento) {
    var form = evento.target;
    if (!form.matches("[data-curtir]")) return;
    evento.preventDefault();

    var botao = form.querySelector("button");
    botao.disabled = true;
    fetch(form.action, {
      method: "POST",
      headers: { "Accept": "application/json", "X-CSRFToken": csrf(form) },
      body: new FormData(form),
      credentials: "same-origin",
    })
      .then(function (resposta) {
        if (!resposta.ok) throw new Error(String(resposta.status));
        return resposta.json();
      })
      .then(function (dados) {
        botao.setAttribute("aria-pressed", dados.curtido ? "true" : "false");
        botao.setAttribute(
          "aria-label",
          botao.getAttribute(dados.curtido ? "data-rotulo-descurtir" : "data-rotulo-curtir") + ". " + dados.total + " curtidas."
        );
        form.querySelector("[data-curtir-total]").textContent = dados.total;
      })
      .catch(function () {
        // Sem resposta útil (sessão expirada, limite): cai no envio normal,
        // que mostra a mensagem do servidor.
        form.submit();
      })
      .finally(function () { botao.disabled = false; });
  });

  // --- Ordenação aplica ao escolher --------------------------------------------
  document.querySelectorAll("form[data-autoenvio] select").forEach(function (select) {
    select.addEventListener("change", function () { select.form.submit(); });
  });

  // --- Carregar mais / Ver menos -----------------------------------------------
  // "Carregar mais" acrescenta a próxima página de cards; "Ver menos" recolhe
  // tudo de volta à primeira página. Sem JavaScript, "Carregar mais" é só um
  // link para a página seguinte.
  var carregarMais = document.querySelector("[data-carregar-mais]");
  var verMenos = document.querySelector("[data-ver-menos]");
  var grade = document.querySelector("[data-grade]");
  if (carregarMais && grade) {
    var cardsIniciais = grade.children.length;
    var proximaInicial = carregarMais.getAttribute("href");

    carregarMais.addEventListener("click", function (evento) {
      evento.preventDefault();
      var url = new URL(carregarMais.href, location.href);
      url.hash = "";
      url.searchParams.set("parcial", "1");
      carregarMais.setAttribute("aria-busy", "true");

      fetch(url, { credentials: "same-origin" })
        .then(function (resposta) {
          if (!resposta.ok) throw new Error(String(resposta.status));
          return resposta.text();
        })
        .then(function (html) {
          var molde = document.createElement("template");
          molde.innerHTML = html;
          var proxima = molde.content.querySelector("template[data-proxima]");
          if (proxima) proxima.remove();
          var primeiroNovo = molde.content.querySelector("li");
          grade.appendChild(molde.content);
          carregarMais.removeAttribute("aria-busy");
          if (proxima) {
            carregarMais.href = proxima.getAttribute("data-proxima") + "#explorar";
          } else {
            carregarMais.hidden = true;
          }
          if (verMenos) verMenos.hidden = false;
          // Leva o foco ao primeiro card novo para quem navega pelo teclado.
          var link = primeiroNovo && primeiroNovo.querySelector(".card__titulo a");
          if (link) link.focus({ preventScroll: true });
        })
        .catch(function () { location.href = carregarMais.href; });
    });

    if (verMenos) {
      verMenos.addEventListener("click", function () {
        while (grade.children.length > cardsIniciais) grade.lastElementChild.remove();
        carregarMais.href = proximaInicial;
        carregarMais.hidden = false;
        verMenos.hidden = true;
        document.getElementById("explorar").scrollIntoView({ behavior: "smooth", block: "start" });
        carregarMais.focus({ preventScroll: true });
      });
    }
  }

  // --- Copiar link do verbete -----------------------------------------------------
  document.querySelectorAll("[data-copiar-link]").forEach(function (botao) {
    var original = botao.textContent;
    botao.addEventListener("click", function () {
      var texto = botao.getAttribute("data-copiar-link");
      var copia = navigator.clipboard ? navigator.clipboard.writeText(texto) : Promise.reject();
      copia
        .then(function () { botao.textContent = botao.getAttribute("data-copiado"); })
        .catch(function () { botao.textContent = botao.getAttribute("data-falha"); })
        .finally(function () { setTimeout(function () { botao.textContent = original; }, 2500); });
    });
  });

  // --- Mostrar senha -----------------------------------------------------------------
  document.querySelectorAll("[data-mostrar-senha]").forEach(function (botao) {
    var campo = document.getElementById(botao.getAttribute("data-mostrar-senha"));
    botao.hidden = false;
    botao.addEventListener("click", function () {
      var visivel = campo.type === "text";
      campo.type = visivel ? "password" : "text";
      botao.textContent = visivel ? "Mostrar senha" : "Ocultar senha";
    });
  });

  // --- Requisitos da senha -------------------------------------------------------------
  document.querySelectorAll("[data-requisitos]").forEach(function (campo) {
    var lista = document.getElementById(campo.getAttribute("data-requisitos"));
    var usuario = document.getElementById(campo.getAttribute("data-usuario") || "");
    function conferir() {
      var senha = campo.value;
      var regras = {
        tamanho: senha.length >= 8,
        numeros: senha.length > 0 && !/^\d+$/.test(senha),
        usuario: senha.length > 0 && (!usuario || senha.toLowerCase() !== usuario.value.trim().toLowerCase()),
      };
      lista.querySelectorAll("[data-regra]").forEach(function (item) {
        item.setAttribute("data-ok", regras[item.getAttribute("data-regra")] ? "true" : "false");
      });
    }
    campo.addEventListener("input", conferir);
    if (usuario) usuario.addEventListener("input", conferir);
    conferir();
  });

  // --- Contadores de caracteres ------------------------------------------------------
  document.querySelectorAll("[data-contador]").forEach(function (campo) {
    var ajuda = document.getElementById(campo.getAttribute("data-contador"));
    var modelo = ajuda.getAttribute("data-modelo");
    function contar() {
      var n = campo.tagName === "TEXTAREA" ? campo.value.trim().length : campo.value.length;
      ajuda.textContent = modelo.replace("{n}", n);
    }
    campo.addEventListener("input", contar);
    contar();
  });

  // --- Tags em etiquetas ------------------------------------------------------------
  // O campo continua sendo um texto separado por vírgulas (é o que o servidor
  // recebe); as etiquetas são só a forma de editar.
  document.querySelectorAll("[data-etiquetas]").forEach(function (original) {
    var MAXIMO = 8;
    var total = document.querySelector("[data-etiquetas-total]");
    var tags = original.value.split(",").map(function (t) { return t.trim(); }).filter(Boolean);

    var caixa = document.createElement("div");
    caixa.className = "etiquetas-campo";
    var digitacao = document.createElement("input");
    digitacao.id = original.id;
    digitacao.setAttribute("aria-describedby", original.getAttribute("aria-describedby"));
    if (original.hasAttribute("aria-invalid")) digitacao.setAttribute("aria-invalid", "true");
    original.removeAttribute("id");
    original.type = "hidden";
    original.parentNode.insertBefore(caixa, original);

    var sugestoes = document.createElement("div");
    sugestoes.className = "sugestoes";
    var opcoes = (original.getAttribute("data-sugestoes") || "").split("|").filter(Boolean);
    caixa.parentNode.insertBefore(sugestoes, original.nextSibling);

    function existe(tag) {
      return tags.some(function (t) { return t.toLocaleLowerCase() === tag.toLocaleLowerCase(); });
    }

    function desenhar() {
      caixa.textContent = "";
      tags.forEach(function (tag, indice) {
        var etiqueta = document.createElement("span");
        etiqueta.className = "etiqueta-campo";
        etiqueta.textContent = tag;
        var remover = document.createElement("button");
        remover.type = "button";
        remover.textContent = "×";
        remover.setAttribute("aria-label", "Remover a tag " + tag);
        remover.addEventListener("click", function () {
          tags.splice(indice, 1);
          desenhar();
          digitacao.focus();
        });
        etiqueta.appendChild(remover);
        caixa.appendChild(etiqueta);
      });
      digitacao.placeholder = tags.length ? "" : "Internetês, anglicismo…";
      caixa.appendChild(digitacao);
      original.value = tags.join(", ");
      if (total) total.textContent = tags.length;

      sugestoes.textContent = "";
      if (tags.length < MAXIMO) {
        opcoes.filter(function (s) { return !existe(s); }).slice(0, 6).forEach(function (sugestao) {
          var botao = document.createElement("button");
          botao.type = "button";
          botao.textContent = "+ " + sugestao;
          botao.addEventListener("click", function () { adicionar(sugestao); digitacao.focus(); });
          sugestoes.appendChild(botao);
        });
      }
    }

    function adicionar(bruta) {
      var tag = bruta.trim().replace(/,+$/, "");
      digitacao.value = "";
      if (!tag || existe(tag) || tags.length >= MAXIMO) return desenhar();
      tags.push(tag);
      desenhar();
    }

    digitacao.addEventListener("keydown", function (evento) {
      if (evento.key === "Enter" || evento.key === ",") {
        evento.preventDefault();
        adicionar(digitacao.value);
      } else if (evento.key === "Backspace" && digitacao.value === "" && tags.length) {
        tags.pop();
        desenhar();
      }
    });
    // Tag digitada sem Enter também entra no envio.
    digitacao.addEventListener("blur", function () { if (digitacao.value.trim()) adicionar(digitacao.value); });
    original.form.addEventListener("submit", function () { if (digitacao.value.trim()) adicionar(digitacao.value); });

    desenhar();
  });

  // --- Citações do formulário de envio --------------------------------------------
  var lista = document.querySelector("[data-citacoes]");
  var adicionarCitacao = document.querySelector("[data-adicionar-citacao]");
  var modeloCitacao = document.querySelector("template[data-modelo-citacao]");
  if (lista && adicionarCitacao && modeloCitacao) {
    var MAXIMO_CITACOES = 10;

    function numerar() {
      var itens = lista.querySelectorAll("[data-citacao]");
      itens.forEach(function (item, indice) {
        var n = indice + 1;
        item.querySelector("[data-citacao-numero]").textContent = "Citação " + n;
        item.querySelector("[data-remover-citacao]").setAttribute("aria-label", "Remover a citação " + n);
        item.querySelector("textarea").setAttribute("aria-label", "Texto da citação " + n);
        item.querySelector("input[name=fonte]").setAttribute("aria-label", "Fonte da citação " + n);
        item.querySelector("input[name=link]").setAttribute("aria-label", "Link da citação " + n);
      });
      adicionarCitacao.hidden = itens.length >= MAXIMO_CITACOES;
    }

    adicionarCitacao.addEventListener("click", function () {
      lista.appendChild(modeloCitacao.content.cloneNode(true));
      numerar();
      lista.lastElementChild.querySelector("textarea").focus();
    });

    lista.addEventListener("click", function (evento) {
      var botao = evento.target.closest("[data-remover-citacao]");
      if (!botao) return;
      botao.closest("[data-citacao]").remove();
      numerar();
      adicionarCitacao.focus();
    });

    numerar();
  }

  // --- Cancelar dentro de <details> (rejeição na moderação) -------------------
  document.addEventListener("click", function (evento) {
    var botao = evento.target.closest("[data-fechar-detalhes]");
    if (!botao) return;
    var detalhes = botao.closest("details");
    detalhes.open = false;
    detalhes.querySelector("summary").focus();
  });

  // --- Painel: seletores que se aplicam ao escolher ----------------------------
  document.querySelectorAll("select[data-autoenvio-campo]").forEach(function (select) {
    select.addEventListener("change", function () { select.form.requestSubmit(); });
  });

  // --- Painel: ações em lote -----------------------------------------------------
  var formLote = document.querySelector("[data-lote]");
  if (formLote) {
    var itensLote = document.querySelectorAll("[data-lote-item]");
    var marcarTodos = formLote.querySelector("[data-marcar-todos]");
    var contagemLote = formLote.querySelector("[data-lote-contagem]");
    var atualizarLote = function () {
      var marcados = Array.prototype.filter.call(itensLote, function (c) { return c.checked; }).length;
      contagemLote.textContent = marcados === 0 ? "Nenhum marcado" : marcados === 1 ? "1 marcado" : marcados + " marcados";
      marcarTodos.checked = marcados > 0 && marcados === itensLote.length;
      marcarTodos.indeterminate = marcados > 0 && marcados < itensLote.length;
      formLote.querySelectorAll("button[name=acao]").forEach(function (b) { b.disabled = marcados === 0; });
    };
    marcarTodos.addEventListener("change", function () {
      itensLote.forEach(function (c) { c.checked = marcarTodos.checked; });
      atualizarLote();
    });
    itensLote.forEach(function (c) { c.addEventListener("change", atualizarLote); });
    atualizarLote();
  }

  // --- Painel: prévia do membro da equipe ---------------------------------------
  document.querySelectorAll("[data-previa]").forEach(function (alvo) {
    var campo = document.getElementById(alvo.getAttribute("data-previa"));
    if (!campo) return;
    var padrao = alvo.textContent;
    campo.addEventListener("input", function () { alvo.textContent = campo.value || padrao; });
  });
  var campoFoto = document.getElementById("id_foto");
  var previaFoto = document.querySelector("[data-previa-foto]");
  if (campoFoto && previaFoto) {
    campoFoto.addEventListener("change", function () {
      var arquivo = campoFoto.files && campoFoto.files[0];
      if (!arquivo) return;
      previaFoto.src = URL.createObjectURL(arquivo);
      previaFoto.hidden = false;
      var iniciais = document.querySelector("[data-previa-iniciais]");
      if (iniciais) iniciais.hidden = true;
    });
  }

  // --- Carregamento entre páginas ------------------------------------------------
  // O frasco só aparece se a próxima página demorar: em navegação rápida ele
  // nem chega a piscar. Fica por último para enxergar o preventDefault dos
  // tratamentos acima (curtir e "Carregar mais" não trocam de página).
  var carregando = document.querySelector("[data-carregando]");
  if (carregando) {
    var temporizador = null;
    var mostrarCarregando = function () {
      clearTimeout(temporizador);
      temporizador = setTimeout(function () { carregando.hidden = false; }, 350);
    };
    var esconderCarregando = function () {
      clearTimeout(temporizador);
      carregando.hidden = true;
    };

    document.addEventListener("click", function (evento) {
      if (evento.defaultPrevented || evento.button !== 0) return;
      if (evento.metaKey || evento.ctrlKey || evento.shiftKey || evento.altKey) return;
      var link = evento.target.closest("a[href]");
      if (!link || link.target === "_blank" || link.hasAttribute("download")) return;
      var destino = new URL(link.href, location.href);
      if (destino.origin !== location.origin) return;
      // Âncora na própria página não carrega nada.
      if (destino.pathname === location.pathname && destino.search === location.search) return;
      mostrarCarregando();
    });

    document.addEventListener("submit", function (evento) {
      if (!evento.defaultPrevented) mostrarCarregando();
    });

    // Voltar pelo histórico restaura a página do cache já com o frasco visível.
    window.addEventListener("pageshow", esconderCarregando);
  }

  // --- Foco no resumo de erros depois de um envio com problemas ----------------
  var resumo = document.querySelector("[data-foco-inicial]");
  if (resumo) resumo.focus();
})();
