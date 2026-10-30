# 11. As decisões de arquitetura, em linguagem simples

Uma decisão de arquitetura é uma escolha com **custo**. Aqui cada uma está no mesmo formato: qual era o problema, o que foi escolhido, o que foi descartado e que custo se aceitou. Os textos completos estão nos **ADRs** (*Architecture Decision Records*) dentro dos repositórios.

## 11.1 Spillway (ADRs do `spillway-api`)

| # | Decisão | Problema | Alternativa descartada | Custo aceito |
|---|---|---|---|---|
| 1 | **Quatro repositórios com um contrato escrito; a API é dona do esquema** | Quatro partes que evoluem juntas podem discordar sobre tabelas e rotas | Um repositório único (monorepo), ou cada parte criando suas tabelas | Mudar algo compartilhado começa por um documento e passa por mais de um repositório |
| 2 | **O número oficial do ONS vale; distribui-se para as usinas** | A estimativa por usina não fecha com o total oficial | Usar só a estimativa das usinas | A distribuição por usina é uma regra de modelagem (explicada na metodologia) |
| 3 | **Cargas mensais idempotentes, reprocessando os últimos 3 meses** | O ONS revisa dados antigos; rodar de novo não pode duplicar | Carregar só o mês novo e nunca revisar | Mais processamento por rodada |
| 4 | **Invalidação do cache disparada por evento (do pipeline para o site)** | Esperar uma hora para ver dados novos é ruim, mas consultar sempre é caro | Só cache por tempo; ou nenhum cache | Uma cadeia de chamadas (pipeline, API, site) que precisa de segredos |
| 5 | **Sem NAT gateway** | Custa uns US$ 40 por mês parado | NAT gateway em todas as redes | Tarefas em sub-redes públicas, com toda a entrada fechada |
| 6 | **Deploy sem chaves, por OIDC, com ambiente de produção aprovado por pessoa** | Chaves da AWS no GitHub vazam | Chaves de acesso guardadas como segredo | Configuração inicial de papéis e confiança |
| 7 | **A previsão é publicada pelo banco, não chamada por HTTP** | A API não pode depender de um serviço de ML estar no ar | Proxy HTTP da API para o serviço de ML | Uma camada de tabelas e um job de publicação |

## 11.2 Relay (ADRs do `relay`)

| # | Decisão | Problema | Alternativa descartada | Custo aceito |
|---|---|---|---|---|
| 1 | **Outbox transacional com um publicador líder** | Escrever no banco e no Kafka separadamente perde ou duplica mensagens | Publicar no Kafka direto da API | Um processo a mais e um pequeno atraso até o Kafka |
| 2 | **Partição por destinatário, com concorrência por chave** | Manter a ordem por pessoa sem serializar tudo | Um consumidor único, ou sem ordem | O paralelismo máximo é o número de partições |
| 3 | **Pelo-menos-uma-vez com idempotência em cada salto** | "Exatamente uma vez" não existe de ponta a ponta com provedores externos | Tentar garantir exatamente uma vez | Um duplicado raro quando o provedor não tem chave de idempotência |
| 4 | **Filas de retry em camadas e fila de mortos** | Esperar sem prender o consumidor nem usar um cronômetro por mensagem | Dormir no consumidor ou agendar por mensagem | Atrasos fixos (5 s, 30 s, 5 min) |
| 5 | **Troca de provedor com circuit breaker por processo** | Um provedor morto custaria um timeout por mensagem | Estado de saúde compartilhado em um serviço | Cada servidor aprende a falha por conta própria |
| 6 | **Limite de taxa para toda a frota num balde no Redis** | O contrato é por conta, não por servidor | Limite por processo | Redis no caminho quente (sem ele, os workers param) |
| 7 | **Recibos de provedores, status que só avança e lista de supressão** | O que o provedor diz depois (bounce, spam) precisa voltar, e fora de ordem | Ignorar os eventos | Duas dimensões de status (`status` e `delivery_status`) |
| 8 | **O produto manda o HTML; o Relay preenche as variáveis** | O Relay serve vários produtos e não deve virar catálogo de modelos | Guardar modelos dentro do Relay | O Relay não tem condicionais nem laços: o produto renderiza se precisar |

## 11.3 Relay-receipts

| Decisão | Problema | Escolha | Custo aceito |
|---|---|---|---|
| **SQS entre as duas Lambdas, não API Gateway** | O Relay pode estar fora do ar; picos de eventos | Fila (guarda por 14 dias, tentativas, DLQ, sem endpoint público) | Entrega pelo-menos-uma-vez, resolvida com ledger e idempotência |
| **Recibo neutro de um único formato** | O Relay não deve conhecer o vocabulário de cada provedor | Um tradutor por provedor (hoje o `webhook-ses`) e um webhook geral | Escrever um tradutor novo por provedor |

## 11.4 Forecast

| Decisão | Problema | Escolha | Custo aceito |
|---|---|---|---|
| **Gradient boosting global, com duas linhas de base** | Prever o risco por hora com histórico limitado e sem clima | Árvores (HistGradientBoosting), um modelo para 27 séries | Sem clima, o modelo é "histórico mais calendário" |
| **Validação temporal com folga e teste final intocado** | Evitar vazamento de futuro | 5 dobras crescentes, embargo de 7 dias, teste de vazamento | Validação mais pesada (cerca de 20 minutos de treino) |
| **Publicar no banco em uma transação** | A previsão nunca pode aparecer pela metade | Rodada `loading` e depois `ready` | Mais tabelas |
| **Retreino automático com portão** | Um modelo novo pode ser pior que o atual | Promover só se não piorar e ainda vencer a climatologia | Lógica extra de comparação |

## 11.5 Decisões de produto e de experiência

| Decisão | Por quê |
|---|---|
| **Só a página inicial, a metodologia e a privacidade são abertas** | O site é um produto para membros e a base alimenta o e-mail mensal |
| **Menu por pergunta** (Painel, Explorar, Análises, Previsão, Relatórios) | Menos itens e sem redundância entre relatórios, painel e análises |
| **Comparar é uma ação** dentro de Estados e Usinas | Compara-se a partir de algo que se está olhando |
| **Cadastro com e-mail existente avisa claramente** | Clareza para o usuário valia mais que esconder se o e-mail existe |
| **Relatório inteiro no corpo do e-mail** (sem anexo por enquanto) | Mais simples e mais lido; o anexo PDF fica para depois |
| **Dois downloads: PDF ou dados completos** | Um PDF completo e um conjunto de dados, em vez de muitos arquivos soltos |
| **Newsletter com um clique para quem está logado** | O e-mail já foi verificado; confirmar de novo seria atrito sem ganho |

> **Em resumo:** quase todas as decisões trocam um pouco de simplicidade por **segurança contra falha** (nada se perde, nada duplica, cada serviço pode cair sozinho). Em um produto que depende de dados oficiais e de e-mail, é a troca certa.

## 11.6 Novas fontes do ONS

| Decisão | Por quê | Custo aceito |
|---|---|---|
| **Um pipeline por assunto** (sistema, hidrologia, rede) | Isolar falhas e horários; o curtailment não muda | Mais DAGs para acompanhar |
| **Tabela própria para a frota** (`power_plant`) em vez de ampliar `plant` | `plant` é eólica e solar do produto de curtailment | Duas tabelas de usinas, com o mesmo id |
| **Cadastro da rede com histórico** (`valid_from`, `valid_to`) | O mapa da rede vai mostrar a expansão | Uma lógica de comparação por hash no publish |
| **Gates que dizem a verdade dos dados** (reservatório negativo, `SIN` no balanço, ruído solar) | Bloquear só o que é erro, avisar o que é incomum | É preciso olhar os avisos de vez em quando |
| **Backfill de hidrologia só de 2015 em diante** | Os arquivos antigos são grandes e raros de usar | O histórico anterior fica para uma execução à parte |
