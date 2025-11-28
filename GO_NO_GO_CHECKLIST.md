# Checklist Go/No-Go

Use esta lista antes de colocar a versão em produção. Marque cada item quando houver evidência documentada (dashboard, issue, script ou runbook).

## Métricas e SLO batidos
- [ ] SLOs de disponibilidade, latência e erros estão definidos e documentados para o serviço.
- [ ] Dashboards mostram os últimos 7-30 dias dentro das metas definidas (picos justificáveis anotados).
- [ ] Métricas de capacidade (fila, CPU/memória, throughput) estão estáveis no ambiente de pré-produção com carga representativa.
- [ ] Todos os endpoints expõem `/metrics` com etiquetas de tenant/usuário para facilitar correlação.

## Alertas configurados
- [ ] Alertas de SLO (erro/latência) mapeados para os respectivos dashboards e testados com firing controlado.
- [ ] Alertas de infraestrutura (CPU, memória, disco, fila, TLS) habilitados com limites revisados.
- [ ] Alertas enviam para os canais corretos (on-call/chat) com prioridade e rotas de escalonamento documentadas.
- [ ] Alertas silenciam serviços não afetados (evitar spam) e registram playbook ligado ao alerta.

## RBAC válido
- [ ] Papéis e permissões revisados segundo o princípio do menor privilégio (serviços, DB, filas e painéis).
- [ ] Credenciais/API keys rotacionadas para o deploy e armazenadas em secret manager; acesso auditável.
- [ ] Service accounts de CI/CD só têm permissão para o escopo necessário (deploy, logs, métricas, rollback).

## Backups e restauração
- [ ] Rotina de backup automatizada documentada (frequência, retenção, cifragem, armazenamento off-site).
- [ ] Restaurar backup foi testado no último ciclo e tempo de recuperação (RTO/RPO) está dentro do acordado.
- [ ] Backups incluem dados, configurações críticas (dashboards, rules) e segredos não reconstituíveis.

## Plano de rollback
- [ ] Estratégia definida (feature flag, blue/green, canário ou tag de release) com passos de reversão claros.
- [ ] Migrações de banco têm caminho de volta ou scripts de compensação; schema diffs revisados.
- [ ] Pacotes/imagens anteriores estão disponíveis e versionados; checklist de verificação pós-rollback pronto.

## Runbook de incidentes
- [ ] Runbook cobre detecção, triagem, mitigação, recuperação e comunicação externa/interna.
- [ ] Procedimentos de paging/on-call, horários e critérios de escalonamento estão claros e testados.
- [ ] Logs de auditoria e timelines de incidentes são armazenados para RCA posterior.
