import { test, expect } from "@playwright/test";

test("complete UI workflow: register, execute, replay, and compare", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/");
  await expect(
    page.getByRole("heading", {
      name: "A little less guesswork. A lot more proof.",
    }),
  ).toBeVisible();
  await page.getByRole("link", { name: "Agent registry" }).click();
  await page.getByRole("button", { name: "Register an agent" }).click();
  const name = `Northstar QA ${Date.now()}`;
  await page.getByLabel("Agent name").fill(name);
  await page
    .getByLabel("Description")
    .fill("Created by the automated browser smoke test.");
  await page.getByLabel("Execution policy").selectOption("methodical");
  await page.getByRole("button", { name: "Register & benchmark" }).click();
  await expect(
    page.getByRole("dialog", { name: "Put an agent to the test." }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Custom selection" }).click();
  await page.getByRole("button", { name: "Start benchmark" }).click();
  await expect(
    page.getByRole("heading", { name: "1 executions recorded" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Inspect first run" }).click();
  await expect(
    page.getByRole("heading", { name: "Reconcile a messy invoice ledger" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Play replay" }).click();
  await expect(page.locator(".player-step")).toContainText("Step 2", {
    timeout: 5000,
  });
  await page.getByRole("button", { name: "Pause replay" }).click();
  await page.getByRole("button", { name: "Evaluation", exact: false }).click();
  await expect(
    page.getByRole("heading", { name: "4 of 4 output checks passed" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Final output", exact: true }).click();
  await expect(page.locator(".detail-content .json-block")).toContainText(
    "1100",
  );
  await page.getByRole("link", { name: "Compare run" }).click();
  await expect(
    page.getByRole("heading", { name: "Same challenge. Different choices." }),
  ).toBeVisible();
  await expect(page.locator(".compare-agent")).toHaveCount(2);
  await page
    .getByRole("button", { name: "Execution traces", exact: true })
    .click();
  await expect(page.locator(".compare-event").first()).toBeVisible();
  await page.locator(".compare-event summary").first().click();
  await expect(page.locator(".compare-event[open] .json-block")).toBeVisible();
  const [download] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("button", { name: "Export comparison" }).click(),
  ]);
  expect(download.suggestedFilename()).toBe("arena-comparison.json");
  expect(errors).toEqual([]);
});

test("task filters and fixture details work", async ({ page }) => {
  await page.goto("/tasks");
  await expect(page.locator(".task-card")).toHaveCount(12);
  await page.getByRole("button", { name: "Research 4", exact: true }).click();
  await expect(page.locator(".task-card")).toHaveCount(4);
  await page.getByLabel("Task difficulty").selectOption("Hard");
  await expect(page.locator(".task-card")).toHaveCount(1);
  await page.locator(".task-card").click();
  await page.getByRole("button", { name: "Fixtures", exact: true }).click();
  await expect(page.locator(".fixture-block .json-block")).toContainText(
    "official",
  );
  await page.getByRole("button", { name: "Output schema" }).click();
  await expect(page.locator(".detail-content .json-block")).toContainText(
    "citation_ids",
  );
});

test("leaderboard filters, export, search, and documentation", async ({
  page,
}) => {
  await page.goto("/leaderboard");
  await expect(page.locator(".ranking-table tbody tr").first()).toContainText(
    "Atlas",
  );
  await page.getByLabel("Search leaderboard").fill("Meridian");
  await expect(page.locator(".ranking-table tbody tr")).toHaveCount(1);
  await page.getByRole("button", { name: "Research", exact: true }).click();
  await expect(page.locator(".ranking-table tbody tr")).toHaveCount(1);
  const [csv] = await Promise.all([
    page.waitForEvent("download"),
    page.getByRole("link", { name: "Export CSV" }).click(),
  ]);
  expect(csv.suggestedFilename()).toBe("agent-arena-leaderboard.csv");
  await page.getByRole("button", { name: "Methodology" }).click();
  await expect(
    page.getByRole("heading", {
      name: "Understand the score before trusting it.",
    }),
  ).toBeVisible();
  await page.keyboard.press("Escape");
  await page.keyboard.press("Control+k");
  await page.getByLabel("Search workspace").fill("shipping");
  await page.locator(".command-results button").first().click();
  await expect(
    page.getByRole("heading", { name: "Find the cheapest eligible shipment" }),
  ).toBeVisible();
  await page
    .getByRole("link", { name: "Documentation", exact: true })
    .first()
    .click();
  await page
    .locator(".docs-nav")
    .getByRole("button", { name: "Bring your agent", exact: false })
    .click();
  await expect(page.locator(".docs-code").first()).toContainText(
    "class MyAgent",
  );
});

test("mobile navigation and all main pages avoid document overflow", async ({
  page,
}) => {
  await page.setViewportSize({ width: 390, height: 844 });
  for (const path of [
    "/",
    "/leaderboard",
    "/experiments",
    "/tasks",
    "/agents",
    "/runs",
    "/compare",
    "/docs",
    "/settings",
  ]) {
    await page.goto(path);
    await expect(page.locator(".page")).toBeVisible();
    await expect
      .poll(
        () =>
          page.evaluate(
            () => document.documentElement.scrollWidth <= window.innerWidth + 1,
          ),
        { message: `No document overflow on ${path}` },
      )
      .toBe(true);
  }
  await page.getByRole("button", { name: "Open navigation" }).click();
  await page.getByRole("link", { name: "Overview", exact: true }).click();
  await expect(page.locator(".hero-panel")).toBeVisible();
  await expect(page.locator(".sidebar")).not.toHaveClass(/open/);
});

test("OpenRouter onboarding and real experiment budget controls", async ({
  page,
}) => {
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto("/experiments");
  await expect(
    page.getByRole("heading", { name: "Same model. Three ways to solve." }),
  ).toBeVisible();
  await expect(page.locator(".architecture-card")).toHaveCount(3);
  await expect(page.locator(".experiment-task")).toHaveCount(3);
  await expect(page.locator(".experiment-launch")).toContainText(
    "up to 13 model requests",
  );
  await expect(
    page.getByRole("button", { name: "Run three-agent comparison" }),
  ).toBeDisabled();
  await page.getByLabel("Calls per tool-based agent").selectOption("4");
  await expect(page.locator(".experiment-launch")).toContainText(
    "up to 9 model requests",
  );
  await page.getByRole("button", { name: "Show all 12 tasks" }).click();
  await expect(page.locator(".experiment-task")).toHaveCount(12);
  await page
    .getByRole("link", { name: "Settings", exact: true })
    .first()
    .click();
  await expect(page.locator(".provider-setup-body")).toContainText(
    "setup_openrouter.py",
  );
  await expect(
    page.getByRole("heading", { name: "OpenRouter setup" }),
  ).toBeVisible();
  expect(errors).toEqual([]);
});

test("public results mode shows explanation and prevents execution", async ({
  page,
}) => {
  test.skip(
    !process.env.ARENA_PUBLIC_TEST_URL,
    "Requires separate read-only server",
  );
  const errors: string[] = [];
  page.on("pageerror", (e) => errors.push(e.message));
  await page.goto(`${process.env.ARENA_PUBLIC_TEST_URL}/experiments`);
  await expect(page.locator(".public-mode-banner")).toBeVisible();
  await expect(page.locator(".experiment-public")).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Run three-agent comparison" }),
  ).toHaveCount(0);
  const response = await page.request.post(
    `${process.env.ARENA_PUBLIC_TEST_URL}/api/experiments`,
    { data: {} },
  );
  expect(response.status()).toBe(403);
  await page.setViewportSize({ width: 390, height: 844 });
  await expect
    .poll(() =>
      page.evaluate(
        () => document.documentElement.scrollWidth <= window.innerWidth + 1,
      ),
    )
    .toBe(true);
  expect(errors).toEqual([]);
});

test("summary-only replay never presents a withheld artifact as an empty model answer", async ({
  page,
}) => {
  // UI boundary test using an explicitly transformed reference response, not model evidence.
  const response = await page.request.get(
    "/api/runs?agent_id=atlas&task_id=invoice-reconciliation",
  );
  const id = (await response.json()).items[0].id;
  await page.route(`**/api/runs/${id}`, async (route) => {
    const original = await route.fetch();
    const run = await original.json();
    await route.fulfill({
      json: {
        ...run,
        visibility: "summary-only",
        events: [],
        output: {},
        evaluation: { ...run.evaluation, checks: [] },
      },
    });
  });
  await page.goto(`/runs/${id}`);
  await expect(
    page.getByRole("heading", { name: "Execution trace withheld" }),
  ).toBeVisible();
  await expect(page.getByRole("button", { name: "Play replay" })).toHaveCount(
    0,
  );
  await page.getByRole("button", { name: "Final output", exact: true }).click();
  await expect(
    page.getByRole("heading", { name: "Final artifact withheld" }),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Download JSON", exact: true }),
  ).toHaveCount(0);
  await page.getByRole("button", { name: "Evaluation", exact: false }).click();
  await expect(
    page.getByRole("heading", { name: "Field-level evaluation withheld" }),
  ).toBeVisible();
});
