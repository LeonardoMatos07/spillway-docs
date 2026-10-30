# 10. Operação: como subir, onde está cada coisa, o que fazer quando algo quebra

## 10.1 O mapa de portas (ambiente local)

| Serviço | Porta | O que é |
|---|---|---|
| spillway-web (dev) | **3002** | O site |
| spillway-api | **8000** | API do Spillway |
| Airflow | **8081** | Interface do pipeline (login `airflow` / `airflow` localmente) |
| Postgres do warehouse | **5433** | Banco do Spillway (`warehouse` / `warehouse`) |
| Data lake (SeaweedFS) | **8333** (S3) e **8888** (navegador de arquivos) | Bronze, silver, gold |
| Relay API | **3000** | Mensagens |
| Relay publisher | 3001 | Métricas do publisher |
| relay-api-gateway | **8080** | Porta de entrada do Relay |
| Postgres do Relay | 5432 | Banco do Relay |
| Redpanda (Kafka) | 19092 | Fila |
| Prometheus / Grafana | 9090 / 3030 | Métricas |
| Provedores simulados | 8091 a 8096 | SMS, e-mail, WhatsApp, push de mentira |
| Serviço de depuração do forecast | 8100 | Opcional, fora do caminho de produção |

> **Por quê o site na 3002?** O Relay já usa a 3000 e a 3001. O Airflow ficou na 8081 (e não na 8080) porque o gateway do Relay ocupa a 8080.

## 10.2 Subindo tudo, na ordem

```
# 1) Relay (mensagens)
cd relay
docker compose up -d --build api publisher worker postgres redis redpanda
# com PROVIDERS=providers.real.json para usar o SES de verdade

# 2) Gateway do Relay
cd ../relay-api-gateway
docker compose up -d --build

# 3) Pipeline e banco do Spillway
cd ../energia-data
docker compose up -d        # Airflow, lake, warehouse (use o override de porta se a 8080 estiver ocupada)

# 4) Migrações do banco (cria as tabelas)
cd ../energia-api
DATABASE_URL=postgresql+psycopg://warehouse:warehouse@localhost:5433/warehouse uv run alembic upgrade head

# 5) API do Spillway
ENVIRONMENT=local AUTH_DISABLED=true DATABASE_URL=postgresql+psycopg://warehouse:warehouse@localhost:5433/warehouse \
WEB_URL=http://localhost:3002 EMAIL_BACKEND=gateway GATEWAY_URL=http://localhost:8080 GATEWAY_API_KEY=... \
uv run uvicorn app.main:app --port 8000

# 6) Site
cd ../energia-web
API_URL=http://127.0.0.1:8000 pnpm exec next dev -p 3002
```

> **Dica:** para a velocidade real do site, use o build de produção em vez do `next dev`:
> `NEXT_DIST_DIR=.next-prod pnpm build && NEXT_DIST_DIR=.next-prod pnpm exec next start -p 3002`.

## 10.3 Dados: backfill e relatórios

```
# Backfill (carrega muitos meses) pelo Airflow
docker exec energia-data-airflow-scheduler-1 airflow dags unpause ons_curtailment_pipeline
docker exec energia-data-airflow-scheduler-1 airflow dags trigger ons_curtailment_pipeline \
  --conf '{"first_month": "2021-10", "last_month": "2026-09"}'

# Gerar e publicar os relatórios de todos os meses
docker exec energia-data-airflow-scheduler-1 python -m energy_pipeline.report \
  --from 2021-10 --to 2026-09 --publish --submit
```

## 10.4 Envios de e-mail

| Quero | Comando ou rota |
|---|---|
| Enviar o relatório do mês mais recente | `uv run python -m app.dispatch report` (na pasta da API) ou `POST /v1/admin/dispatches` |
| Terminar um envio que parou | acrescentar `--retry` |
| Reenviar um mês já enviado | apagar a linha do mês em `email_dispatch` (e saber que o Relay devolve "já enviado" para as mesmas chaves) |
| Mandar um e-mail genérico, sem modelo | `POST /v1/messages` no gateway, só com `channel`, `to`, `subject` e `body` |

## 10.5 Testes e verificações por repositório

| Repositório | Comando |
|---|---|
| spillway-api | `uv run ruff check . && uv run mypy && uv run pytest -q` |
| spillway-web | `pnpm exec tsc --noEmit && pnpm exec eslint src && pnpm exec vitest run` |
| spillway-data | `uv run ruff check . && uv run pytest -q` |
| relay | `npm test` |
| relay-api-gateway | `pnpm test` |
| relay-receipts | `uv run ruff check . && uv run mypy && uv run pytest -q` |
| spillway-forecast | `uv run pytest && uv run ruff check . && uv run mypy` |
| relay-terraform e spillway-infra | `terraform fmt -check && terraform validate` |

Todos os repositórios têm **CI no GitHub Actions** com lint, tipos, testes, varredura de segredos e auditoria de dependências (e, nos de imagem Docker, varredura de vulnerabilidades com Trivy).

## 10.6 Onde ficam segredos e configurações

| O quê | Onde |
|---|---|
| Chaves do Relay e do gateway | Arquivos `.env` **fora do Git** em cada repositório |
| Chave de acesso do SES local | `.env` do Relay (saída do Terraform) |
| Estado do Terraform do `relay-terraform` | Arquivo local, **fora do Git** (contém o segredo da chave IAM) |
| Segredos de produção | AWS Secrets Manager e SSM (previstos no `spillway-infra`) |

> **Atenção:** o estado local do Terraform do `relay-terraform` guarda o segredo da chave de acesso do usuário IAM. Mantenha esse arquivo fora do Git (já está) e, para uso em equipe, migre para um backend S3 criptografado.

## 10.7 Lista de problemas que já aconteceram (e a solução)

| Sintoma | Causa | O que fazer |
|---|---|---|
| Página mostra "Dados indisponíveis" ou lista antiga depois de carregar dados | Cache de `fetch` do Next persistiu | Parar o site, apagar `energia-web/.next/cache/fetch-cache`, subir de novo |
| Rota nova da API responde 404 | O processo da API é antigo | Reiniciar o processo da API |
| Erro 500 ao cadastrar depois de mudar templates | Processo da API antigo com arquivo de template removido | Reiniciar a API |
| `RELAY_URL must start with http://` ao testar a Lambda `relay-receipts` | A Lambda está desligada de propósito (Relay não é público) | Esperado. Ligar exige URL pública e `terraform apply` |
| Recursos "não aparecem" na AWS | Console aberto em outra região | Trocar para **sa-east-1 (São Paulo)** |
| Docker Desktop parou durante um build grande | Falta de memória do Docker | Reiniciar o Docker Desktop e subir de novo (os volumes permanecem) |
| Porta 8080 em uso ao subir o Airflow | O gateway do Relay usa a 8080 | Usar o override de porta (Airflow na 8081) |
| Alarme `relay-dlq-ses_events` em ALARM | 16 mensagens antigas na DLQ, restos de testes | Limpar a fila (`purge-queue`) quando quiser |
| Previsão com datas antigas | Último dado do ONS no silver é 30/09 | Já corrigido pela ingestão híbrida (capítulo 8.10): rode `uv run spillway refresh` ou suba o worker |
| `terraform apply` não mostra mudanças para recursos que "sumiram" | Os recursos existem, em outra região | Conferir a região |

## 10.8 Cuidados antes de alterar algo

- **Banco compartilhado (warehouse):** migrações e cargas escrevem nele. Rodar `spillway publish`, o backfill ou o `alembic upgrade` altera dados reais do ambiente local.
- **Nomes implantados** (escopo do Cognito, ECR, usuários do banco, caminhos na EC2): não renomear sem planejar a migração.
- **SES:** a conta está em sandbox; um envio de teste só vai para endereços verificados.
- **Disco:** o backfill e as imagens do Docker ocupam espaço; se faltar, `docker system df` mostra o que é recuperável.
