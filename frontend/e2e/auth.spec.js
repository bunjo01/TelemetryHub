import { expect, test } from "@playwright/test";

async function signIn(page, role = "system_admin") {
  await page.route("**/api/auth/login", (route) =>
    route.fulfill({
      json: { access_token: "test-token", token_type: "bearer" },
    }),
  );
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      json: {
        id: "never-show-this",
        email: "crew@example.com",
        role,
        status: "active",
      },
    }),
  );
  await page.goto("/");
  await page.getByLabel("Email address").fill("crew@example.com");
  await page.getByLabel("Password", { exact: true }).fill("test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/profile$/);
}

test("admin signs in, creates a company and signs out", async ({ page }) => {
  await signIn(page);
  await expect(
    page.getByText("System administrator", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("never-show-this")).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Invite owner" }),
  ).toBeEnabled();
  await page.getByRole("button", { name: "Create company" }).click();
  await expect(page.getByLabel("Company name")).toBeFocused();
  await page.route("**/api/companies", async (route) => {
    expect(route.request().postDataJSON()).toEqual({ name: "Orbital Labs" });
    expect(route.request().headers().authorization).toBe("Bearer test-token");
    await route.fulfill({ status: 201, json: { name: "Orbital Labs" } });
  });
  await page.getByLabel("Company name").fill("Orbital Labs");
  await page
    .locator("form")
    .getByRole("button", { name: "Create", exact: true })
    .click();
  await expect(page.getByRole("status")).toContainText(
    "Orbital Labs was created",
  );
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page).toHaveURL("/");
  await page.goto("/profile");
  await expect(page).toHaveURL("/");
});
for (const role of ["company_owner", "member"]) {
  test(`${role} sees only appropriate actions, also on mobile`, async ({
    page,
  }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await signIn(page, role);
    await expect(
      page.getByRole("button", { name: "Create company" }),
    ).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Invite owner" }),
    ).toHaveCount(0);
    if (role === "company_owner")
      await expect(
        page.getByRole("button", { name: "Invite member" }),
      ).toBeDisabled();
    else
      await expect(
        page.getByRole("button", { name: "Invite member" }),
      ).toHaveCount(0);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.reload();
    await expect(page).toHaveURL("/");
  });
}
test("failed login is shown and password is cleared", async ({ page }) => {
  await page.route("**/api/auth/login", (route) =>
    route.fulfill({ status: 401, json: {} }),
  );
  await page.goto("/");
  await page.getByLabel("Email address").fill("crew@example.com");
  await page.getByLabel("Password", { exact: true }).fill("wrong");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByRole("alert")).toContainText(
    "Invalid email or password",
  );
  await expect(page.getByLabel("Password", { exact: true })).toHaveValue("");
});
test("expired session redirects to login with an explanation", async ({
  page,
}) => {
  await signIn(page);
  await page.route("**/api/companies", (route) =>
    route.fulfill({ status: 401, json: {} }),
  );
  await page.getByRole("button", { name: "Create company" }).click();
  await page.getByLabel("Company name").fill("Orbital Labs");
  await page
    .locator("form")
    .getByRole("button", { name: "Create", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText("session has expired");
});

test("company failure preserves input and closing returns keyboard focus", async ({
  page,
}) => {
  await signIn(page);
  await page.route("**/api/companies", (route) =>
    route.fulfill({ status: 503, json: {} }),
  );
  await page.getByRole("button", { name: "Create company" }).click();
  await page.getByLabel("Company name").fill("Orbital Labs");
  await page
    .locator("form")
    .getByRole("button", { name: "Create", exact: true })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "temporarily unavailable",
  );
  await expect(page.getByLabel("Company name")).toHaveValue("Orbital Labs");
  await page.getByRole("button", { name: "Close create company" }).click();
  await expect(
    page.getByRole("button", { name: "Create company" }),
  ).toBeFocused();
});

test("desktop and mobile pages fit their viewport", async ({
  page,
}, testInfo) => {
  await page.setViewportSize({ width: 1440, height: 1000 });
  await page.goto("/");
  await page.screenshot({
    path: testInfo.outputPath("iotmonitor-login.png"),
    fullPage: true,
  });
  await signIn(page);
  await page.screenshot({
    path: testInfo.outputPath("iotmonitor-profile.png"),
    fullPage: true,
  });
  await page.setViewportSize({ width: 375, height: 812 });
  await page.screenshot({
    path: testInfo.outputPath("iotmonitor-profile-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
  await page.getByRole("button", { name: "Sign out" }).click();
  await page.screenshot({
    path: testInfo.outputPath("iotmonitor-login-mobile.png"),
    fullPage: true,
  });
  expect(
    await page.evaluate(
      () => document.documentElement.scrollWidth <= innerWidth,
    ),
  ).toBe(true);
});

test("company popup traps focus, closes with Escape and resets when reopened", async ({
  page,
}) => {
  await page.setViewportSize({ width: 375, height: 812 });
  await signIn(page);
  await page
    .getByRole("button", { name: "Create company", exact: true })
    .click();
  const dialog = page.getByRole("dialog", { name: "Create company" });
  await expect(dialog).toBeVisible();
  await expect(page).toHaveURL(/\/profile$/);
  await expect(dialog.getByRole("textbox")).toHaveCount(1);
  await expect(page.getByLabel("Company name")).toBeFocused();
  await page.getByLabel("Company name").fill("Unsubmitted company");
  await page.keyboard.press("Tab");
  await expect(
    dialog.getByRole("button", { name: "Create", exact: true }),
  ).toBeFocused();
  await page.keyboard.press("Shift+Tab");
  await page.keyboard.press("Shift+Tab");
  await expect(
    dialog.getByRole("button", { name: "Close create company" }),
  ).toBeFocused();
  const bounds = await dialog.boundingBox();
  expect(bounds.x).toBeGreaterThanOrEqual(0);
  expect(bounds.x + bounds.width).toBeLessThanOrEqual(375);
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
  await expect(
    page.getByRole("button", { name: "Create company", exact: true }),
  ).toBeFocused();
  await page
    .getByRole("button", { name: "Create company", exact: true })
    .click();
  await expect(page.getByLabel("Company name")).toHaveValue("");
});

test("admin searches and selects a company before inviting its owner", async ({
  page,
}) => {
  await signIn(page);
  const companyId = "28f63fb6-b64f-4607-bb79-a6e815ab9131";
  await page.route("**/api/companies?*", (route) => {
    const query = new URL(route.request().url()).searchParams.get("q");
    return route.fulfill({
      json: {
        items:
          query === "missing" ? [] : [{ id: companyId, name: "Orbital Labs" }],
        has_more: false,
      },
    });
  });
  await page.route(
    `**/api/companies/${companyId}/owner-invitations`,
    async (route) => {
      expect(route.request().postDataJSON()).toEqual({
        email: "owner@example.com",
      });
      await route.fulfill({
        status: 201,
        json: {
          email: "owner@example.com",
          token: "a".repeat(43),
          expires_at: "2030-01-01T00:00:00Z",
        },
      });
    },
  );
  await page.getByRole("button", { name: "Invite owner", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Invite company owner" });
  await expect(dialog.getByLabel("Owner email address")).toBeFocused();
  await dialog.getByLabel("Owner email address").fill("owner@example.com");
  await dialog.locator("summary").click();
  await dialog.getByLabel("Search companies").fill("missing");
  await expect(dialog.getByText(/No companies found/)).toBeVisible();
  await dialog.getByLabel("Search companies").fill("Orbital");
  await dialog
    .getByRole("button", { name: "Orbital Labs", exact: true })
    .click();
  await expect(dialog.locator("summary")).toContainText("Orbital Labs");
  await expect(dialog.getByText(companyId)).toHaveCount(0);
  await dialog
    .getByRole("button", { name: "Invite owner", exact: true })
    .click();
  await expect(dialog.getByRole("status")).toContainText("Invitation created");
  await expect(dialog.getByLabel("Invitation token")).toHaveValue(
    "a".repeat(43),
  );
  await expect(dialog.getByText(/No email was sent/)).toBeVisible();
  await dialog.getByRole("button", { name: "Close invite owner" }).click();
  await expect(
    page.getByRole("button", { name: "Invite owner", exact: true }),
  ).toBeFocused();
  await page.getByRole("button", { name: "Invite owner", exact: true }).click();
  await expect(page.getByLabel("Invitation token")).toHaveCount(0);
});

test("invitation requires selection and preserves input on conflict", async ({
  page,
}) => {
  await signIn(page);
  await page.route("**/api/companies?*", (route) =>
    route.fulfill({
      json: {
        items: [
          { id: "28f63fb6-b64f-4607-bb79-a6e815ab9131", name: "Orbital Labs" },
        ],
        has_more: false,
      },
    }),
  );
  await page.route("**/owner-invitations", (route) =>
    route.fulfill({ status: 409, json: {} }),
  );
  await page.getByRole("button", { name: "Invite owner", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.getByLabel("Owner email address").fill("owner@example.com");
  await dialog
    .getByRole("button", { name: "Invite owner", exact: true })
    .click();
  await expect(dialog.getByRole("alert")).toContainText("Choose a company");
  await dialog.getByRole("button", { name: "Orbital Labs" }).click();
  await dialog
    .getByRole("button", { name: "Invite owner", exact: true })
    .click();
  await expect(dialog.getByRole("alert")).toContainText("pending invitation");
  await expect(dialog.getByLabel("Owner email address")).toHaveValue(
    "owner@example.com",
  );
});

test("company search pages results and ignores obsolete responses", async ({
  page,
}, testInfo) => {
  await signIn(page);
  let finishOldSearch;
  let oldSearchStarted;
  const started = new Promise((resolve) => {
    oldSearchStarted = resolve;
  });
  const company = (name) => ({
    id: "28f63fb6-b64f-4607-bb79-a6e815ab9131",
    name,
  });
  await page.route("**/api/companies?*", async (route) => {
    const params = new URL(route.request().url()).searchParams;
    if (params.get("q") === "old") {
      oldSearchStarted();
      await new Promise((resolve) => {
        finishOldSearch = resolve;
      });
      await route.fulfill({
        json: { items: [company("Obsolete company")], has_more: false },
      });
      return;
    }
    const isNext = params.get("offset") === "20";
    await route.fulfill({
      json: {
        items: isNext
          ? [company("Second company")]
          : Array.from({ length: 8 }, (_, index) => ({
              id: `28f63fb6-b64f-4607-bb79-a6e815ab913${index}`,
              name:
                index === 0 ? "Orbital Labs" : `Orbital Station ${index + 1}`,
            })),
        has_more: !isNext,
      },
    });
  });
  await page.getByRole("button", { name: "Invite owner", exact: true }).click();
  const dialog = page.getByRole("dialog");
  await dialog.locator("summary").click();
  await dialog.getByRole("button", { name: "Next", exact: true }).click();
  await expect(
    dialog.getByRole("button", { name: "Second company" }),
  ).toBeVisible();
  await dialog.getByLabel("Search companies").fill("old");
  await started;
  await dialog.getByLabel("Search companies").fill("Orbital");
  await expect(
    dialog.getByRole("button", { name: "Orbital Labs" }),
  ).toBeVisible();
  finishOldSearch();
  await expect(
    dialog.getByRole("button", { name: "Obsolete company" }),
  ).toHaveCount(0);
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({
    path: testInfo.outputPath("invite-owner-mobile.png"),
    fullPage: true,
  });
  await page.keyboard.press("Escape");
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Search companies")).not.toBeVisible();
  await page.keyboard.press("Escape");
  await expect(dialog).not.toBeVisible();
});
