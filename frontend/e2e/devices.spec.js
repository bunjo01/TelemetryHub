import { expect, test } from "@playwright/test";

const companyId = "11111111-1111-4111-8111-111111111111";
const deviceTypes = ["temperature_sensor", "environment_sensor", "gps_tracker"];
const devices = Array.from({ length: 48 }, (_, index) => ({
  id: `22222222-2222-4222-8222-${String(index + 1).padStart(12, "0")}`,
  company_id: companyId,
  name: `Sensor ${String(index + 1).padStart(2, "0")}`,
  description: index % 2 === 0 ? "Warehouse monitoring" : null,
  device_type: deviceTypes[index % deviceTypes.length],
  status: index < 25 ? "active" : "inactive",
  created_at: "2026-10-24T12:00:00Z",
  updated_at: "2026-10-24T12:00:00Z",
}));

async function signIn(page, role = "company_owner") {
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
        company_id: role === "system_admin" ? null : companyId,
      },
    }),
  );
  await page.goto("/");
  await page.getByLabel("Email address").fill("crew@example.com");
  await page.getByLabel("Password", { exact: true }).fill("test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/profile$/);
}

function listResponse(params, source = devices) {
  const status = params.get("status");
  const search = (params.get("search") ?? "").toLowerCase();
  const offset = Number(params.get("offset"));
  const limit = Number(params.get("limit"));
  const matches = source.filter(
    (device) =>
      (status === "all" || device.status === status) &&
      device.name.toLowerCase().includes(search),
  );

  return {
    items: matches.slice(offset, offset + limit),
    limit,
    offset,
    has_more: offset + limit < matches.length,
  };
}

async function mockDevices(page, source = devices) {
  const requests = [];
  await page.route("**/api/devices?*", (route) => {
    const params = new URL(route.request().url()).searchParams;
    requests.push(Object.fromEntries(params));
    expect(route.request().headers().authorization).toBe("Bearer test-token");
    expect(params.get("limit")).toBe("20");
    return route.fulfill({ json: listResponse(params, source) });
  });
  return requests;
}

async function openDevices(page) {
  await page.getByRole("link", { name: "Devices", exact: true }).click();
  await expect(page).toHaveURL(/\/devices$/);
}

async function chooseStatus(page, label) {
  await page.getByRole("combobox", { name: "Status", exact: true }).click();
  await page
    .getByRole("listbox", { name: "Status", exact: true })
    .getByRole("option", { name: label, exact: true })
    .click();
}

async function navigateInSession(page, path) {
  await page.evaluate((destination) => {
    history.pushState({}, "", destination);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, path);
}

function deviceLinks(page) {
  return page
    .getByRole("list", { name: "Devices", exact: true })
    .getByRole("link");
}

for (const role of ["company_owner", "member"]) {
  test(`${role} can open the active device list with keyboard-accessible links`, async ({
    page,
  }) => {
    await mockDevices(page);
    await signIn(page, role);
    await openDevices(page);

    await expect(page).toHaveTitle("Devices · TelemetryHub");
    await expect(
      page.getByRole("heading", { name: "Devices", exact: true }),
    ).toBeFocused();
    await expect(
      page.getByRole("combobox", { name: "Status", exact: true }),
    ).toHaveText("Active");
    await expect(deviceLinks(page)).toHaveCount(20);
    await expect(
      page.getByRole("button", { name: "Previous", exact: true }),
    ).toBeDisabled();
    await expect(
      page.getByRole("button", { name: "Next", exact: true }),
    ).toBeEnabled();
    await expect(
      page.getByText("Temperature sensor", { exact: true }).first(),
    ).toBeVisible();

    const first = page.getByRole("link", { name: "Sensor 01", exact: true });
    await expect(first).toHaveAttribute("href", `/devices/${devices[0].id}`);
    await first.focus();
    await expect(first).toBeFocused();
    await page.keyboard.press("Tab");
    await expect(
      page.getByRole("link", { name: "Sensor 02", exact: true }),
    ).toBeFocused();
  });
}

test("unauthenticated visitors and system admins cannot access device data", async ({
  page,
}) => {
  const requests = await mockDevices(page);
  await page.goto("/devices");
  await expect(page).toHaveURL("/");
  await expect(
    page.getByRole("link", { name: "Devices", exact: true }),
  ).toHaveCount(0);

  await signIn(page, "system_admin");
  await expect(
    page.getByRole("link", { name: "Devices", exact: true }),
  ).toHaveCount(0);
  await navigateInSession(page, "/devices");
  await expect(page).toHaveURL(/\/profile$/);
  expect(requests).toEqual([]);
});

test("pagination and filters preserve browser history and details-link context", async ({
  page,
}) => {
  await mockDevices(page);
  await signIn(page);
  await openDevices(page);
  await expect(deviceLinks(page)).toHaveCount(20);

  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(page).toHaveURL(/\/devices\?offset=20$/);
  await expect(deviceLinks(page)).toHaveCount(5);
  await expect(
    page.getByRole("button", { name: "Next", exact: true }),
  ).toBeDisabled();

  await chooseStatus(page, "Inactive");
  await expect(page).toHaveURL(/\/devices\?status=inactive$/);
  await expect(deviceLinks(page)).toHaveCount(20);
  await expect(
    page.getByRole("link", { name: "Sensor 26", exact: true }),
  ).toHaveAttribute("href", `/devices/${devices[25].id}?status=inactive`);

  await page.goBack();
  await expect(page).toHaveURL(/\/devices\?offset=20$/);
  await expect(
    page.getByRole("combobox", { name: "Status", exact: true }),
  ).toHaveText("Active");
  await expect(deviceLinks(page)).toHaveCount(5);

  await page.goForward();
  await expect(
    page.getByRole("combobox", { name: "Status", exact: true }),
  ).toHaveText("Inactive");
  await expect(deviceLinks(page)).toHaveCount(20);

  await chooseStatus(page, "All");
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Sensor 21", exact: true }),
  ).toBeVisible();
  await page.getByRole("button", { name: "Previous", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Sensor 01", exact: true }),
  ).toBeVisible();
});

test("search debounces, resets pagination, preserves focus, and encodes special characters", async ({
  page,
}) => {
  const source = devices.map((device, index) =>
    index === 0 ? { ...device, name: "Freezer & cold" } : device,
  );
  const requests = await mockDevices(page, source);
  await signIn(page);
  await openDevices(page);
  await expect(deviceLinks(page)).toHaveCount(20);
  await page.getByRole("button", { name: "Next", exact: true }).click();
  await expect(deviceLinks(page)).toHaveCount(5);

  await page.clock.install();
  await page.clock.pauseAt(new Date());
  const search = page.getByLabel("Search devices", { exact: true });
  const before = requests.length;
  await search.fill("Free");
  await page.clock.runFor(100);
  await search.fill("Freezer & cold");
  await page.clock.runFor(249);
  expect(requests).toHaveLength(before);
  await page.clock.runFor(1);

  await expect(deviceLinks(page)).toHaveCount(1);
  expect(requests).toHaveLength(before + 1);
  expect(requests.at(-1)).toEqual({
    status: "active",
    limit: "20",
    offset: "0",
    search: "Freezer & cold",
  });
  await expect(search).toBeFocused();
  expect(new URL(page.url()).searchParams.get("search")).toBe("Freezer & cold");
  expect(new URL(page.url()).searchParams.has("offset")).toBe(false);

  const link = page.getByRole("link", { name: "Freezer & cold", exact: true });
  const destination = new URL(await link.getAttribute("href"), page.url());
  expect(destination.searchParams.get("search")).toBe("Freezer & cold");

  await search.fill("Sensor 02");
  await search.press("Enter");
  await expect(
    page.getByRole("link", { name: "Sensor 02", exact: true }),
  ).toBeVisible();
  await expect(search).toBeFocused();
  await page.clock.runFor(300);
  expect(requests).toHaveLength(before + 2);
});

test("normalizes malformed query parameters and restores valid search state", async ({
  page,
}) => {
  const requests = await mockDevices(page);
  await signIn(page);
  await navigateInSession(
    page,
    "/devices?status=unknown&offset=-20&extra=ignored",
  );
  await expect(page).toHaveURL(/\/devices$/);
  await expect(deviceLinks(page)).toHaveCount(20);
  expect(
    requests.every(
      (query) => query.status === "active" && query.offset === "0",
    ),
  ).toBe(true);

  await navigateInSession(page, "/devices?search=Sensor%2026&status=inactive");
  await expect(page.getByLabel("Search devices", { exact: true })).toHaveValue(
    "Sensor 26",
  );
  await expect(
    page.getByRole("combobox", { name: "Status", exact: true }),
  ).toHaveText("Inactive");
  await expect(deviceLinks(page)).toHaveCount(1);
});

test("distinguishes empty status, empty company, and no search matches", async ({
  page,
}) => {
  await mockDevices(page, []);
  await signIn(page);
  await openDevices(page);
  await expect(
    page.getByText("There are no active devices. Try another status."),
  ).toBeVisible();
  await chooseStatus(page, "All");
  await expect(
    page.getByText("Your company has no devices yet."),
  ).toBeVisible();
  await page.getByLabel("Search devices", { exact: true }).fill("missing");
  await expect(
    page.getByText("No devices match your search. Try another name or status."),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Previous", exact: true }),
  ).toBeDisabled();
  await expect(
    page.getByRole("button", { name: "Next", exact: true }),
  ).toBeDisabled();
});

test("allows returning from an empty later page", async ({ page }) => {
  await mockDevices(page);
  await signIn(page);
  await navigateInSession(page, "/devices?offset=40");

  await expect(
    page.getByText(
      "There are no devices on this page. Go back to the previous page.",
    ),
  ).toBeVisible();
  await expect(
    page.getByRole("button", { name: "Next", exact: true }),
  ).toBeDisabled();
  await page.getByRole("button", { name: "Previous", exact: true }).click();
  await expect(page).toHaveURL(/\/devices\?offset=20$/);
  await expect(deviceLinks(page)).toHaveCount(5);
});

test("cancels a pending search when leaving the list", async ({ page }) => {
  const requests = await mockDevices(page);
  await signIn(page);
  await openDevices(page);
  await expect(deviceLinks(page)).toHaveCount(20);

  await page.clock.install();
  await page.clock.pauseAt(new Date());
  const before = requests.length;
  await page
    .getByLabel("Search devices", { exact: true })
    .fill("pending search");
  await page
    .getByRole("link", { name: "TelemetryHub home", exact: true })
    .click();
  await expect(page).toHaveURL(/\/profile$/);
  await page.clock.runFor(300);

  await expect(page).toHaveURL(/\/profile$/);
  expect(requests).toHaveLength(before);
});

for (const failure of ["server", "network", "malformed response"]) {
  test(`recovers from a ${failure} failure using Retry`, async ({ page }) => {
    let attempts = 0;
    await page.route("**/api/devices?*", (route) => {
      attempts += 1;
      if (attempts === 1) {
        if (failure === "network") return route.abort("failed");
        if (failure === "server") {
          return route.fulfill({
            status: 503,
            json: { detail: "private database information" },
          });
        }
        return route.fulfill({ json: { items: null } });
      }
      return route.fulfill({
        json: listResponse(new URL(route.request().url()).searchParams),
      });
    });
    await signIn(page);
    await openDevices(page);
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByText("private database information")).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Next", exact: true }),
    ).toBeDisabled();
    await page.getByRole("button", { name: "Retry", exact: true }).click();
    await expect(deviceLinks(page)).toHaveCount(20);
    await expect(page.getByRole("alert")).toHaveCount(0);
    expect(attempts).toBe(2);
  });
}

test("shows denied company access without displaying devices or a retry action", async ({
  page,
}) => {
  await page.route("**/api/devices?*", (route) =>
    route.fulfill({ status: 403, json: { detail: "Company is unavailable." } }),
  );
  await signIn(page);
  await openDevices(page);
  await expect(page.getByRole("alert")).toHaveText(
    "Device access is unavailable for your account or company.",
  );
  await expect(deviceLinks(page)).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Retry", exact: true }),
  ).toHaveCount(0);
});

test("expires the session when device loading returns 401", async ({
  page,
}) => {
  await page.route("**/api/devices?*", (route) =>
    route.fulfill({ status: 401, json: {} }),
  );
  await signIn(page);
  await page.getByRole("link", { name: "Devices", exact: true }).click();
  await expect(page).toHaveURL(/\/\?expired=1$/);
  await expect(page.getByRole("alert")).toContainText("session has expired");
  await expect(page.getByRole("button", { name: "Sign out" })).toHaveCount(0);
  await navigateInSession(page, "/devices");
  await expect(page).toHaveURL("/");
});

test("shows pending state and keeps newer results when an older search finishes", async ({
  page,
}) => {
  let release;
  let finish;
  const blocked = new Promise((resolve) => {
    release = resolve;
  });
  const handled = new Promise((resolve) => {
    finish = resolve;
  });
  let oldSearchStarted = false;
  await page.route("**/api/devices?*", async (route) => {
    const params = new URL(route.request().url()).searchParams;
    if (params.get("search") === "Sensor 01") {
      oldSearchStarted = true;
      await blocked;
      try {
        await route.fulfill({ json: listResponse(params) });
      } finally {
        finish();
      }
      return;
    }
    await route.fulfill({ json: listResponse(params) });
  });
  try {
    await signIn(page);
    await openDevices(page);
    await expect(deviceLinks(page)).toHaveCount(20);
    const search = page.getByLabel("Search devices", { exact: true });
    await search.fill("Sensor 01");
    await expect.poll(() => oldSearchStarted).toBe(true);
    await expect(
      page.getByRole("region", { name: "Device results" }),
    ).toHaveAttribute("aria-busy", "true");
    await expect(page.getByRole("status")).toHaveText("Loading devices…");
    await expect(deviceLinks(page)).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Next", exact: true }),
    ).toBeDisabled();
    await search.fill("Sensor 02");
    await expect(
      page.getByRole("link", { name: "Sensor 02", exact: true }),
    ).toBeVisible();
    release();
    await handled;
    await expect(deviceLinks(page)).toHaveCount(1);
    await expect(
      page.getByRole("link", { name: "Sensor 01", exact: true }),
    ).toHaveCount(0);
    await expect(search).toBeFocused();
  } finally {
    release();
  }
});

test("status popup supports arrows, Home, End, and typing without committing early", async ({
  page,
}) => {
  const requests = await mockDevices(page);
  await signIn(page);
  await openDevices(page);
  await expect(deviceLinks(page)).toHaveCount(20);

  const status = page.getByRole("combobox", { name: "Status", exact: true });
  const options = page.getByRole("listbox", { name: "Status", exact: true });
  const before = requests.length;
  await status.focus();
  await status.press("ArrowDown");
  await expect(options).toBeVisible();
  await expect(
    options.getByRole("option", { name: "Active", exact: true }),
  ).toHaveAttribute("aria-selected", "true");
  await status.press("ArrowDown");
  await expect(status).toHaveText("Active");
  expect(requests).toHaveLength(before);
  await status.press("Enter");
  await expect(page).toHaveURL(/\/devices\?status=inactive$/);
  await expect(options).toHaveCount(0);
  await expect(status).toHaveText("Inactive");
  await expect(status).toBeFocused();
  await expect(
    page.getByRole("link", { name: "Sensor 26", exact: true }),
  ).toBeVisible();

  await status.press("Home");
  await status.press("Enter");
  await expect(status).toHaveText("Active");
  await expect(
    page.getByRole("link", { name: "Sensor 01", exact: true }),
  ).toBeVisible();

  await status.press("End");
  await status.press("Enter");
  await expect(page).toHaveURL(/\/devices\?status=all$/);
  await expect(status).toHaveText("All");
  await expect(deviceLinks(page)).toHaveCount(20);

  await status.press("i");
  const inactiveId = await options
    .getByRole("option", { name: "Inactive", exact: true })
    .getAttribute("id");
  await expect(status).toHaveAttribute("aria-activedescendant", inactiveId);
  await expect(status).toHaveText("All");
  await status.press("Enter");
  await expect(
    page.getByRole("link", { name: "Sensor 26", exact: true }),
  ).toBeVisible();
  await expect(status).toHaveText("Inactive");
});

test("status popup closes on Escape, Tab, and outside click without changing the filter", async ({
  page,
}) => {
  const requests = await mockDevices(page);
  await signIn(page);
  await openDevices(page);
  await expect(deviceLinks(page)).toHaveCount(20);
  const status = page.getByRole("combobox", { name: "Status", exact: true });
  const options = page.getByRole("listbox", { name: "Status", exact: true });
  const before = requests.length;

  await status.press("Space");
  await expect(options).toBeVisible();
  await status.press("ArrowDown");
  await status.press("Escape");
  await expect(status).toHaveAttribute("aria-expanded", "false");
  await expect(options).toHaveCount(0);
  await expect(status).toBeFocused();

  await status.click();
  await status.press("Tab");
  await expect(options).toHaveCount(0);
  await expect(
    page.getByRole("link", { name: "Sensor 01", exact: true }),
  ).toBeFocused();

  await status.click();
  await page.getByLabel("Search devices", { exact: true }).click();
  await expect(options).toHaveCount(0);
  await expect(
    page.getByLabel("Search devices", { exact: true }),
  ).toBeFocused();
  await expect(status).toHaveText("Active");
  expect(requests).toHaveLength(before);
});

test("status popup overlays results without shifting the toolbar on desktop and mobile", async ({
  page,
}, testInfo) => {
  await mockDevices(page);
  await signIn(page);
  await openDevices(page);
  await expect(deviceLinks(page)).toHaveCount(20);

  for (const width of [1440, 390, 320]) {
    await page.setViewportSize({ width, height: 800 });
    const status = page.getByRole("combobox", { name: "Status", exact: true });
    const first = page.getByRole("link", { name: "Sensor 01", exact: true });
    const triggerBefore = await status.boundingBox();
    const resultBefore = await first.boundingBox();
    await status.click();
    const options = page.getByRole("listbox", { name: "Status", exact: true });
    await expect(options).toBeVisible();
    expect(await status.boundingBox()).toEqual(triggerBefore);
    expect(await first.boundingBox()).toEqual(resultBefore);
    const bounds = await options.boundingBox();
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
    await page.screenshot({
      path: testInfo.outputPath(`status-popup-${width}.png`),
      fullPage: true,
    });
    await options.getByRole("option", { name: "All", exact: true }).click();
    await expect(options).toHaveCount(0);
    await expect(status).toHaveText("All");
    await expect(status).toBeFocused();
    await expect(first).toBeVisible();
  }
});

test("fits desktop and mobile widths with long device content", async ({
  page,
}, testInfo) => {
  const source = [
    {
      ...devices[0],
      name: "W".repeat(100),
      description: "Long description ".repeat(60),
    },
    { ...devices[1], name: "Device without description" },
  ];
  await mockDevices(page, source);
  await signIn(page, "member");
  await openDevices(page);
  await expect(deviceLinks(page)).toHaveCount(2);

  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 800 });
    const search = await page
      .getByLabel("Search devices", { exact: true })
      .boundingBox();
    const status = await page
      .getByLabel("Status", { exact: true })
      .boundingBox();
    if (width > 700) {
      expect(status.y + status.height).toBeCloseTo(search.y + search.height, 0);
      expect(status.x).toBeGreaterThan(search.x + search.width);
    } else {
      expect(status.y).toBeGreaterThan(search.y + search.height);
    }

    for (const link of await deviceLinks(page).all()) {
      const bounds = await link.boundingBox();
      expect(bounds.x).toBeGreaterThanOrEqual(0);
      expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
      expect(
        await link.evaluate(
          (element) => element.scrollWidth <= element.clientWidth,
        ),
      ).toBe(true);
    }
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    await page.screenshot({
      path: testInfo.outputPath(`devices-${width}.png`),
      fullPage: true,
    });
  }
});
