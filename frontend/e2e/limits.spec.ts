import { test, expect, request } from '@playwright/test';
import { performance } from 'perf_hooks';

const apiBase = process.env.API_BASE_URL || 'http://localhost:8080';

test.describe('Fluxo completo de limites', () => {
  test.skip(!process.env.E2E_LIVE, 'Executar com stack subida (E2E_LIVE=1)');

  test('recalcula limites em menos de 5s', async ({ page }) => {
    const docId = process.env.E2E_DOC_ID;
    const tenantId = process.env.E2E_TENANT_ID || 'demo';
    test.skip(!docId, 'Defina E2E_DOC_ID com um documento já semeado');

    const context = await request.newContext();
    const headers = { 'X-User-Role': 'admin', 'x-tenant-id': tenantId };

    const start = performance.now();
    const patch = await context.patch(`${apiBase}/documents/${docId}`, {
      headers,
      data: [{ path: 'totals.gross_amount', value: 100.0, source: 'e2e' }],
    });

    expect(patch.ok()).toBeTruthy();

    const recalculated = await context.post(`${apiBase}/limits/recalculate`, {
      headers,
      data: { tenant_id: tenantId, year: 2024, doc_ids: [docId] },
    });

    expect(recalculated.ok()).toBeTruthy();
    expect(performance.now() - start).toBeLessThanOrEqual(5_000);

    await page.goto('/dashboard');
    await expect(page.getByText('Dashboard de Limites')).toBeVisible();
  });
});

