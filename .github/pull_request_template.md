## O que muda

<!-- Uma ou duas frases. O "por quê" importa mais que o "o quê": o diff já
     mostra o que mudou. -->

## Por quê

<!-- Que problema isso resolve? Se corrige um comportamento, descreva o
     comportamento errado de antes. -->

## Como testar

<!-- Os passos para quem for revisar ver a mudança funcionando.
     Ex.: subir com `docker compose up`, buscar "voce" na Home e conferir
     que "Vocezinho" aparece. -->

## Checklist

- [ ] O CI passou (testes, lint, tipos, build).
- [ ] Mexi em `models.py`? Então gerei a migração (`makemigrations`).
- [ ] Mexi em comportamento da API ou da interface? Então há teste cobrindo.
- [ ] Mexi em variável de ambiente? Então atualizei `.env.example` /
      `.env.prod.example` e o `DEPLOY.md`.
- [ ] Nenhum segredo, token ou senha real entrou no diff.
