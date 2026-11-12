import { expect, test } from "@playwright/test";

test.use({ locale: "en-GB", timezoneId: "Europe/Belgrade" });

const companyId = "11111111-1111-4111-8111-111111111111";
const devices = Array.from({ length: 24 }, (_, index) => ({
  id: `33333333-3333-4333-8333-${String(index + 1).padStart(12, "0")}`,
  company_id: companyId,
  name: `Freezer sensor ${String(index + 1).padStart(2, "0")}`,
  description: "Main warehouse\nCold storage",
  device_type: "temperature_sensor",
  status: "inactive",
  created_at: "2026-11-10T12:00:00Z",
  updated_at: "2026-11-11T14:30:00Z",
}));
const device = devices[0];

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

async function navigateInSession(page, path) {
  await page.evaluate((destination) => {
    history.pushState({}, "", destination);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }, path);
}

async function mockDetails(page, source = devices) {
  const requests = [];
  await page.route("**/api/devices/*", (route) => {
    const id = new URL(route.request().url()).pathname.split("/").at(-1);
    requests.push(id);
    expect(route.request().method()).toBe("GET");
    expect(route.request().headers().authorization).toBe("Bearer test-token");
    const result = source.find((item) => item.id === id);
    return route.fulfill({
      status: result ? 200 : 404,
      json: result ?? { detail: "Device not found." },
    });
  });
  return requests;
}

async function openDetails(page, selected = device) {
  await navigateInSession(page, `/devices/${selected.id}`);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    selected.name,
  );
}

for (const role of ["company_owner", "member"]) {
  test(`${role} can view inactive device metadata and local timestamps`, async ({
    page,
  }) => {
    await mockDetails(page);
    await signIn(page, role);
    await openDetails(page);

    await expect(page).toHaveTitle("Device details · TelemetryHub");
    await expect(
      page.getByRole("button", { name: "Edit device", exact: true }),
    ).toHaveCount(role === "company_owner" ? 1 : 0);
    await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
    await expect(page.getByText("Inactive", { exact: true })).toBeVisible();
    const information = page.getByRole("region", {
      name: "Device information",
    });
    await expect(information).toHaveAttribute("aria-busy", "false");
    await expect(information.getByText(device.description)).toBeVisible();
    await expect(
      information.getByText("Temperature sensor", { exact: true }),
    ).toBeVisible();
    await expect(
      information.getByText(device.id, { exact: true }),
    ).toBeVisible();
    await expect(information.locator("time").nth(0)).toHaveAttribute(
      "datetime",
      device.created_at,
    );
    await expect(information.locator("time").nth(0)).toHaveText(
      "10 Nov 2026, 13:00",
    );
    await expect(information.locator("time").nth(1)).toHaveText(
      "11 Nov 2026, 15:30",
    );
    await expect(
      page.getByRole("button", { name: "Copy device ID", exact: true }),
    ).toBeEnabled();
  });
}

test("edits an inactive device in place using the server response and preserves return context", async ({
  page,
}) => {
  const writes = [];
  let reads = 0;
  let stored = { ...device };
  await page.route(`**/api/devices/${device.id}`, (route) => {
    expect(route.request().headers().authorization).toBe("Bearer test-token");
    if (route.request().method() === "PATCH") {
      const changes = route.request().postDataJSON();
      writes.push(changes);
      stored = { ...stored, ...changes, updated_at: "2026-11-12T15:00:00Z" };
    } else {
      expect(route.request().method()).toBe("GET");
      reads += 1;
    }
    return route.fulfill({ json: stored });
  });
  await signIn(page);
  const path = `/devices/${device.id}?search=Freezer&status=inactive&offset=20`;
  await navigateInSession(page, path);
  const edit = page.getByRole("button", { name: "Edit device", exact: true });
  await edit.click();
  const dialog = page.getByRole("dialog", { name: "Edit device", exact: true });
  const name = dialog.getByLabel("Device name", { exact: true });
  const description = dialog.getByLabel("Description (optional)", {
    exact: true,
  });
  const save = dialog.getByRole("button", {
    name: "Save changes",
    exact: true,
  });
  await expect(name).toBeFocused();
  await expect(name).toHaveValue(device.name);
  await expect(description).toHaveValue(device.description);
  await expect(dialog.getByLabel("Device type", { exact: true })).toHaveValue(
    "Temperature sensor",
  );
  await expect(
    dialog.getByLabel("Device type", { exact: true }),
  ).toBeDisabled();
  await expect(dialog.getByRole("combobox")).toHaveCount(0);
  await expect(save).toBeDisabled();
  await name.fill("  Renamed freezer  ");
  await description.fill("");
  await save.click();

  await expect(dialog).toHaveCount(0);
  await expect(page).toHaveURL(path);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    "Renamed freezer",
  );
  await expect(
    page.getByText("No description provided.", { exact: true }),
  ).toBeVisible();
  await expect(page.getByText("Inactive", { exact: true })).toBeVisible();
  await expect(page.locator("time").nth(1)).toHaveText("12 Nov 2026, 16:00");
  await expect(
    page.getByText("Device changes saved.", { exact: true }),
  ).toBeVisible();
  await expect(edit).toBeFocused();
  await expect(
    page.getByRole("link", { name: "Back to devices" }),
  ).toHaveAttribute(
    "href",
    "/devices?search=Freezer&status=inactive&offset=20",
  );
  expect(writes).toEqual([{ name: "Renamed freezer", description: null }]);
  expect(reads).toBe(1);

  await edit.click();
  await expect(name).toHaveValue("Renamed freezer");
  await expect(description).toHaveValue("");
  await expect(save).toBeDisabled();
});

test("cancels edits without changing the device and discards the draft on reopen", async ({
  page,
}) => {
  await mockDetails(page);
  await signIn(page);
  await openDetails(page);
  const edit = page.getByRole("button", { name: "Edit device", exact: true });
  await edit.click();
  const dialog = page.getByRole("dialog", { name: "Edit device", exact: true });
  await dialog.getByLabel("Device name", { exact: true }).fill("Unsaved name");
  await page.keyboard.press("Escape");
  await expect(dialog).toHaveCount(0);
  await expect(edit).toBeFocused();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(device.name);
  await edit.click();
  await expect(dialog.getByLabel("Device name", { exact: true })).toHaveValue(
    device.name,
  );
  await expect(
    dialog.getByRole("button", { name: "Save changes", exact: true }),
  ).toBeDisabled();
});

for (const status of [403, 404, 503]) {
  test(`preserves the edit draft and existing details after a ${status} response`, async ({
    page,
  }) => {
    let writes = 0;
    await page.route(`**/api/devices/${device.id}`, (route) => {
      if (route.request().method() === "PATCH") {
        writes += 1;
        return route.fulfill({
          status,
          json: { detail: "private backend information" },
        });
      }
      return route.fulfill({ json: device });
    });
    await signIn(page);
    await openDetails(page);
    await page
      .getByRole("button", { name: "Edit device", exact: true })
      .click();
    const dialog = page.getByRole("dialog", {
      name: "Edit device",
      exact: true,
    });
    const name = dialog.getByLabel("Device name", { exact: true });
    await name.fill("Draft name");
    await dialog
      .getByRole("button", { name: "Save changes", exact: true })
      .click();
    await expect(dialog.getByRole("alert")).toBeVisible();
    if (status === 503)
      await expect(dialog.getByRole("alert")).toContainText(
        "Check the device details before trying again.",
      );
    await expect(dialog.getByText("private backend information")).toHaveCount(
      0,
    );
    await expect(name).toHaveValue("Draft name");
    await expect(
      dialog.getByRole("button", { name: "Save changes", exact: true }),
    ).toBeEnabled();
    expect(writes).toBe(1);
    await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      device.name,
    );
  });
}

test("expires the session when saving an edit returns 401", async ({
  page,
}) => {
  await page.route(`**/api/devices/${device.id}`, (route) =>
    route.fulfill({
      status: route.request().method() === "PATCH" ? 401 : 200,
      json: route.request().method() === "PATCH" ? {} : device,
    }),
  );
  await signIn(page);
  await openDetails(page);
  await page.getByRole("button", { name: "Edit device", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Edit device", exact: true });
  await dialog.getByLabel("Device name", { exact: true }).fill("Draft name");
  await dialog
    .getByRole("button", { name: "Save changes", exact: true })
    .click();
  await expect(page).toHaveURL(/\/\?expired=1$/);
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("alert")).toContainText("session has expired");
});

test("closes an open edit session when navigating to a different device", async ({
  page,
}) => {
  await mockDetails(page);
  await signIn(page);
  await openDetails(page);
  await page.getByRole("button", { name: "Edit device", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Edit device", exact: true });
  await dialog
    .getByLabel("Device name", { exact: true })
    .fill("Old device draft");
  await openDetails(page, devices[1]);
  await expect(dialog).toHaveCount(0);
  await page.getByRole("button", { name: "Edit device", exact: true }).click();
  await expect(dialog.getByLabel("Device name", { exact: true })).toHaveValue(
    devices[1].name,
  );
});

test("restores search, status and pagination through the return link and browser history", async ({
  page,
}) => {
  const listRequests = [];
  await page.route("**/api/devices?*", (route) => {
    const params = new URL(route.request().url()).searchParams;
    listRequests.push(Object.fromEntries(params));
    const offset = Number(params.get("offset"));
    const limit = Number(params.get("limit"));
    return route.fulfill({
      json: {
        items: devices.slice(offset, offset + limit),
        offset,
        limit,
        has_more: offset + limit < devices.length,
      },
    });
  });
  await mockDetails(page);
  await signIn(page);
  const listPath = "/devices?search=Freezer&status=inactive&offset=20";
  await navigateInSession(page, listPath);
  const link = page.getByRole("link", { name: devices[20].name, exact: true });
  await link.focus();
  await link.press("Enter");
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    devices[20].name,
  );
  await expect(
    page.getByRole("link", { name: "Back to devices" }),
  ).toHaveAttribute("href", listPath);

  await page.goBack();
  await expect(page).toHaveURL(listPath);
  await expect(page.getByLabel("Search devices", { exact: true })).toHaveValue(
    "Freezer",
  );
  await expect(
    page.getByRole("combobox", { name: "Status", exact: true }),
  ).toHaveText("Inactive");
  await expect(link).toBeVisible();

  await page.goForward();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    devices[20].name,
  );
  const before = listRequests.length;
  await page.getByRole("link", { name: "Back to devices" }).click();
  await expect(page).toHaveURL(listPath);
  await expect(link).toBeVisible();
  expect(listRequests.length).toBeGreaterThan(before);
  expect(listRequests.at(-1)).toEqual({
    search: "Freezer",
    status: "inactive",
    offset: "20",
    limit: "20",
  });
});

test("recovers an empty page when returning from details after the list changes", async ({
  page,
}) => {
  let source = devices;
  const requests = [];
  await page.route("**/api/devices?*", (route) => {
    const params = new URL(route.request().url()).searchParams;
    requests.push(Object.fromEntries(params));
    const offset = Number(params.get("offset"));
    const limit = Number(params.get("limit"));
    return route.fulfill({
      json: {
        items: source.slice(offset, offset + limit),
        offset,
        limit,
        has_more: offset + limit < source.length,
      },
    });
  });
  await mockDetails(page);
  await signIn(page);
  await navigateInSession(
    page,
    "/devices?search=Freezer&status=inactive&offset=20",
  );
  await page.getByRole("link", { name: devices[20].name, exact: true }).click();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    devices[20].name,
  );
  source = devices.slice(0, 20);
  const before = requests.length;
  await page.getByRole("link", { name: "Back to devices" }).click();
  await expect(page).toHaveURL("/devices?search=Freezer&status=inactive");
  await expect(
    page.getByRole("list", { name: "Devices", exact: true }).getByRole("link"),
  ).toHaveCount(20);
  expect(requests.slice(before).map((query) => query.offset)).toEqual([
    "20",
    "0",
  ]);
  expect(
    requests
      .slice(before)
      .every(
        (query) => query.search === "Freezer" && query.status === "inactive",
      ),
  ).toBe(true);
  await page.goBack();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    devices[20].name,
  );
});

test("defaults direct-entry return navigation to Active and normalizes malformed context", async ({
  page,
}) => {
  await mockDetails(page);
  await signIn(page);
  await openDetails(page);
  await expect(
    page.getByRole("link", { name: "Back to devices" }),
  ).toHaveAttribute("href", "/devices");
  await navigateInSession(
    page,
    `/devices/${device.id}?search=%20Freezer%20&status=unknown&offset=-1&extra=ignored`,
  );
  await expect(
    page.getByRole("link", { name: "Back to devices" }),
  ).toHaveAttribute("href", "/devices?search=Freezer");
});

test("updates the same page when navigating to another device and handles a missing description", async ({
  page,
}) => {
  const second = {
    ...devices[1],
    description: null,
    status: "active",
    device_type: "gps_tracker",
  };
  await mockDetails(page, [device, second]);
  await signIn(page);
  await openDetails(page);
  await openDetails(page, second);
  await expect(page.getByText("No description provided.")).toBeVisible();
  await expect(page.getByText("GPS tracker", { exact: true })).toBeVisible();
  await expect(page.getByText("Active", { exact: true })).toBeVisible();
  await expect(page.getByText(device.id, { exact: true })).toHaveCount(0);
  await page.goBack();
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(device.name);
});

test("shows a loading state until details arrive", async ({ page }) => {
  let release;
  const pending = new Promise((resolve) => {
    release = resolve;
  });
  await page.route("**/api/devices/*", async (route) => {
    await pending;
    await route.fulfill({ json: device });
  });
  try {
    await signIn(page);
    await navigateInSession(page, `/devices/${device.id}`);
    await expect(page.getByRole("status")).toHaveText("Loading device…");
    await expect(
      page.getByRole("region", { name: "Device information" }),
    ).toHaveAttribute("aria-busy", "true");
    await expect(
      page.getByRole("button", { name: "Copy device ID" }),
    ).toHaveCount(0);
    release();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      device.name,
    );
    await expect(page.getByRole("status")).toHaveText("Device details loaded.");
  } finally {
    release();
  }
});

for (const failure of ["server", "network", "malformed response"]) {
  test(`recovers from a ${failure} details failure`, async ({ page }) => {
    let attempts = 0;
    await page.route("**/api/devices/*", (route) => {
      attempts += 1;
      if (attempts === 1) {
        if (failure === "network") return route.abort("failed");
        return route.fulfill({
          status: failure === "server" ? 503 : 200,
          json: { detail: "private backend information" },
        });
      }
      return route.fulfill({ json: device });
    });
    await signIn(page);
    await navigateInSession(page, `/devices/${device.id}`);
    await expect(page.getByRole("alert")).toBeVisible();
    await expect(page.getByText("private backend information")).toHaveCount(0);
    await page.getByRole("button", { name: "Retry", exact: true }).click();
    await expect(page.getByRole("heading", { level: 1 })).toHaveText(
      device.name,
    );
    await expect(page.getByRole("alert")).toHaveCount(0);
    expect(attempts).toBe(2);
  });
}

for (const status of [403, 404]) {
  test(`shows a ${status} state without private details or Retry`, async ({
    page,
  }) => {
    await page.route("**/api/devices/*", (route) =>
      route.fulfill({
        status,
        json: { detail: "private backend information" },
      }),
    );
    await signIn(page);
    await navigateInSession(page, `/devices/${device.id}`);
    await expect(page.getByRole("alert")).toHaveText(
      status === 404
        ? "Device not found."
        : "Device access is unavailable for your account or company.",
    );
    await expect(page.getByRole("button", { name: "Retry" })).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Copy device ID" }),
    ).toHaveCount(0);
    await expect(page.getByText("private backend information")).toHaveCount(0);
    await expect(
      page.getByRole("link", { name: "Back to devices" }),
    ).toBeVisible();
  });
}

test("handles invalid device IDs without requesting device data", async ({
  page,
}) => {
  const requests = await mockDetails(page);
  await signIn(page);
  await navigateInSession(page, "/devices/not-a-uuid");
  await expect(page.getByRole("alert")).toHaveText("Device not found.");
  expect(requests).toEqual([]);
});

test("blocks unauthenticated visitors and system admins from details", async ({
  page,
}) => {
  const requests = await mockDetails(page);
  await page.goto(`/devices/${device.id}`);
  await expect(page).toHaveURL("/");
  await signIn(page, "system_admin");
  await navigateInSession(page, `/devices/${device.id}`);
  await expect(page).toHaveURL(/\/profile$/);
  expect(requests).toEqual([]);
});

test("expires the session when details return 401", async ({ page }) => {
  await page.route("**/api/devices/*", (route) =>
    route.fulfill({ status: 401, json: {} }),
  );
  await signIn(page);
  await navigateInSession(page, `/devices/${device.id}`);
  await expect(page).toHaveURL(/\/\?expired=1$/);
  await expect(page.getByRole("alert")).toContainText("session has expired");
  await expect(page.getByRole("button", { name: "Sign out" })).toHaveCount(0);
});

for (const outcome of ["success", "failure"]) {
  test(`reports clipboard ${outcome} and restores the copy action`, async ({
    page,
  }) => {
    await mockDetails(page);
    await signIn(page);
    await openDetails(page);
    await page.evaluate((result) => {
      window.copiedDeviceIds = [];
      Object.defineProperty(navigator, "clipboard", {
        configurable: true,
        value: {
          writeText: async (value) => {
            window.copiedDeviceIds.push(value);
            if (result === "failure") throw new Error("Clipboard unavailable");
          },
        },
      });
    }, outcome);
    const copy = page.getByRole("button", {
      name: "Copy device ID",
      exact: true,
    });
    await copy.focus();
    await copy.press("Enter");
    await expect(
      page.getByText(
        outcome === "success"
          ? "Device ID copied."
          : "Unable to copy the device ID. Select and copy it manually.",
        { exact: true },
      ),
    ).toBeVisible();
    expect(await page.evaluate(() => window.copiedDeviceIds)).toEqual([
      device.id,
    ]);
    await expect(copy).toBeEnabled();
    await expect(page.getByText(device.id, { exact: true })).toBeVisible();
  });
}

test("prevents duplicate copying and ignores copy completion after changing devices", async ({
  page,
}) => {
  await mockDetails(page);
  await signIn(page);
  await openDetails(page);
  await page.evaluate(() => {
    window.deviceCopyCalls = 0;
    Object.defineProperty(navigator, "clipboard", {
      configurable: true,
      value: {
        writeText: () => {
          window.deviceCopyCalls += 1;
          return new Promise((resolve) => {
            window.finishDeviceCopy = resolve;
          });
        },
      },
    });
  });
  await page
    .getByRole("button", { name: "Copy device ID", exact: true })
    .click();
  const pending = page.getByRole("button", {
    name: "Copying device ID",
    exact: true,
  });
  await expect(pending).toBeDisabled();
  await pending.evaluate((button) => button.click());
  expect(await page.evaluate(() => window.deviceCopyCalls)).toBe(1);

  await openDetails(page, devices[1]);
  await page.evaluate(async () => {
    window.finishDeviceCopy();
    await new Promise(requestAnimationFrame);
  });
  await expect(
    page.getByText("Device ID copied.", { exact: true }),
  ).toHaveCount(0);
  await expect(
    page.getByRole("button", { name: "Copy device ID", exact: true }),
  ).toBeEnabled();
});

test("time-zone hints support hover, keyboard focus, Escape and outside dismissal", async ({
  page,
}) => {
  await mockDetails(page);
  await signIn(page);
  await openDetails(page);
  const created = page.getByRole("button", {
    name: "Created time zone",
    exact: true,
  });
  const updated = page.getByRole("button", {
    name: "Last updated time zone",
    exact: true,
  });
  const tooltip = page.getByRole("tooltip");
  await created.hover();
  await expect(tooltip).toHaveText("Your local time zone: Europe/Belgrade.");
  await tooltip.hover();
  await expect(tooltip).toBeVisible();
  await page.getByRole("heading", { level: 1 }).hover();
  await expect(tooltip).toHaveCount(0);

  await created.focus();
  await expect(tooltip).toBeVisible();
  await expect(created).toHaveAttribute(
    "aria-describedby",
    await tooltip.getAttribute("id"),
  );
  await created.press("Escape");
  await expect(tooltip).toHaveCount(0);
  await expect(created).toBeFocused();
  await created.press("Tab");
  await expect(updated).toBeFocused();
  await expect(tooltip).toBeVisible();
  await page.getByRole("heading", { level: 1 }).click();
  await expect(tooltip).toHaveCount(0);
});

test.describe("touch interaction", () => {
  test.use({ hasTouch: true, viewport: { width: 390, height: 844 } });

  test("toggles the time-zone hint by tapping", async ({ page }) => {
    await mockDetails(page);
    await signIn(page);
    await openDetails(page);
    const info = page.getByRole("button", {
      name: "Created time zone",
      exact: true,
    });
    await info.tap();
    await expect(page.getByRole("tooltip")).toBeVisible();
    await info.tap();
    await expect(page.getByRole("tooltip")).toHaveCount(0);
  });
});

test("keeps long metadata and tooltips within desktop and mobile widths", async ({
  page,
}, testInfo) => {
  const longDevice = {
    ...device,
    name: "W".repeat(100),
    description: "D".repeat(1000),
  };
  await mockDetails(page, [longDevice]);
  await signIn(page);
  await openDetails(page, longDevice);

  for (const width of [1440, 768, 390, 320]) {
    await page.setViewportSize({ width, height: 800 });
    expect(
      await page.evaluate(
        () => document.documentElement.scrollWidth <= innerWidth,
      ),
    ).toBe(true);
    const id = page.getByText(device.id, { exact: true });
    await expect(id).toHaveText(device.id);
    const bounds = await id.boundingBox();
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(width);
    const info = page.getByRole("button", {
      name: "Created time zone",
      exact: true,
    });
    await info.scrollIntoViewIfNeeded();
    await info.click();
    const tooltip = page.getByRole("tooltip");
    await expect(tooltip).toBeVisible();
    const hint = await tooltip.boundingBox();
    expect(hint.x).toBeGreaterThanOrEqual(0);
    expect(hint.y).toBeGreaterThanOrEqual(0);
    expect(hint.x + hint.width).toBeLessThanOrEqual(width);
    expect(hint.y + hint.height).toBeLessThanOrEqual(800);
    await page.screenshot({
      path: testInfo.outputPath(`device-details-${width}.png`),
      fullPage: true,
    });
    await info.press("Escape");
  }
});
