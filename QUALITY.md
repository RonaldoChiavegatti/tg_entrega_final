# Definição de Pronto (DoR) e Definição de Feito (DoD)

## DoR
- Histórias com critérios de aceitação claros e exemplos de payloads para os endpoints afetados.
- Dependências (serviços externos, filas, variáveis de ambiente) mapeadas e configuradas em `.env`.
- Métricas e alertas desejados descritos (Prometheus/Grafana) e valores de SLA registrados.
- Plano de testes definido (unitários, integração, e2e) e dados de teste disponíveis.

## DoD
- Endpoints novos/alterados documentados no README ou em rotas autodocumentadas do FastAPI.
- Métricas expostas em `/metrics` com novos contadores/histogramas publicados.
- Todos os testes automatizados passando (unitários, integração, e2e) e executados em CI.
- Alertas configurados/atualizados para os dashboards afetados e limites revisados.
- Logs estruturados e rastreabilidade (correlação de tenant/usuário) confirmados nos serviços tocados.

## Testes adicionados
- `pytest` em `tests/` para validação de CNPJ, datas, somas e estados de limite/tokenização.
- Teste de integração simulando upload→OCR→PATCH→FIELDS_UPDATED→LIMITS_RECALCULATED→dashboard.
- Suite Playwright (`frontend/e2e`) para medir SLA de recálculo (≤5s) com o stack em execução (`E2E_LIVE=1`).

