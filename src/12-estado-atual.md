# 12. Estado atual, pendências e riscos

> **Honestidade:** este capítulo descreve o estado conhecido ao final da escrita desta documentação. Atualizado em 29/10/2026, depois do merge do ciclo automático do forecast.

## 12.1 O que está pronto e funcionando (no seu computador)

| Área | Estado |
|---|---|
| Pipeline de dados | Backfill completo de **2021-10 a 2026-09** (60 meses; eólica desde 2021-10, solar desde 2024-04). Relatórios dos 60 meses gerados, com gráficos. |
| Site | Menu por pergunta, área de membros, painel, estados, usinas, comparar, análises com download em PDF, Excel e CSV, relatórios com PDF, previsão com barra de progresso, tema claro e escuro. |
| API | Contas com código por e-mail, exportações, relatórios, disparo mensal, newsletter com um clique, boas-vindas e relatório por e-mail, previsão publicada pelo banco. |
| Relay | Plataforma completa com testes e carga; templates e variáveis; recibos de entrega; **e-mails reais entregues pelo SES** (verificado nos seus envios). |
| Forecast | Treinado com **todos os anos**, validado com protocolo temporal, publicado no banco local, com ficha do modelo na tela. |
| Documentação | Esta, em Markdown, HTML e PDF. |

## 12.2 O que foi concluído por último e o que está aberto

- **Mergeado:** ciclo automático da previsão (ingestão híbrida, worker que vigia a cada hora, tag `forecast`, aviso de defasagem, janela que parte de hoje), spillway-forecast #2, spillway-api #13 e spillway-web #11. **Falta subir o worker** para ele rodar sozinho.
- **Retreino mensal automático** com portão de qualidade e troca atômica (mergeado, ativo quando o worker roda).
- **spillway-web #12 (aberto):** gráfico de confiabilidade legível e conclusão com cuidados.
- **spillway-data #3:** renomeação das referências para `spillway-*` (CI vermelho por vulnerabilidades da imagem do Airflow que já existiam).

## 12.3 O que ainda não existe

| Item | Situação |
|---|---|
| **Spillway em produção na AWS** | O Terraform está escrito e validado, mas **nada foi aplicado**. O roteiro de primeira implantação está no `spillway-infra`. |
| **Renomear as pastas locais** `energia-*` para `spillway-*` | Pendente: exige parar API, web e Airflow e fechar editores. O `docker-compose.yml` do `spillway-data` na `main` ainda aponta para um caminho antigo (o PR de renomeação corrige). |
| **SES fora do sandbox** | A conta só envia para endereços verificados. |
| **Relay com URL pública** | Necessário para ligar a Lambda `relay-receipts`. |
| **Ciclo automático em produção** | Hoje tudo roda localmente; em produção, o worker do forecast viraria uma tarefa do ECS. |
| **Comparativo de modelos** | Só foram medidas duas linhas de base; falta comparar com LightGBM, Prophet e redes neurais, se for importante. |
| **Anexo PDF no e-mail** | Planejado para depois ("primeiro no corpo"). |
| **Clima na previsão** | Próximo grande ganho possível. |

## 12.4 Riscos e pontos de atenção

| Risco | Impacto | Mitigação |
|---|---|---|
| Dado do ONS com defasagem de semanas | A previsão "não é de hoje" | Ingestão híbrida da cauda do mês corrente (mergeada) e aviso claro na página |
| Retreino automático piorar o modelo | Previsão pior sem ninguém ver | Portão de promoção e modelo anterior guardado |
| Nomes antigos em recursos implantados | Confusão e quebra se alguém renomear sem migrar | Documentado; não renomear sem planejar |
| Confiança do OIDC aponta para os nomes novos | O deploy por GitHub Actions falha até aplicar o Terraform | `terraform apply` no `spillway-infra` na primeira implantação |
| Estado local do Terraform do `relay-terraform` | Contém o segredo da chave IAM | Fora do Git; migrar para S3 criptografado em equipe |
| Cache local de `fetch` do Next | Mostra dados antigos depois de carga | Apagar `.next/cache/fetch-cache`; em produção a invalidação é automática |
| SES em sandbox | Envio só para você | Pedir a saída do sandbox antes de abrir o produto |
| Alarme da DLQ do SES em ALARM | Ruído | Limpar a fila de restos de teste |
| Vulnerabilidades da imagem do Airflow | CI vermelho no scan | Atualizar a imagem base e os pacotes quando houver correção |

## 12.5 Próximos passos sugeridos

1. **Revisar e mergear** os PRs do ciclo automático do forecast quando terminarem.
2. **Colocar o Spillway no ar**: seguir o roteiro do `spillway-infra`, começando pelo estado do Terraform e pelas variáveis.
3. **Abrir o e-mail**: tirar o SES do sandbox, e decidir se o Relay terá URL pública.
4. **Observar o primeiro ciclo mensal real** (dia 3): conferir o relatório publicado, o e-mail e a previsão.
5. **Evoluir o modelo**: incluir clima e comparar com outras famílias de modelos.
6. **Anexar o PDF** do relatório ao e-mail.

## 12.6 Resumo em números

| | |
|---|---|
| Repositórios | 10 (9 com GitHub) |
| Meses de dados | 60 (2021-10 a 2026-09) |
| Séries do forecast | 27 |
| Testes | API ≈ 240, site ≈ 160, Relay 86, relay-receipts 74, data 91 |
| Capacidade medida do Relay (1 API) | ≈ 290 msg/s aceitas; entrega sustentada de 250 msg/s |
| Custo mensal estimado na AWS | US$ 170 a 270 |

## 12.7 Novas fontes do ONS (fases 0 a 4)

| Fase | O que entrou | Situação |
|---|---|---|
| 0 | Arquivos anuais até um mês e fallback parquet/csv | Mergeado |
| 1 | Painel do SIN: balanço, geração por fonte e por usina | Mergeado |
| 2 | Intercâmbio e despacho térmico | Mergeado |
| 3 | Água e energia (reservatórios, EAR, ENA, energia vertida) | Mergeado |
| 4 | Cadastro da rede com histórico | Mergeado |

Ainda **não existe**: as telas do portal (Painel do SIN, Água e energia, Mapa da rede), que só consomem estas rotas; as coordenadas das linhas (virão da ANEEL/SIGEL); e o backfill da hidrologia antes de 2015. Nada disso foi aplicado na AWS: o Terraform do `spillway-infra` já tem as permissões novas, mas a implantação de produção continua pendente.
