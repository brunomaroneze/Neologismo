"""Sugestão do processo de formação de um neologismo.

Mesma abordagem do neologism_detector (RandomForest sobre características
explícitas da palavra + n-gramas de letras), com duas diferenças:

- o modelo é treinado aqui, com a versão do scikit-learn do projeto, em vez
  de carregar o .pkl do repositório original (pickle de outra versão costuma
  não abrir, e carregar pickle executa código);
- além do CSV classificado pela equipe, entram no treino os neologismos já
  aprovados no Neoscópio que têm processo de formação. O CSV sozinho tem 84%
  de "composto neoclássico", o que fazia o modelo chutar essa classe.

O treino leva poucos segundos e acontece no primeiro uso de cada processo
do servidor; depois de TTL_TREINO o modelo é refeito para aprender com as
aprovações novas.
"""

import csv
import threading
import time
from pathlib import Path

import numpy as np
from scipy.sparse import csr_matrix, hstack
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer

TREINO_CSV = Path(__file__).resolve().parent / 'dados' / 'treino.csv'
TTL_TREINO = 6 * 60 * 60
MINIMO_POR_CLASSE = 3

# Rótulos do detector original -> vocabulário usado nos verbetes do Neoscópio.
ROTULOS = {
    'composto neoclássico': 'composição neoclássica',
    'derivado prefixal': 'derivação prefixal',
    'derivado sufixal': 'derivação sufixal',
    'estrangeirismo': 'empréstimo',
    'splinter': 'formação com splinter',
    'composto': 'composição',
    'sigla': 'sigla',
    'outros': 'outros',
}

# Listas do train_classifier.py original.
PREFIXOS = ['pré-', 'pós-', 'super-', 'mega-', 'macro-', 'micro-', 'anti-', 'auto-', 'co-',
            'des-', 'in-', 're-', 'hiper-', 'inter-']
SUFIXOS = ['-dade', '-dades', '-ção', '-ções', '-agem', '-agens', '-mento', '-mentos', '-ico',
           '-ica', '-icos', '-icas', '-izar', '-ismo', '-ismos', '-eiro', '-eira', '-eiras',
           '-vel', '-veis', '-ificar']
ESTRANGEIROS = {
    'letras': ['k', 'w', 'y'],
    'inicios': ['st', 'sp', 'sl', 'sm', 'sf', 'sc', 'sk', 'sh', 'th', 'ph', 'ch'],
    'finais': ['q', 't', 'p', 'j', 'h', 'g', 'f', 'd', 'c', 'v', 'b',
               'er', 'or', 'ar', 'ing', 'est'],
    'internos': ['zz', 'th', 'ph', 'mm', 'gg', 'tt', 'sh', 'zh', 'ck'],
}
FINAIS_PORTUGUESES = ['ão', 'ões']


def caracteristicas(palavra):
    """Vetor de características explícitas (mesma lógica do original)."""
    p = palavra.lower()
    vogais = sum(1 for c in p if c in 'aeiouáéíóúâêôãõ')
    valores = [
        1 if '-' in p else 0,
        len(p),
        vogais / len(p) if p else 0,
    ]
    valores += [1 if p.startswith(x.replace('-', '')) else 0 for x in PREFIXOS]
    valores += [1 if p.endswith(x.replace('-', '')) else 0 for x in SUFIXOS]
    valores += [1 if x in p else 0 for x in ESTRANGEIROS['letras']]
    valores += [1 if p.startswith(x) else 0 for x in ESTRANGEIROS['inicios']]
    valores += [1 if p.endswith(x) else 0 for x in ESTRANGEIROS['finais']]
    valores += [1 if x in p else 0 for x in ESTRANGEIROS['internos']]
    valores += [1 if p.endswith(x) else 0 for x in FINAIS_PORTUGUESES]
    return valores


def exemplos_de_treino():
    """Pares (palavra, processo) do CSV original e dos verbetes aprovados."""
    from neologismo.models import Neologismo

    pares = []
    with open(TREINO_CSV, encoding='utf-8') as arquivo:
        for linha in csv.DictReader(arquivo):
            rotulo = ROTULOS.get(linha['processo'].strip().lower())
            if rotulo:
                pares.append((linha['palavra'], rotulo))

    aprovados = (
        Neologismo.objects.filter(status=Neologismo.APROVADO)
        .exclude(tipologia='')
        .values_list('titulo', 'tipologia')
    )
    pares += [(titulo, tipologia.strip().lower()) for titulo, tipologia in aprovados]

    # Classes com pouquíssimos exemplos só confundiriam o modelo.
    contagem = {}
    for _, rotulo in pares:
        contagem[rotulo] = contagem.get(rotulo, 0) + 1
    return [(p, r) for p, r in pares if contagem[r] >= MINIMO_POR_CLASSE]


class Classificador:
    def __init__(self):
        self._trava = threading.Lock()
        self._modelo = None
        self._vetorizador = None
        self._treinado_em = 0.0

    def _matriz(self, palavras):
        explicitas = csr_matrix(np.array([caracteristicas(p) for p in palavras], dtype=float))
        return hstack([explicitas, self._vetorizador.transform(palavras)]).tocsr()

    def treinar(self):
        pares = exemplos_de_treino()
        palavras = [p for p, _ in pares]
        rotulos = [r for _, r in pares]
        self._vetorizador = TfidfVectorizer(
            analyzer='char_wb', ngram_range=(1, 3), max_features=5000,
        )
        self._vetorizador.fit(palavras)
        modelo = RandomForestClassifier(
            n_estimators=200, random_state=42, class_weight='balanced', n_jobs=1,
        )
        modelo.fit(self._matriz(palavras), rotulos)
        self._modelo = modelo
        self._treinado_em = time.monotonic()

    def _garantir_modelo(self):
        with self._trava:
            if self._modelo is None or time.monotonic() - self._treinado_em > TTL_TREINO:
                self.treinar()

    def sugerir(self, palavras):
        """Para cada palavra, (processo mais provável, confiança de 0 a 1)."""
        if not palavras:
            return []
        self._garantir_modelo()
        probabilidades = self._modelo.predict_proba(self._matriz(palavras))
        classes = self._modelo.classes_
        return [
            (classes[int(np.argmax(linha))], float(np.max(linha)))
            for linha in probabilidades
        ]


classificador = Classificador()
