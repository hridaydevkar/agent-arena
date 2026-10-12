import { defineConfig } from "@playwright/test";
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  workers: 1,
  retries: 0,
  use: {
    baseURL: process.env.ARENA_TEST_URL || "http://127.0.0.1:8000",
    viewport: { width: 1440, height: 1000 },
    screenshot: "only-on-failure",
  },
  reporter: "list",
  timeout: 30000,
});
