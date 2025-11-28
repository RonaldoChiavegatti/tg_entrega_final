import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  vus: parseInt(__ENV.VUS || '5', 10),
  duration: __ENV.DURATION || '30s',
  thresholds: {
    http_req_failed: ['rate<0.02'],
    http_req_duration: ['p(95)<1200'],
  },
};

const BASE_URL = __ENV.BASE_URL || 'http://localhost:8080';
const TENANT = __ENV.TENANT || 'demo';
const DOC_ID = __ENV.DOC_ID || 'demo-doc';
const YEAR = parseInt(__ENV.YEAR || '2024', 10);

function authHeaders() {
  const token = __ENV.AUTHORIZATION;
  return token ? { Authorization: token } : {};
}

function jsonHeaders() {
  return { 'Content-Type': 'application/json', ...authHeaders() };
}

export default function () {
  const headers = jsonHeaders();
  const key = `load/${DOC_ID}.txt`;

  const presign = http.post(
    `${BASE_URL}/documents/storage/presign-upload`,
    JSON.stringify({ key, content_type: 'text/plain', tenant_id: TENANT }),
    { headers },
  );
  check(presign, { 'presign 200': (r) => r.status === 200 });

  const patch = http.patch(
    `${BASE_URL}/documents/${DOC_ID}`,
    JSON.stringify([
      { path: 'totals.gross_amount', value: Math.random() * 500, source: 'loadtest' },
      { path: 'storage.mock_text', value: 'patched during load', source: 'loadtest' },
    ]),
    { headers },
  );
  check(patch, {
    'patch success': (r) => r.status === 200 || r.status === 404,
  });

  const recalc = http.post(
    `${BASE_URL}/limits/recalculate`,
    JSON.stringify({ tenant_id: TENANT, year: YEAR, doc_ids: [DOC_ID] }),
    { headers },
  );
  check(recalc, {
    'recalc accepted': (r) => r.status === 202 || r.status === 200,
  });

  sleep(1);
}
