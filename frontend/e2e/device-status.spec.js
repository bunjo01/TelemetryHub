import { expect, test } from "@playwright/test";

const original = {
  id: "55555555-5555-4555-8555-555555555555",
  company_id: "11111111-1111-4111-8111-111111111111",
  name: "Freezer sensor",
  description: "Warehouse freezer",
  device_type: "temperature_sensor",
  status: "active",
  created_at: "2026-11-12T12:00:00Z",
  updated_at: "2026-11-12T12:00:00Z",
};

async function setup(page, role = "company_owner", status = "active") {
  const state = {
    device: { ...original, status },
    writes: [],
    detailReads: 0,
    listReads: 0,
    writeFailure: 0,
    readFailure: 0,
    applyFailedWrite: false,
    hold: null,
  };
  await page.route("**/api/auth/login", (route) =>
    route.fulfill({
      json: { access_token: "test-token", token_type: "bearer" },
    }),
  );
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      json: {
        email: "crew@example.com",
        role,
        company_id: original.company_id,
      },
    }),
  );
  await page.route(
    (url) =>
      url.pathname === "/api/devices" ||
      url.pathname.startsWith("/api/devices/"),
    async (route) => {
      const url = new URL(route.request().url());
      expect(route.request().headers().authorization).toBe("Bearer test-token");
      if (url.pathname === "/api/devices") {
        state.listReads += 1;
        const status = url.searchParams.get("status");
        const offset = Number(url.searchParams.get("offset"));
        return route.fulfill({
          json: {
            items:
              offset === 0 &&
              (status === "all" || state.device.status === status)
                ? [state.device]
                : [],
            offset,
            limit: 20,
            has_more: false,
          },
        });
      }
      if (url.pathname === `/api/devices/${original.id}`) {
        state.detailReads += 1;
        return route.fulfill({
          status: state.readFailure || 200,
          json: state.readFailure ? {} : state.device,
        });
      }
      const action = url.pathname.split("/").at(-1);
      expect(["activate", "deactivate"]).toContain(action);
      expect(route.request().method()).toBe("POST");
      expect(route.request().postData()).toBeNull();
      state.writes.push(action);
      if (state.hold) await state.hold;
      if (!state.writeFailure || state.applyFailedWrite) {
        state.device = {
          ...state.device,
          status: action === "activate" ? "active" : "inactive",
          updated_at: "2026-11-12T13:00:00Z",
        };
      }
      return route.fulfill({
        status: state.writeFailure || 200,
        json: state.writeFailure ? {} : state.device,
      });
    },
  );
  await page.goto("/");
  await page.getByLabel("Email address").fill("crew@example.com");
  await page.getByLabel("Password", { exact: true }).fill("test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/profile$/);
  return state;
}

async function navigate(page, path) {
  await page.evaluate((value) => {
    history.pushState({}, "", value);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, path);
}

function statusSwitch(page) {
  return page.getByRole("switch", {
    name: "Freezer sensor: device active",
    exact: true,
  });
}

test("members see status badges without switches on either page", async ({
  page,
}) => {
  await setup(page, "member");
  await navigate(page, "/devices");
  await expect(
    page.getByRole("link", { name: original.name, exact: true }),
  ).toBeVisible();
  await expect(page.getByRole("switch")).toHaveCount(0);
  await page.getByRole("link", { name: original.name, exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    original.name,
  );
  await expect(page.getByText("Active", { exact: true })).toBeVisible();
  await expect(page.getByRole("switch")).toHaveCount(0);
});

for (const pageName of ["list", "details"]) {
  test(`${pageName} requests confirmation before deactivation and preserves state on cancel`, async ({
    page,
  }) => {
    const state = await setup(page);
    const path = pageName === "list" ? "/devices" : `/devices/${original.id}`;
    await navigate(page, path);
    const control = statusSwitch(page);
    await expect(control).toHaveAttribute("aria-checked", "true");
    expect(
      await control.evaluate((element) => element.closest("a") === null),
    ).toBe(true);
    await control.focus();
    await control.press("Space");
    const dialog = page.getByRole("dialog", {
      name: `Deactivate “${original.name}”?`,
      exact: true,
    });
    await expect(dialog).toBeVisible();
    await expect(dialog).toContainText(
      "hidden from the default Active devices list",
    );
    expect(state.writes).toEqual([]);
    await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await expect(control).toHaveAttribute("aria-checked", "true");
    await expect(control).toBeFocused();
    await expect(page).toHaveURL(path);
  });
}

test("deactivates from the Active list and removes the row after confirmation", async ({
  page,
}) => {
  const state = await setup(page);
  await navigate(page, "/devices");
  await statusSwitch(page).click();
  await page
    .getByRole("dialog")
    .getByRole("button", { name: "Deactivate device", exact: true })
    .click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(
    page.getByText("There are no active devices. Try another status."),
  ).toBeVisible();
  await expect(statusSwitch(page)).toHaveCount(0);
  await expect(
    page.getByText("Freezer sensor was deactivated.", { exact: true }),
  ).toBeVisible();
  expect(state.writes).toEqual(["deactivate"]);
  expect(state.listReads).toBe(2);
});

test("activates immediately from Inactive and removes the row from that filter", async ({
  page,
}) => {
  const state = await setup(page, "company_owner", "inactive");
  await navigate(page, "/devices?status=inactive");
  await expect(statusSwitch(page)).toHaveAttribute("aria-checked", "false");
  await statusSwitch(page).click();
  await expect(
    page.getByText("There are no inactive devices. Try another status."),
  ).toBeVisible();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  expect(state.writes).toEqual(["activate"]);
});

test("keeps the All-list row and updates confirmed state without reloading the list", async ({
  page,
}) => {
  const state = await setup(page, "company_owner", "inactive");
  await navigate(page, "/devices?status=all");
  await expect(statusSwitch(page)).toHaveAttribute("aria-checked", "false");
  await statusSwitch(page).press("Enter");
  await expect(statusSwitch(page)).toHaveAttribute("aria-checked", "true");
  await expect(page).toHaveURL("/devices?status=all");
  expect(state.listReads).toBe(1);
  expect(state.writes).toEqual(["activate"]);
});

test("keeps the confirmed state and blocks editing while a status request is pending", async ({
  page,
}) => {
  const state = await setup(page, "company_owner", "inactive");
  let release;
  state.hold = new Promise((resolve) => {
    release = resolve;
  });
  try {
    await navigate(page, `/devices/${original.id}`);
    await statusSwitch(page).click();
    await expect.poll(() => state.writes.length).toBe(1);
    await expect(statusSwitch(page)).toHaveAttribute("aria-checked", "false");
    await expect(statusSwitch(page)).toHaveAttribute("aria-busy", "true");
    await expect(statusSwitch(page)).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Edit device", exact: true }),
    ).toBeDisabled();
    release();
    await expect(statusSwitch(page)).toHaveAttribute("aria-checked", "true");
    await expect(statusSwitch(page)).toBeEnabled();
    await expect(
      page.getByRole("button", { name: "Edit device", exact: true }),
    ).toBeEnabled();
    expect(state.writes).toEqual(["activate"]);
  } finally {
    release();
  }
});

test("preserves status after a forbidden deactivation and allows cancelling the confirmation", async ({
  page,
}) => {
  const state = await setup(page);
  state.writeFailure = 403;
  await navigate(page, `/devices/${original.id}`);
  await statusSwitch(page).click();
  const dialog = page.getByRole("dialog");
  await dialog
    .getByRole("button", { name: "Deactivate device", exact: true })
    .click();
  await expect(dialog.getByRole("alert")).toHaveText(
    "You do not have permission to do this.",
  );
  await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
  await expect(statusSwitch(page)).toHaveAttribute("aria-checked", "true");
  expect(state.writes).toEqual(["deactivate"]);
  expect(state.detailReads).toBe(1);
});

test("reconciles an uncertain write without sending it again", async ({
  page,
}) => {
  const state = await setup(page, "company_owner", "inactive");
  state.writeFailure = 503;
  state.applyFailedWrite = true;
  await navigate(page, `/devices/${original.id}`);
  await statusSwitch(page).click();
  await expect(statusSwitch(page)).toHaveAttribute("aria-checked", "true");
  await expect(statusSwitch(page)).toBeEnabled();
  await expect(
    page.getByText(
      "Device status refreshed. Check its current state before trying again.",
      { exact: true },
    ),
  ).toBeVisible();
  expect(state.writes).toEqual(["activate"]);
  expect(state.detailReads).toBe(2);
});

test("blocks further changes until failed reconciliation is retried successfully", async ({
  page,
}) => {
  const state = await setup(page, "company_owner", "inactive");
  await navigate(page, `/devices/${original.id}`);
  await expect(statusSwitch(page)).toBeEnabled();
  state.writeFailure = 503;
  state.readFailure = 503;
  await statusSwitch(page).click();
  await expect(page.getByRole("alert")).toContainText("could not be verified");
  await expect(statusSwitch(page)).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Edit device", exact: true }),
  ).toBeDisabled();
  state.readFailure = 0;
  await page
    .getByRole("button", { name: "Refresh status", exact: true })
    .click();
  await expect(statusSwitch(page)).toBeEnabled();
  await expect(statusSwitch(page)).toHaveAttribute("aria-checked", "false");
  await expect(
    page.getByRole("button", { name: "Edit device", exact: true }),
  ).toBeEnabled();
  expect(state.writes).toEqual(["activate"]);
  expect(state.detailReads).toBe(3);
});

test("expires the session after an unauthorized status request", async ({
  page,
}) => {
  const state = await setup(page, "company_owner", "inactive");
  state.writeFailure = 401;
  await navigate(page, `/devices/${original.id}`);
  await statusSwitch(page).click();
  await expect(page).toHaveURL(/\/\?expired=1$/);
  await expect(page.getByRole("alert")).toContainText("session has expired");
});

test("fits switches on narrow list cards and respects reduced motion", async ({
  page,
}, testInfo) => {
  await setup(page);
  await page.emulateMedia({ reducedMotion: "reduce" });
  await navigate(page, "/devices");
  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 800 });
    const control = statusSwitch(page);
    await expect(control).toBeVisible();
    const bounds = await control.boundingBox();
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    expect(
      await control.evaluate((element) =>
        [...element.children].every((child) =>
          getComputedStyle(child)
            .transitionDuration.split(",")
            .every((duration) => parseFloat(duration) === 0),
        ),
      ),
    ).toBe(true);
    await page.screenshot({
      path: testInfo.outputPath(`device-switch-${width}.png`),
      fullPage: true,
    });
  }
});
