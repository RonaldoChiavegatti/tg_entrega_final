import { defineConfig } from '@playwright/test';

const apiBase = process.env.API_BASE_URL || 'http://localhost:8080';

export default defineConfig({
  testDir: './e2e',
  timeout: 15_000,
  expect: {
    timeout: 5_000,
  },
  use: {
    baseURL: process.env.FRONTEND_BASE_URL || 'http://localhost:3000',
    extraHTTPHeaders: {
      'X-User-Role': 'admin',
    },
    trace: 'on-first-retry',
  },
  metadata: {
    apiBase,
  },
});

