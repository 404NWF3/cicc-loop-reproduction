import { defineConfig } from '@playwright/test';
import { existsSync, mkdtempSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

const stateDir = mkdtempSync(join(tmpdir(), 'loop-research-e2e-'));
const credentials = { username: 'e2e', password: 'e2e-only-long-test-password' };
const chromium =
  process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE ||
  (existsSync('/usr/bin/chromium') ? '/usr/bin/chromium' : undefined);

export default defineConfig({
  testDir: './e2e',
  timeout: 45000,
  workers: 1,
  use: {
    baseURL: 'http://127.0.0.1:5174',
    httpCredentials: credentials,
    viewport: { width: 1440, height: 1000 },
    trace: 'retain-on-failure',
    launchOptions: chromium ? { executablePath: chromium } : {},
  },
  webServer: [
    {
      command: '../.venv/bin/python -m loop_research.cli serve --port 8001',
      url: 'http://127.0.0.1:8001/api/v1/health',
      env: {
        LOOP_STATE_DIR: stateDir,
        LOOP_DATA_DIR: join(stateDir, 'data'),
        LOOP_FIXTURE_STEP_SECONDS: '0.15',
        LOOP_WORKER_AUTOSTART: 'true',
        LOOP_BUDGET_PATH: join(stateDir, 'budget.sqlite3'),
        DEEPSEEK_API_KEY: '',
        LOOP_RESEARCH_TOKEN: '',
        LOOP_AUTH_REQUIRED: 'true',
        LOOP_AUTH_USERNAME: credentials.username,
        LOOP_AUTH_PASSWORD: credentials.password,
      },
      reuseExistingServer: false,
    },
    {
      command: 'npm run dev -- --port 5174',
      url: 'http://127.0.0.1:5174',
      env: { LOOP_API_PROXY: 'http://127.0.0.1:8001' },
      reuseExistingServer: false,
    },
  ],
});
