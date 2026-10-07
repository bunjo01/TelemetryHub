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
  ).toBeDisabled();
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
    .getByRole("button", { name: "Create company" })
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
    .getByRole("button", { name: "Create company" })
    .click();
  await expect(page.getByRole("alert")).toContainText("session has expired");
});

test("company failure preserves input and cancel returns keyboard focus", async ({
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
    .getByRole("button", { name: "Create company" })
    .click();
  await expect(page.getByRole("alert")).toContainText(
    "temporarily unavailable",
  );
  await expect(page.getByLabel("Company name")).toHaveValue("Orbital Labs");
  await page.getByRole("button", { name: "Cancel" }).click();
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
