# 9. Fluxos de ponta a ponta

Este capítulo junta as peças. Cada fluxo mostra **quem fala com quem, em que ordem**, atravessando os projetos.

## 9.1 Cadastro de um membro (com código por e-mail)

```mermaid
sequenceDiagram
  autonumber
  actor U as Pessoa
  participant W as spillway-web
  participant A as spillway-api
  participant G as relay-api-gateway
  participant R as Relay
  participant S as Amazon SES
  U->>W: preenche o cadastro
  W->>A: POST /v1/auth/signup
  alt e-mail já tem conta
    A-->>W: 409 já existe
    W-->>U: aviso, com links para entrar ou recuperar a senha
  else novo
    A->>A: grava o membro (não verificado) e um código de 6 dígitos (hash)
    A->>G: POST /v1/messages (modelo, variáveis nome e código)
    G->>R: repassa (Idempotency-Key)
    R->>R: renderiza e grava na outbox
    R-->>A: 202
    A-->>W: 202
    W-->>U: pede o código
    R->>S: envia o e-mail (HTML + texto)
    S-->>U: e-mail com o código
    U->>W: digita o código
    W->>A: POST /v1/auth/verify-email
    A->>A: confere o hash, marca como verificado
    A-->>W: ok
    W->>A: POST /v1/auth/login
    A-->>W: token de sessão (14 dias)
    W-->>U: entra no Painel
  end
```

> **Por quê código e não link?** O código se digita na própria tela, funciona no celular sem abrir outro navegador e tem limite de tentativas. É mais difícil de interceptar em encaminhamentos e prévias de e-mail.

## 9.2 Um novo mês do ONS: do arquivo ao e-mail

É o ciclo mais importante do produto. Acontece sozinho no dia 3 de cada mês.

```mermaid
sequenceDiagram
  autonumber
  participant AF as Airflow (spillway-data)
  participant ONS as ONS
  participant L as Data lake
  participant DB as Postgres
  participant A as spillway-api
  participant W as spillway-web
  participant R as Relay
  actor M as Inscritos
  AF->>ONS: baixa os arquivos (se o ETag mudou)
  AF->>L: bronze, silver, quarentena
  AF->>AF: valida (quality gates)
  AF->>DB: publish: apaga e reinsere o mês (1 transação)
  AF->>A: revalidate (token de máquina)
  A->>W: invalida o cache por tags
  AF->>A: POST /v1/admin/reports (relatório com gráficos)
  AF->>A: POST /v1/admin/dispatches (kind report, mês)
  A->>DB: reserva o envio do mês (único) e lista os destinatários
  A->>R: um e-mail por pessoa, com chave de idempotência fixa
  R-->>M: relatório no corpo do e-mail
  Note over A,R: Repetir é seguro: mês já enviado responde 409, envio parcial é completado
```

> **Por quê um envio por mês, com chave por pessoa?** Se o pipeline rodar de novo (ou o envio parar no meio), ninguém recebe duas vezes. O Relay responde "já enviei" para a mesma chave.

## 9.3 Ativar a newsletter na home

```mermaid
sequenceDiagram
  autonumber
  actor U as Membro logado
  participant W as spillway-web
  participant A as spillway-api
  participant R as Relay
  U->>W: clica em Receber a newsletter mensal
  W->>A: PUT /v1/auth/me/newsletter {enabled: true}
  A->>A: marca marketing_opt_in (sem confirmação)
  A->>A: monta boas-vindas e o relatório mais recente
  A-->>W: perfil atualizado
  W-->>U: Você habilitou a newsletter mensal
  A->>R: e-mail de boas-vindas
  A->>R: relatório mais recente (mesma chave do envio mensal)
  R-->>U: dois e-mails em poucos minutos
```

O relatório de boas-vindas é construído **exatamente** como o envio mensal o constrói, com a mesma chave de idempotência. Assim, quem ativa antes do envio do mês não recebe o relatório duas vezes.

## 9.4 Baixar a análise em PDF

```mermaid
sequenceDiagram
  autonumber
  actor U as Membro
  participant W as spillway-web
  participant A as spillway-api
  participant DB as Postgres
  U->>W: Baixar, PDF (com o filtro da tela)
  W->>W: confere a sessão e valida os parâmetros
  W->>A: GET /v1/exports/analysis.pdf (escopo, fonte, período)
  A->>DB: resumo, rankings, série mensal, perfil horário
  A->>A: monta o PDF (reportlab) com todas as linhas
  A-->>W: PDF
  W-->>U: arquivo com o nome certo
```

## 9.5 O recibo de entrega de um e-mail

```mermaid
sequenceDiagram
  autonumber
  participant R as Relay
  participant S as SES
  participant Q1 as SQS eventos
  participant L1 as Lambda webhook-ses
  participant Q2 as SQS recibos
  participant L2 as Lambda relay-receipts
  R->>S: envia o e-mail (com o id do Relay numa tag)
  S->>Q1: evento Delivery ou Bounce ou Complaint
  Q1->>L1: lote de eventos
  L1->>L1: traduz para o recibo neutro
  L1->>Q2: enfileira
  Q2->>L2: lote
  L2->>L2: ledger: já vi este recibo?
  L2->>R: POST /v1/receipts
  R->>R: atualiza delivery_status e suprime se for bounce permanente
```

## 9.6 Da previsão ao site

```mermaid
sequenceDiagram
  autonumber
  participant W as Worker do forecast
  participant L as Lake (silver)
  participant DB as Postgres
  participant A as spillway-api
  participant S as spillway-web
  W->>L: há dado mais novo?
  L-->>W: sim, até o dia D
  W->>W: reconstrói as séries e pontua 168 h
  W->>DB: publica a rodada (1 transação)
  W->>A: revalidate (tag forecast)
  A->>S: invalida o cache da previsão
  S->>A: GET /v1/forecast
  A->>DB: lê a última rodada ready
  A-->>S: previsão + data dos dados + versão do modelo
```

> **Atenção:** o worker precisa estar rodando (capítulo 8.10) e a API precisa de `REVALIDATE_SECRET` para o site atualizar na hora.

## 9.7 Esqueci a senha

Segue o mesmo desenho do cadastro: a API gera um código (modelo "redefinir senha"), o Relay entrega, a pessoa digita o código com a nova senha, e a API troca a senha e **encerra as sessões antigas**.

## 9.8 Resumo: onde cada decisão aparece

| Fluxo | Decisões em ação |
|---|---|
| Cadastro | Código por e-mail; Relay com outbox e idempotência; modelos de e-mail do próprio produto |
| Novo mês | Carga idempotente com reprocessamento; invalidação de cache por evento; envio único por mês |
| Newsletter | Mesma chave do envio mensal; sem confirmação para quem já verificou o e-mail |
| Recibos | Fila entre as Lambdas; recibo neutro; status que só avança |
| Previsão | Publicação pelo banco; API dona do esquema |
