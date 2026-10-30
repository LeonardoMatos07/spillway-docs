# 8. spillway-forecast: a previsão de risco de corte

## 8.1 O que ele prevê

Para cada hora dos próximos dias, em cada **série** (estado ou subsistema × fonte eólica ou solar), o modelo estima duas coisas:

1. **O risco**: a probabilidade de aquela hora ter corte de pelo menos **10% da geração potencial**. É um indicador estatístico, não uma garantia.
2. **O corte esperado**: o percentual de corte esperado para a hora.

São **27 séries** modeladas (a solar do Mato Grosso do Sul tem menos de 120 dias de histórico e fica de fora).

> **Em resumo:** é um "termômetro de risco" por hora, apoiado em cinco anos de histórico, calendário e no comportamento recente. Ele **não usa clima**.

## 8.2 Os dados

| Fonte | Período | Origem |
|---|---|---|
| Eólica | 2021-10 até hoje | ONS (conjuntos), pela camada **silver** do `spillway-data` |
| Solar | 2024-04 até hoje | idem (a ONS só publica a solar desde essa data) |

As linhas de 30 minutos viram **séries horárias** por estado, subsistema e Brasil. A "geração potencial" é a geração verificada mais a cortada; o percentual de corte divide uma pela outra. Horas em que o denominador é menor que 1 MWh (a solar à noite) são **excluídas** do treino e da avaliação, e aparecem como "não aplicável".

O resultado do ajuste: cerca de **1,6 milhão de linhas de previsão** (uma origem a cada 3 dias × 168 horas à frente), das quais ~218 mil formam o teste final.

> **Atenção (a limitação mais importante hoje):** a camada silver só tem **meses completos** e o ONS publica o mês anterior no começo do seguinte. Por isso o último dado hoje é **30/09/2026**, e a previsão publicada cobre **1 a 7 de outubro**, ou seja, não é "a próxima semana a partir de hoje". A primeira versão do projeto, que baixava direto do ONS, chegava a 27/10 porque o ONS atualiza o **mês corrente** aos poucos. A correção, já mergeada, é a **ingestão híbrida**: silver para o histórico validado + cauda do mês corrente direto do ONS, marcada como provisória. Em 28/10/2026 os dados iam até 27/10 e a janela publicada ia de 28/10 a 03/11. Nos meses em comum, silver e ONS diferem só por ruído de ponto flutuante.

## 8.3 O que o modelo recebe (as variáveis)

| Grupo | Exemplos |
|---|---|
| Calendário da hora prevista | hora, dia da semana, mês, fim de semana, **feriado brasileiro**, sazonalidade (seno e cosseno) |
| Histórico do corte (só o passado) | % de corte no último dia, 7, 28 e 90 dias; tendência; pico horário do último dia |
| Geração | nível de geração em 1, 7 e 28 dias |
| Mesmo horário em dias anteriores | ontem, média de 7 e de 28 dias, mesma hora na semana anterior |
| Identificação | a série e a fonte (variáveis categóricas) |

Não usa clima (vento, irradiação), preço, consumo nem informação de indisponibilidade da rede.

## 8.4 O modelo e por que ele

São **dois** estimadores `HistGradientBoosting` do scikit-learn, treinados juntos nas mesmas variáveis: um **classificador** (o risco) e um **regressor** (o percentual esperado). Um modelo **global** para as 27 séries, com a série e a fonte como variáveis. Parâmetros: 250 iterações, taxa de aprendizado 0,06, 31 folhas, mínimo de 200 amostras por folha, regularização L2 igual a 1, sem parada antecipada, semente 42.

> **Por quê gradient boosting (árvores)?** É a família que costuma vencer em **dados tabulares com variáveis misturadas** (números e categorias) e interações como "de dia, em abril, no Nordeste, a eólica sofre mais". Aprende essas interações sozinho, é **rápido** com 1,6 milhão de linhas, lida com valores ausentes e produz **probabilidades bem calibradas** (o erro de calibração medido foi 0,036). Um único modelo global **aprende entre séries**: o padrão de uma região ajuda outra com menos histórico.

> **Por quê o HistGradientBoosting, e não LightGBM ou XGBoost?** Foi escolhido por instalar sem atrito no Windows e **não acrescentar dependências** além do scikit-learn. Para este tamanho de dado, o desempenho esperado é equivalente.

> **Por quê não modelos por série (Prophet, ARIMA)?** Seriam 27 modelos independentes, sem aprendizado compartilhado e com dificuldade de usar tantas variáveis de contexto.

> **Por quê não redes neurais (LSTM, Transformer)?** Com poucos anos de dados horários e sem variáveis externas ricas, elas raramente superam árvores, exigem mais engenharia e são mais difíceis de explicar e de calibrar.

> **Honestidade:** esse raciocínio é a justificativa de projeto. **Os únicos comparativos medidos são contra duas linhas de base simples** (abaixo). Não foram feitos testes de bancada contra Prophet, LightGBM ou redes neurais. Se isso importar para a pós ou para uma apresentação, vale executar esse comparativo.

## 8.5 As linhas de base (contra o que o modelo é comparado)

Um modelo só vale se vencer alternativas simples. Foram usadas duas:

| Linha de base | Ideia |
|---|---|
| **Climatologia** | O risco típico por série × mês × tipo de dia (útil ou fim de semana) × hora, aprendido do passado |
| **Sazonal ingênuo** | "A mesma hora na semana anterior" |

## 8.6 Como se valida (sem se enganar)

Prever o futuro exige **validação temporal**: nada de sorteio aleatório, que deixaria o modelo "ver" o futuro.

```mermaid
gantt
  title Janelas de validação (rolling-origin com janela crescente)
  dateFormat YYYY-MM
  axisFormat %Y
  tickInterval 1year
  section Treino (sempre cresce)
  Treino até a dobra 1 : 2021-10, 2024-12
  section Dobras de validação cruzada
  Dobra 1 (3 meses) : 2025-01, 2025-03
  Dobra 2 : 2025-04, 2025-06
  Dobra 3 : 2025-07, 2025-09
  Dobra 4 : 2025-10, 2025-12
  Dobra 5 : 2026-01, 2026-03
  section Teste final (intocado)
  Teste final : 2026-04, 2026-09
```

Regras que garantem honestidade:

- **5 dobras de 3 meses** (2025-01 a 2026-03), cada uma treinando só com o que veio **antes** e com **7 dias de folga** (*embargo*) entre treino e teste.
- **Teste final intocado** (2026-04 a 2026-09): hiperparâmetros fixos, nada ajustado nele.
- **Teste de vazamento** automatizado: se alguém corromper todos os dados a partir da origem da previsão, nenhuma variável de histórico pode mudar.
- **Significância por blocos de semanas**: as linhas de treino se sobrepõem muito (cada origem gera 168 horas), então o intervalo de confiança reamostra **semanas**, não linhas.

> **Por quê tanto cuidado?** Em dados de séries temporais, o vazamento é fácil de criar sem querer: janelas de 28 dias precisam ser deslocadas um dia, "a mesma hora na semana anterior" só vale até 7 dias de horizonte, e a parada antecipada padrão do scikit-learn usa um sorteio aleatório interno. Todos esses pontos foram tratados.

## 8.7 Resultados (teste final, 2026-04 a 2026-09)

| Modelo | Erro médio (MAE, pontos percentuais) | ROC-AUC | Brier | Erro de calibração |
|---|---|---|---|---|
| Climatologia | 13,65 | 0,841 | 0,2174 | 0,218 |
| Sazonal ingênuo | 11,84 | 0,803 | n/d | 0,190 |
| **Gradient boosting** | **10,05** | **0,917** | **0,1156** | **0,036** |

- Diferença do modelo para a climatologia no MAE: **−3,6 pontos percentuais**, com intervalo de confiança de 95% de **−4,6 a −2,5** (exclui zero).
- Na validação cruzada (média das 5 dobras): MAE 9,45 (modelo), 11,54 (climatologia), 10,61 (sazonal ingênuo).

> **O que os números dizem, com honestidade:**
> - O modelo é **muito melhor que as linhas de base na classificação do risco e na calibração**: quando ele diz "70% de risco", acontece perto de 70% das vezes.
> - No **erro do percentual de corte** o ganho é menor, e numa dobra (2025-01 a 03) o modelo ficou **ligeiramente pior** que a climatologia (10,57 contra 10,45).
> - A precisão **quase não cai** do dia 1 ao dia 7. Isso é sinal de que o modelo é, na prática, uma "climatologia adaptativa mais calendário": sem clima, ele não enxerga o vento de amanhã.

## 8.8 Limitações

- **Sem clima.** O próximo passo natural é incluir previsão de vento e irradiação, e a carga e o preço (CMO) previstos pelo ONS.
- **Defasagem dos dados** (seção 8.2).
- Os números "apurados" do ONS são **revisados**; o último mês pode mudar.
- A solar tem só ~2,5 anos de histórico; séries por estado podem ser curtas.
- Estado ou usina **novos** não existem para o modelo (as séries são fixas no treino).
- Não serve para decisões financeiras ou operacionais sozinho, nem para alegar compensação contratual.

## 8.9 Como a previsão chega ao site

A decisão central (ADR 7): o Forecast **publica no banco**, a API **lê do banco**, o site chama **só a API**.

```mermaid
flowchart LR
  silver[("Silver<br/>data lake")] --> ingest["ingest<br/>séries horárias"]
  ingest --> train["train<br/>treino, validação,<br/>MLflow"]
  train --> bundle["models/bundle.joblib"]
  bundle --> publish
  ingest --> publish["publish<br/>pontua as 27 séries<br/>para 168 h"]
  publish -- "uma transação" --> db[("Postgres<br/>forecast_model<br/>forecast_run<br/>forecast_hourly")]
  db --> api["spillway-api<br/>/v1/forecast"]
  api --> web["spillway-web<br/>/previsao"]
```

```mermaid
sequenceDiagram
  autonumber
  participant F as spillway publish
  participant P as Postgres
  participant A as spillway-api
  participant W as spillway-web
  participant U as Membro
  F->>P: BEGIN
  F->>P: INSERT forecast_model (uma vez por treino)
  F->>P: INSERT forecast_run (status loading)
  F->>P: INSERT forecast_hourly (4.536 linhas)
  F->>P: UPDATE run para ready, marca o modelo como atual
  F->>P: COMMIT (apaga rodadas antigas, guarda as 14 últimas)
  U->>W: abre /previsao
  W->>A: GET /v1/forecast, /scopes, /model
  A->>P: lê a última rodada ready (cache curto)
  A-->>W: pontos + origem, data dos dados, versão do modelo
  W-->>U: mapa de calor, KPIs, resultados do treino
```

> **Por quê o banco, e não uma chamada HTTP da API ao serviço de ML?**
> - A API **continua funcionando** (mostrando a última previsão e a idade dela) se o job de ML estiver fora do ar.
> - O tempo de resposta não depende de pontuar um modelo no meio da requisição.
> - A imagem da API **não precisa** de scikit-learn nem de joblib.
> - Cada previsão fica **ligada à versão do modelo** que a gerou (auditoria e retorno).
> - É o mesmo padrão do pipeline: a API é dona do esquema e o produtor só escreve nas suas tabelas.

A publicação é **idempotente**: rodar de novo para o mesmo modelo e a mesma origem não faz nada. Uma rodada só fica visível quando está completa (`ready`).

## 8.9.1 O que a página mostra

- Mapa de calor do **risco por hora** nos próximos dias, com seletores de fonte e de região (a URL guarda a escolha, dá para compartilhar);
- Indicadores e um gráfico do corte esperado;
- Um aviso de **defasagem** ("dados do ONS até 30/09/2026");
- Os **resultados do treino em português simples**: o que é o modelo, o período dos dados, como foi validado, a tabela contra as linhas de base, o gráfico de calibração, o peso das variáveis e as limitações;
- Se o serviço estiver fora, "Previsão indisponível no momento".

## 8.10 Ciclo automático (em produção local desde 28/10/2026)

O ciclo abaixo está mergeado (spillway-forecast #2, spillway-api #13, spillway-web #11). O worker é um contêiner (`docker compose up -d --build forecast-worker`); sem ele, `uv run spillway refresh` faz uma atualização manual:

```mermaid
flowchart TD
  A["Worker vigia a cada 60 min"] --> B{"Há dia novo no ONS<br/>desde a última previsão?"}
  B -- "não" --> A
  B -- "sim" --> C["Reconstrói as séries<br/>silver + cauda do mês corrente"]
  C --> D["Publica a previsão<br/>uma transação"]
  D --> E["Avisa a API:<br/>revalidar a tag forecast"]
  E --> F["API limpa o cache<br/>e o site é atualizado"]
  F --> A
  A --> G{"1x por dia:<br/>mês completo novo no silver<br/>e 25 dias desde o último treino?"}
  G -- "não" --> A
  G -- "sim" --> H["Retreina<br/>mesmo protocolo honesto"]
  H --> I{"Portão: o modelo novo<br/>não é pior que o atual<br/>e ainda vence a climatologia?"}
  I -- "sim" --> J["Promove e publica"]
  I -- "não" --> K["Mantém o modelo atual<br/>e registra o motivo"]
  J --> A
  K --> A
```

Pontos de proteção do retreino automático: os dois modelos (atual e candidato) são avaliados na **mesma janela de teste**; a troca é **atômica** (o modelo antigo fica guardado); existe uma **trava** para nunca rodarem dois processos ao mesmo tempo; e uma falha deixa tudo como estava.

> **Atenção:** o worker só roda se você o subir. Sem ele, a previsão fica parada até um `spillway refresh`. Para o site ser avisado na hora, a API precisa de `REVALIDATE_SECRET`; sem isso, o cache de 10 minutos do site vale.

> **Retreino medido:** o retreino completo com os dados híbridos levou cerca de 12,5 minutos e deu MAE 10,15 pp (climatologia 13,90), ROC-AUC 0,915, ECE 0,037, no mesmo nível do primeiro treino. Portão de promoção: AUC cai no máximo 0,01, MAE sobe no máximo 0,3 pp, ECE sobe no máximo 0,02 e o candidato ainda vence a climatologia com intervalo de 95%.

## 8.11 Como rodar

```
cd spillway-forecast
uv sync --extra lake --extra warehouse
uv run spillway ingest        # monta as séries horárias (do silver)
uv run spillway train         # ~20 min: dobras, teste final, MLflow, models/bundle.joblib
uv run spillway publish --dsn postgresql://warehouse:warehouse@localhost:5433/warehouse
uv run mlflow ui --backend-store-uri sqlite:///mlflow.db     # navegar nas execuções
uv run pytest && uv run ruff check . && uv run mypy
```

Arquivos para consultar: `MODEL_CARD.md` (ficha do modelo: uso, dados, variáveis, validação, limites), `reports/results.json` (números completos) e `reports/reconcile.txt` (conferência das somas mensais contra o warehouse, com diferença máxima de 0,0005 MWh).
