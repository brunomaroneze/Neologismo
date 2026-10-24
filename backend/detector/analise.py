"""Detecção de candidatos a neologismo num texto.

Pipeline (adaptado do neologism_detector):

1. spaCy (pt_core_news_sm) separa palavras, frases, classe gramatical e
   entidades; só substantivos, adjetivos e verbos viram candidatos, e nomes
   próprios ficam de fora.
2. Cada palavra é procurada no léxico (≈480 mil formas dicionarizadas), na
   forma escrita, no lema e sem pronome enclítico ("fazê-lo" -> "fazer").
3. O que não está no léxico nem foi marcado como "não é neologismo" pela
   moderação é candidato. Os que já existem no banco aparecem como tal.
4. O classificador sugere o processo de formação.

A consulta ao Dicio.com.br do projeto original (raspagem do site, uma
requisição por palavra) não foi trazida: é lenta e depende de um site de
terceiros que não oferece essa consulta.
"""

import re
import threading
from dataclasses import dataclass, field

from neologismo.models import Neologismo

from .classificador import classificador
from .models import PalavraIgnorada, PalavraLexico

MAX_CARACTERES = 20_000
CLASSES_CANDIDATAS = {'NOUN': 'Substantivo', 'ADJ': 'Adjetivo', 'VERB': 'Verbo'}
ENTIDADES_IGNORADAS = {'PER', 'LOC', 'ORG', 'MISC'}
FINAIS_ENCLITICOS = [
    '-o', '-a', '-os', '-as', '-lo', '-la', '-los', '-las', '-no', '-na', '-nos', '-nas',
    '-se', '-lhe', '-lhes', '-me', '-te',
]
# Derivados de nome próprio ("Bolsonarismo", "Lulista") costumam vir com
# maiúscula e o spaCy os marca como nome de pessoa; com estes sufixos, a
# palavra é analisada mesmo assim. (-iano fica de fora: Mariana, Adriano...)
SUFIXOS_DE_DERIVADOS = ('ismo', 'ismos', 'ista', 'istas', 'ização', 'izações')
HORA = re.compile(r'^\d{1,2}h(\d{2})?(min)?$')
NAO_LETRA = re.compile(r'[^a-záàâãéêíóôõúüç\-]')

_nlp = None
_trava_nlp = threading.Lock()


def carregar_nlp():
    """Modelo do spaCy, carregado uma vez por processo e só quando usado."""
    global _nlp
    with _trava_nlp:
        if _nlp is None:
            import spacy
            _nlp = spacy.load('pt_core_news_sm')
            _nlp.max_length = MAX_CARACTERES * 2
    return _nlp


def e_derivado_de_nome(palavra):
    return any(
        palavra.endswith(sufixo) and len(palavra) >= len(sufixo) + 4
        for sufixo in SUFIXOS_DE_DERIVADOS
    )


def formas_para_conferir(palavra, lema):
    """Formas a procurar no léxico: a escrita, o lema e sem pronome enclítico."""
    formas = {palavra, lema}
    if ' ' in lema:
        formas.add(lema.split(' ')[0])
    for final in FINAIS_ENCLITICOS:
        if palavra.endswith(final) and len(palavra) > len(final) + 1:
            base = palavra[: -len(final)]
            formas.add(base)
            for acentuada, infinitivo in (('á', 'ar'), ('ê', 'er'), ('i', 'ir'), ('ô', 'or')):
                if base.endswith(acentuada):
                    formas.add(base[:-1] + infinitivo)
    # O léxico ainda tem grafias com trema ("lingüista"): a importação guarda
    # também a forma sem trema, e aqui procuramos sempre sem ele.
    return {f.replace('ü', 'u') for f in formas if f}


@dataclass
class Candidato:
    palavra: str
    lema: str
    classe: str
    frase: str
    ocorrencias: int = 1
    processo: str = ''
    confianca: float = 0.0
    registrado: Neologismo | None = None

    @property
    def confianca_pct(self):
        return round(self.confianca * 100)


@dataclass
class Resultado:
    candidatos: list = field(default_factory=list)
    trechos: list = field(default_factory=list)  # (texto, chave do candidato ou None)
    total_palavras: int = 0

    @property
    def novos(self):
        return [c for c in self.candidatos if not c.registrado]


def analisar(texto):
    texto = texto[:MAX_CARACTERES]
    doc = carregar_nlp()(texto)

    # 1. Filtra os tokens que podem ser neologismos.
    possiveis = []
    total = 0
    for token in doc:
        if token.is_space or token.is_punct or token.like_num or token.like_url or token.like_email:
            continue
        palavra = NAO_LETRA.sub('', token.text.lower()).strip('-')
        if not palavra or HORA.match(token.text.lower()):
            continue
        total += 1
        derivado = e_derivado_de_nome(palavra)
        if len(palavra) < 3 or not derivado and (
            token.pos_ not in CLASSES_CANDIDATAS
            or token.ent_type_ in ENTIDADES_IGNORADAS
            # maiúscula no meio da frase: nome próprio que o spaCy não marcou
            or token.text[:1].isupper() and token.i != token.sent.start
        ):
            continue
        lema = NAO_LETRA.sub('', token.lemma_.lower())
        possiveis.append((token, palavra, lema, formas_para_conferir(palavra, lema)))

    # 2. Uma consulta só ao léxico e às palavras ignoradas, para o texto todo.
    todas = set().union(*(formas for *_, formas in possiveis)) if possiveis else set()
    conhecidas = set()
    for modelo in (PalavraLexico, PalavraIgnorada):
        conhecidas |= set(
            modelo.objects.filter(palavra__in=todas).values_list('palavra', flat=True)
        )

    # 3. Agrupa os candidatos por palavra.
    candidatos = {}
    marcados = {}
    for token, palavra, lema, formas in possiveis:
        if formas & conhecidas:
            continue
        marcados[token.i] = palavra
        if palavra in candidatos:
            candidatos[palavra].ocorrencias += 1
            continue
        candidatos[palavra] = Candidato(
            palavra=palavra,
            lema=lema or palavra,
            classe=CLASSES_CANDIDATAS.get(token.pos_, 'Substantivo'),
            frase=token.sent.text.strip(),
        )

    # Os que já estão no banco aparecem com o link para o verbete.
    registrados = {}
    for neologismo in Neologismo.objects.filter(
        titulo__iregex=r'^(' + '|'.join(re.escape(p) for p in candidatos) + r')$'
    ) if candidatos else []:
        registrados.setdefault(neologismo.titulo.lower(), neologismo)

    lista = list(candidatos.values())
    for candidato, (processo, confianca) in zip(
        lista, classificador.sugerir([c.palavra for c in lista]), strict=True,
    ):
        candidato.processo = processo
        candidato.confianca = confianca
        candidato.registrado = registrados.get(candidato.palavra) or registrados.get(candidato.lema)

    # 4. Texto em trechos, com os candidatos marcados (o template escapa tudo).
    trechos = []
    for token in doc:
        trechos.append((token.text, marcados.get(token.i)))
        if token.whitespace_:
            trechos.append((token.whitespace_, None))

    lista.sort(key=lambda c: (c.registrado is not None, -c.ocorrencias, c.palavra))
    return Resultado(candidatos=lista, trechos=_juntar(trechos), total_palavras=total)


def _juntar(trechos):
    """Junta trechos de texto comum vizinhos (menos elementos no HTML)."""
    juntos = []
    for texto, chave in trechos:
        if chave is None and juntos and juntos[-1][1] is None:
            juntos[-1] = (juntos[-1][0] + texto, None)
        else:
            juntos.append((texto, chave))
    return juntos
