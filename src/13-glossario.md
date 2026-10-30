# 13. Glossário

## Setor elétrico

| Termo | Significado |
|---|---|
| **Curtailment** | Energia eólica ou solar que **poderia** ter sido gerada, mas foi reduzida por ordem do operador. |
| **ONS** | Operador Nacional do Sistema Elétrico: quem coordena a operação da rede e publica os dados abertos. |
| **CCEE** | Câmara de Comercialização de Energia Elétrica: forma os preços usados para valorar a energia. |
| **SIN** | Sistema Interligado Nacional (o Brasil inteiro, para este produto). |
| **Subsistema** | N, NE, S e SE (Sudeste/Centro-Oeste). |
| **GNRa** | Geração não realizada apurada: a energia cortada oficial. |
| **REL** | Corte por razão de **confiabilidade elétrica**. |
| **CNF** | Corte por **indisponibilidade externa** (equipamento fora da usina). |
| **ENE** | Corte por **razão energética** (mais oferta que consumo). |
| **CMO** | Custo Marginal de Operação (usado para valorar a energia cortada). |
| **PLD** | Preço de Liquidação das Diferenças (tem piso e teto anuais). |
| **Compensável** | A parte do corte (REL e CNF) que pode dar direito a ressarcimento. |
| **MWh / GWh** | Megawatt-hora e gigawatt-hora (1 GWh = 1.000 MWh). |

## Dados e engenharia

| Termo | Significado |
|---|---|
| **Pipeline** | Sequência automática de passos que leva um dado da origem até o destino. |
| **Airflow** | Agendador e orquestrador de pipelines. |
| **DAG** | O desenho do pipeline: tarefas e a ordem entre elas. |
| **Bronze, silver, gold** | Camadas do data lake: original, limpo e validado, agregado para consumo. |
| **Data lake** | Armazenamento de arquivos (aqui, S3 ou SeaweedFS). |
| **Backfill** | Carregar muitos meses antigos de uma vez. |
| **ETag** | Identificador da versão de um arquivo: se não mudou, não precisa baixar de novo. |
| **Idempotente** | Que dá o mesmo resultado se for repetido; seguro de rodar de novo. |
| **Migração** | Mudança versionada no esquema do banco (Alembic). |
| **ADR** | Registro curto de uma decisão de arquitetura e seu motivo. |
| **CI** | Verificações automáticas em cada mudança de código (GitHub Actions). |
| **OIDC** | Forma de o GitHub provar sua identidade à AWS sem chaves fixas. |
| **Terraform** | Descreve infraestrutura em código. |

## Relay e mensageria

| Termo | Significado |
|---|---|
| **Outbox** | Tabela que guarda a mensagem junto com o dado, na mesma transação, para publicá-la depois. |
| **Kafka (Redpanda)** | Fila de mensagens distribuída e durável. |
| **Partição** | Divisão de um tópico do Kafka; a mesma chave cai sempre na mesma partição. |
| **Offset** | Posição de leitura numa partição. |
| **DLQ** | *Dead-letter queue*: fila de mensagens que não puderam ser processadas. |
| **Circuit breaker** | Disjuntor que para de chamar um provedor com falhas por um tempo. |
| **Failover** | Passar para outro provedor quando o primeiro falha. |
| **Token bucket** | Balde de fichas: limita quantas chamadas por segundo se pode fazer. |
| **Idempotency-Key** | Cabeçalho que identifica uma requisição, para repeti-la sem duplicar. |
| **SES** | Amazon Simple Email Service, o provedor de e-mail. |
| **SNS / SQS** | Notificação e fila da AWS. |
| **Lambda** | Função que roda na AWS sob demanda. |
| **Bounce** | E-mail devolvido (endereço inexistente, caixa cheia). |
| **Complaint** | A pessoa marcou o e-mail como spam. |
| **Supressão** | Lista de endereços para os quais não se envia mais. |
| **Sandbox (SES)** | Modo inicial em que só se envia a endereços verificados. |

## Previsão e aprendizado de máquina

| Termo | Significado |
|---|---|
| **Série temporal** | Valores medidos ao longo do tempo (aqui, por hora). |
| **Climatologia** | O valor típico para aquela época e hora, aprendido do histórico. Usada como linha de base. |
| **Gradient boosting** | Combina muitas árvores de decisão pequenas, cada uma corrigindo as anteriores. |
| **Variável (feature)** | Informação que o modelo recebe para decidir. |
| **Vazamento (leakage)** | O modelo "ver" informação do futuro no treino, o que infla os resultados. |
| **Validação temporal** | Testar sempre em período posterior ao do treino. |
| **Embargo** | Folga entre o fim do treino e o início do teste. |
| **MAE** | Erro absoluto médio (aqui, em pontos percentuais). |
| **ROC-AUC** | Quão bem o modelo separa horas de risco das sem risco (0,5 é sorte, 1 é perfeito). |
| **Brier** | Erro quadrático das probabilidades (menor é melhor). |
| **Calibração (ECE)** | Se "70% de risco" acontece mesmo ~70% das vezes (menor erro é melhor). |
| **Bootstrap** | Reamostragem para estimar a incerteza de uma diferença. |
| **MLflow** | Registro das execuções e versões dos modelos. |
| **Retreino** | Treinar de novo com os dados mais novos. |
| **Defasagem (stale)** | Idade do dado mais recente usado. |
