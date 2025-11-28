# Testes de carga (k6/Locust)

Este diretório contém cenários prontos para k6 e Locust exercitando os fluxos críticos exigidos no hardening:

- `POST /documents/storage/presign-upload`
- `PATCH /documents/{id}`
- `POST /limits/recalculate`

## k6

```
BASE_URL=http://localhost:8080 \
TENANT=demo \
DOC_ID=load-demo \
AUTHORIZATION="Bearer <token>" \
vus=5 duration=30s k6 run k6_scenarios.js
```

Variáveis importantes:
- `BASE_URL`: Gateway ou serviço direto.
- `TENANT`, `DOC_ID`: identificadores usados nos payloads.
- `AUTHORIZATION`: cabeçalho opcional para passar pelo gateway.
- `DURATION`, `VUS`: controlam a pressão do teste.

## Locust

Instale dependências (`pip install locust`) e rode:

```
BASE_URL=http://localhost:8080 TENANT=demo DOC_ID=load-demo locust -f locustfile.py
```

No UI escolha usuários e spawn rate. Os três endpoints são executados em sequência em cada task, registrando falhas e latências.
