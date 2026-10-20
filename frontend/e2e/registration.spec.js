import { expect, test } from "@playwright/test";

const token = "a".repeat(43);
const password = "my long password 123";
async function preview(page) {
  await page.route("**/api/invitations/preview", async (route) => {
    expect(route.request().postDataJSON()).toEqual({ token });
    expect(route.request().headers().authorization).toBeUndefined();
    await route.fulfill({
      json: {
        email: "invited@example.com",
        expires_at: "2030-01-01T00:00:00Z",
      },
    });
  });
}
for (const role of ["company_owner", "member"]) {
  test(`${role} registers with invitation, matching passwords and no bearer token`, async ({
    page,
  }) => {
    await preview(page);
    let writes = 0;
    await page.route("**/api/invitations/accept", async (route) => {
      writes++;
      expect(route.request().postDataJSON()).toEqual({ token, password });
      expect(route.request().headers().authorization).toBeUndefined();
      await route.fulfill({
        status: 201,
        json: { email: "invited@example.com", role },
      });
    });
    await page.goto(`/register#token=${token}`);
    await expect(page.getByLabel("Email address")).toHaveValue(
      "invited@example.com",
    );
    await expect(page.getByLabel("Email address")).toHaveAttribute(
      "readonly",
      "",
    );
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByLabel("Confirm password").fill("different password");
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByRole("alert")).toContainText(
      "Passwords do not match",
    );
    expect(writes).toBe(0);
    await page.getByLabel("Confirm password").fill(password);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page).toHaveURL(/\/\?registered=1$/);
    await expect(page.getByRole("status")).toContainText("Account created");
    expect(writes).toBe(1);
    expect(
      await page.evaluate(() => localStorage.length + sessionStorage.length),
    ).toBe(0);
  });
}

test("missing or duplicate tokens never request preview", async ({ page }) => {
  let calls = 0;
  await page.route("**/api/invitations/preview", () => {
    calls++;
  });
  for (const suffix of ["", "#token=short", `#token=${token}&token=${token}`]) {
    await page.goto(`/register${suffix}`);
    await expect(page.getByRole("alert")).toContainText("missing or invalid");
    await expect(
      page.getByRole("button", { name: "Create account" }),
    ).toHaveCount(0);
  }
  expect(calls).toBe(0);
});

test("preview supports retry, refresh and expired links", async ({ page }) => {
  await page.route("**/api/invitations/preview", (route) =>
    route.fulfill({ status: 503, json: {} }),
  );
  await page.goto(`/register#token=${token}`);
  await expect(page.getByRole("button", { name: "Retry" })).toBeVisible();
  await preview(page);
  await page.getByRole("button", { name: "Retry" }).click();
  await expect(page.getByLabel("Email address")).toBeVisible();
  await page.reload();
  await expect(page.getByLabel("Email address")).toBeVisible();
  await page.route("**/api/invitations/preview", (route) =>
    route.fulfill({ status: 400, json: {} }),
  );
  await page.reload();
  await expect(page.getByRole("alert")).toContainText(
    "invalid, expired, or already used",
  );
  await expect(page.getByRole("button", { name: "Retry" })).toHaveCount(0);
});

for (const status of [400, 409, 503]) {
  test(`acceptance handles ${status} and clears passwords`, async ({
    page,
  }) => {
    await preview(page);
    await page.route("**/api/invitations/accept", (route) =>
      route.fulfill({ status, json: {} }),
    );
    await page.goto(`/register#token=${token}`);
    await page.getByLabel("Password", { exact: true }).fill(password);
    await page.getByLabel("Confirm password").fill(password);
    await page.getByRole("button", { name: "Create account" }).click();
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
    if (status !== 503)
      await expect(
        page.getByRole("button", { name: "Create account" }),
      ).toBeDisabled();
  });
}

test("registration fits desktop and mobile", async ({ page }) => {
  await preview(page);
  for (const [width, height] of [
    [1280, 720],
    [1366, 768],
    [390, 844],
  ]) {
    await page.setViewportSize({ width, height });
    await page.goto(`/register#token=${token}`);
    await expect(page.getByLabel("Email address")).toBeVisible();
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    if (width > 680)
      expect(
        await page.evaluate(
          () => document.documentElement.scrollHeight <= innerHeight,
        ),
      ).toBe(true);
  }
});

test("signed-in visitor must explicitly sign out to register", async ({
  page,
}) => {
  await page.route("**/api/auth/login", (route) =>
    route.fulfill({ json: { access_token: "test", token_type: "bearer" } }),
  );
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      json: { email: "admin@example.com", role: "system_admin" },
    }),
  );
  await preview(page);
  await page.goto("/");
  await page.getByLabel("Email address").fill("admin@example.com");
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/profile$/);
  await page.evaluate((url) => {
    history.pushState({}, "", url);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, `/register#token=${token}`);
  await expect(
    page.getByRole("button", { name: "Sign out to register" }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Sign out to register" }).click();
  await expect(page.getByLabel("Email address")).toHaveValue(
    "invited@example.com",
  );
  await expect(page).toHaveURL(new RegExp(`/register#token=${token}$`));
});

test("new invitation replaces obsolete preview and skip link preserves token", async ({
  page,
}) => {
  let releaseOld;
  const oldResponse = new Promise((resolve) => {
    releaseOld = resolve;
  });
  const second = "b".repeat(43);
  await page.route("**/api/invitations/preview", async (route) => {
    const isOld = route.request().postDataJSON().token === token;
    if (isOld) await oldResponse;
    await route.fulfill({
      json: {
        email: isOld ? "old@example.com" : "new@example.com",
        expires_at: "2030-01-01T00:00:00Z",
      },
    });
  });
  await page.goto(`/register#token=${token}`);
  await expect(page.getByRole("status")).toContainText("Checking");
  await page.evaluate((value) => {
    window.location.hash = `token=${value}`;
  }, second);
  await expect(page.getByLabel("Email address")).toHaveValue("new@example.com");
  releaseOld();
  await page.getByRole("link", { name: "Skip to content" }).focus();
  await page.keyboard.press("Enter");
  await expect(page.locator("main")).toBeFocused();
  await expect(page).toHaveURL(new RegExp(`#token=${second}$`));
  await expect(page.getByLabel("Email address")).toHaveValue("new@example.com");
});

test("submission is bounded, blocks duplicates and explains unknown outcomes", async ({
  page,
}) => {
  await preview(page);
  let release;
  const response = new Promise((resolve) => {
    release = resolve;
  });
  let writes = 0;
  await page.route("**/api/invitations/accept", async (route) => {
    writes++;
    await response;
    await route.abort();
  });
  await page.goto(`/register#token=${token}`);
  await page.getByLabel("Password", { exact: true }).fill(password);
  await page.getByLabel("Confirm password").fill(password);
  await page.getByRole("button", { name: "Create account" }).click();
  await expect(
    page.getByRole("button", { name: "Creating account" }),
  ).toBeDisabled();
  await page.locator("form").dispatchEvent("submit");
  expect(writes).toBe(1);
  release();
  await expect(page.getByRole("alert")).toContainText(
    "account may have been created",
  );
  await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
});
