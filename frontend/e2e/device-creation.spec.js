import { expect, test } from "@playwright/test";

const companyId = "11111111-1111-4111-8111-111111111111";
const createdDevice = {
  id: "44444444-4444-4444-8444-444444444444",
  company_id: companyId,
  name: "Freezer sensor",
  description: "Warehouse\nCold storage",
  device_type: "temperature_sensor",
  status: "active",
  created_at: "2026-11-12T12:00:00Z",
  updated_at: "2026-11-12T12:00:00Z",
};

async function signIn(page, role = "company_owner") {
  await page.route("**/api/auth/login", (route) =>
    route.fulfill({
      json: { access_token: "test-token", token_type: "bearer" },
    }),
  );
  await page.route("**/api/auth/me", (route) =>
    route.fulfill({
      json: { email: "crew@example.com", role, company_id: companyId },
    }),
  );
  await page.route("**/api/devices?*", (route) => {
    const params = new URL(route.request().url()).searchParams;
    const offset = Number(params.get("offset"));
    const status = params.get("status");
    return route.fulfill({
      json: {
        items: [
          {
            ...createdDevice,
            name: "Warehouse sensor",
            status: status === "all" ? "active" : status,
          },
        ],
        offset,
        limit: 20,
        has_more: false,
      },
    });
  });
  await page.goto("/");
  await page.getByLabel("Email address").fill("crew@example.com");
  await page.getByLabel("Password", { exact: true }).fill("test-password");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page).toHaveURL(/\/profile$/);
  await page.getByRole("link", { name: "Devices", exact: true }).click();
  await expect(
    page.getByRole("link", { name: "Warehouse sensor", exact: true }),
  ).toBeVisible();
}

async function openForm(page) {
  await page.getByRole("button", { name: "Add device", exact: true }).click();
  const dialog = page.getByRole("dialog", { name: "Add device", exact: true });
  await expect(dialog).toBeVisible();
  await expect(dialog.getByLabel("Device name", { exact: true })).toBeFocused();
  return dialog;
}

async function fillForm(dialog) {
  await dialog
    .getByLabel("Device name", { exact: true })
    .fill("  Freezer sensor  ");
  await dialog
    .getByRole("combobox", { name: "Device type", exact: true })
    .click();
  await dialog
    .getByRole("option", { name: "Temperature sensor", exact: true })
    .click();
  await dialog
    .getByLabel("Description (optional)", { exact: true })
    .fill(createdDevice.description);
}

test("members cannot open device creation", async ({ page }) => {
  await signIn(page, "member");
  await expect(
    page.getByRole("button", { name: "Add device", exact: true }),
  ).toHaveCount(0);
  await expect(page.getByRole("dialog")).toHaveCount(0);
});

for (const action of ["Cancel", "Close Add device", "Escape"]) {
  test(`cancelling with ${action} restores focus and discards the draft`, async ({
    page,
  }) => {
    let writes = 0;
    await page.route("**/api/devices", (route) => {
      writes += 1;
      return route.fulfill({ json: createdDevice });
    });
    await signIn(page);
    const dialog = await openForm(page);
    await dialog
      .getByLabel("Device name", { exact: true })
      .fill("Unsaved device");
    if (action === "Escape") await page.keyboard.press("Escape");
    else
      await dialog.getByRole("button", { name: action, exact: true }).click();
    await expect(dialog).toHaveCount(0);
    await expect(
      page.getByRole("button", { name: "Add device", exact: true }),
    ).toBeFocused();
    await openForm(page);
    await expect(dialog.getByLabel("Device name", { exact: true })).toHaveValue(
      "",
    );
    expect(writes).toBe(0);
  });
}

test("excludes background controls from keyboard navigation and closes the type popup before the dialog", async ({
  page,
}) => {
  await signIn(page);
  const dialog = await openForm(page);
  const name = dialog.getByLabel("Device name", { exact: true });
  await name.press("Shift+Tab");
  await expect(
    dialog.getByRole("button", { name: "Close Add device", exact: true }),
  ).toBeFocused();
  for (const [key, destination] of [
    ["Shift+Tab", "Add device"],
    ["Tab", "Close Add device"],
  ]) {
    const target = dialog.getByRole("button", {
      name: destination,
      exact: true,
    });
    for (let step = 0; step < 4; step += 1) {
      await page.keyboard.press(key);
      await expect(dialog).toBeVisible();
      expect(
        await dialog.evaluate(
          (element) =>
            document.activeElement === document.body ||
            element.contains(document.activeElement),
        ),
      ).toBe(true);
      if (
        await target.evaluate((element) => element === document.activeElement)
      )
        break;
    }
    await expect(target).toBeFocused();
  }
  const type = dialog.getByRole("combobox", {
    name: "Device type",
    exact: true,
  });
  await type.focus();
  await type.press("ArrowDown");
  await expect(dialog.getByRole("listbox")).toBeVisible();
  await type.press("Escape");
  await expect(dialog.getByRole("listbox")).toHaveCount(0);
  await expect(dialog).toBeVisible();
  await expect(type).toBeFocused();
  await page.mouse.click(1, 1);
  await expect(dialog).toBeVisible();
});

test("validates required fields and focuses the first invalid control", async ({
  page,
}) => {
  await signIn(page);
  const dialog = await openForm(page);
  const submit = dialog.getByRole("button", {
    name: "Add device",
    exact: true,
  });
  const name = dialog.getByLabel("Device name", { exact: true });
  await name.fill("   ");
  await submit.click();
  await expect(name).toBeFocused();
  await expect(name).toHaveAttribute("aria-invalid", "true");
  await expect(
    dialog.getByText("Enter a device name.", { exact: true }),
  ).toBeVisible();
  await name.fill("Freezer sensor");
  await submit.click();
  const type = dialog.getByRole("combobox", {
    name: "Device type",
    exact: true,
  });
  await expect(type).toBeFocused();
  await expect(type).toHaveAttribute("aria-invalid", "true");
  await expect(
    dialog.getByText("Choose a device type.", { exact: true }),
  ).toBeVisible();
});

test("creates a device, navigates to its details and preserves the list return context", async ({
  page,
}) => {
  const writes = [];
  await page.route("**/api/devices", (route) => {
    expect(route.request().method()).toBe("POST");
    expect(route.request().headers().authorization).toBe("Bearer test-token");
    writes.push(route.request().postDataJSON());
    return route.fulfill({ status: 201, json: createdDevice });
  });
  await page.route(`**/api/devices/${createdDevice.id}`, (route) =>
    route.fulfill({ json: createdDevice }),
  );
  await signIn(page);
  await page.evaluate(() => {
    history.pushState(
      {},
      "",
      "/devices?search=Warehouse&status=inactive&offset=20",
    );
    window.dispatchEvent(new PopStateEvent("popstate"));
  });
  const dialog = await openForm(page);
  await fillForm(dialog);
  await dialog.getByRole("button", { name: "Add device", exact: true }).click();
  await expect(page).toHaveURL(
    `/devices/${createdDevice.id}?search=Warehouse&status=inactive&offset=20`,
  );
  await expect(dialog).toHaveCount(0);
  await expect(page.getByRole("heading", { level: 1 })).toHaveText(
    createdDevice.name,
  );
  await expect(page.getByRole("heading", { level: 1 })).toBeFocused();
  await expect(
    page.getByText("Freezer sensor was created successfully.", { exact: true }),
  ).toBeVisible();
  await expect(
    page.getByRole("link", { name: "Back to devices" }),
  ).toHaveAttribute(
    "href",
    "/devices?search=Warehouse&status=inactive&offset=20",
  );
  expect(writes).toEqual([
    {
      name: "Freezer sensor",
      device_type: "temperature_sensor",
      description: createdDevice.description,
    },
  ]);
});

test("keeps the draft and shows an uncertain-outcome message after a server failure", async ({
  page,
}) => {
  let writes = 0;
  await page.route("**/api/devices", (route) => {
    writes += 1;
    return route.fulfill({ status: 503, json: {} });
  });
  await signIn(page);
  const dialog = await openForm(page);
  await fillForm(dialog);
  await dialog.getByRole("button", { name: "Add device", exact: true }).click();
  await expect(dialog.getByRole("alert")).toContainText(
    "Check the device list before trying again.",
  );
  await expect(dialog.getByLabel("Device name", { exact: true })).toHaveValue(
    "  Freezer sensor  ",
  );
  await expect(
    dialog.getByLabel("Description (optional)", { exact: true }),
  ).toHaveValue(createdDevice.description);
  await expect(
    dialog.getByRole("combobox", { name: "Device type", exact: true }),
  ).toHaveText("Temperature sensor");
  await expect(
    dialog.getByRole("button", { name: "Add device", exact: true }),
  ).toBeEnabled();
  expect(writes).toBe(1);
});

test("blocks closing and repeated submission while creation is pending", async ({
  page,
}) => {
  let release;
  const pending = new Promise((resolve) => {
    release = resolve;
  });
  let writes = 0;
  await page.route("**/api/devices", async (route) => {
    writes += 1;
    await pending;
    await route.fulfill({ status: 503, json: {} });
  });
  try {
    await signIn(page);
    const dialog = await openForm(page);
    await fillForm(dialog);
    await dialog
      .getByRole("button", { name: "Add device", exact: true })
      .click();
    await expect.poll(() => writes).toBe(1);
    await expect(
      dialog.getByRole("button", { name: "Adding…", exact: true }),
    ).toBeDisabled();
    await expect(
      dialog.getByRole("button", { name: "Cancel", exact: true }),
    ).toBeDisabled();
    await expect(
      dialog.getByRole("button", { name: "Close Add device", exact: true }),
    ).toBeDisabled();
    await page.keyboard.press("Escape");
    await expect(dialog).toBeVisible();
    await dialog.getByLabel("Device name", { exact: true }).press("Enter");
    expect(writes).toBe(1);
    release();
    await expect(dialog.getByRole("alert")).toBeVisible();
    await dialog.getByRole("button", { name: "Cancel", exact: true }).click();
    await expect(dialog).toHaveCount(0);
  } finally {
    release();
  }
});

test("fits mobile and short viewports with reachable form actions", async ({
  page,
}, testInfo) => {
  await signIn(page);
  for (const viewport of [
    { width: 1440, height: 900 },
    { width: 390, height: 600 },
    { width: 320, height: 480 },
  ]) {
    await page.setViewportSize(viewport);
    const dialog = await openForm(page);
    const bounds = await dialog.boundingBox();
    expect(bounds.x).toBeGreaterThanOrEqual(0);
    expect(bounds.y).toBeGreaterThanOrEqual(0);
    expect(bounds.x + bounds.width).toBeLessThanOrEqual(viewport.width);
    expect(bounds.y + bounds.height).toBeLessThanOrEqual(viewport.height);
    expect(
      await dialog.evaluate(
        (element) => element.scrollWidth <= element.clientWidth,
      ),
    ).toBe(true);
    const cancel = dialog.getByRole("button", { name: "Cancel", exact: true });
    await cancel.scrollIntoViewIfNeeded();
    await expect(cancel).toBeInViewport();
    await page.screenshot({
      path: testInfo.outputPath(`device-create-${viewport.width}.png`),
      fullPage: true,
    });
    await cancel.click();
  }
});
