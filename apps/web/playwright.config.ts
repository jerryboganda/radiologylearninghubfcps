import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 120_000,
  expect: { timeout: 10_000 },
  fullyParallel: false,
  forbidOnly: true,
  reporter: [['line']],
  use: {
    ...devices['Desktop Chrome'],
    headless: true,
    trace: 'off',
    screenshot: 'off',
    video: 'off'
  }
});
