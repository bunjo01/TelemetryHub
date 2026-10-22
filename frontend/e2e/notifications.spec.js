import { expect, test } from "@playwright/test";

test("login errors do not resize the form or page and support manual dismissal", async ({
  page,
}, testInfo) => {
  const errors = [];
  page.on("pageerror", (error) => errors.push(error.message));
  await page.route("**/api/auth/login", (route) =>
    route.fulfill({ status: 401, json: {} }),
  );
  for (const width of [1280, 390, 320]) {
    await page.setViewportSize({ width, height: 800 });
    await page.goto("/");
    await page.getByLabel("Email address").fill("crew@example.com");
    await page.getByLabel("Password", { exact: true }).fill("wrong password");
    const panel = page.getByRole("region", { name: "Sign in to your space." });
    const before = await panel.boundingBox();
    const height = await page.evaluate(
      () => document.documentElement.scrollHeight,
    );
    const submit = page.getByRole("button", { name: "Sign in", exact: true });
    await submit.click();
    const host = page.getByRole("region", {
      name: "Notifications",
      exact: true,
    });
    await expect(host.getByRole("alert")).toBeVisible();
    expect(await panel.boundingBox()).toEqual(before);
    expect(
      await page.evaluate(() => document.documentElement.scrollHeight),
    ).toBe(height);
    await expect(host.getByRole("alert")).toBeInViewport();
    const toast = host.getByRole("region", { name: "Error", exact: true });
    const track = toast.locator(".toast__progress");
    const toastBounds = await toast.boundingBox();
    const trackBounds = await track.boundingBox();
    expect(trackBounds.x).toBeCloseTo(toastBounds.x, 1);
    expect(trackBounds.width).toBeCloseTo(toastBounds.width, 1);
    expect(trackBounds.y + trackBounds.height).toBeCloseTo(
      toastBounds.y + toastBounds.height,
      1,
    );
    await expect(track).toHaveCSS("overflow", "hidden");
    const radius = await toast.evaluate(
      (element) => getComputedStyle(element).borderBottomLeftRadius,
    );
    await expect(track).toHaveCSS("border-bottom-left-radius", radius);
    await expect(page.getByLabel("Email address")).not.toHaveAttribute(
      "aria-invalid",
      "true",
    );
    await page.screenshot({
      path: testInfo.outputPath(`login-toast-${width}.png`),
      fullPage: true,
    });
    const dismiss = host.getByRole("button", {
      name: "Dismiss error notification",
    });
    await dismiss.focus();
    await page.keyboard.press("Enter");
    await expect(host.getByRole("alert")).toHaveCount(0);
    await expect(submit).toBeFocused();
  }
  expect(errors).toEqual([]);
});

test("success toast pauses on hover and focus, then expires without replaying", async ({
  page,
}) => {
  await page.clock.install();
  await page.goto("/?registered=1");
  const toast = page.getByRole("region", { name: "Success", exact: true });
  await expect(toast).toBeVisible();
  await toast.hover();
  await page.clock.fastForward(10000);
  await expect(toast).toBeVisible();
  const dismiss = toast.getByRole("button");
  await dismiss.focus();
  await page.mouse.move(0, 0);
  await page.clock.fastForward(10000);
  await expect(toast).toBeVisible();
  await page.getByLabel("Email address").focus();
  await page.clock.fastForward(8000);
  await expect(toast).toHaveCount(0);
  await page.getByLabel("Email address").fill("crew@example.com");
  await expect(page.getByRole("status")).toHaveCount(0);
});

test("browser field validation does not create a toast", async ({ page }) => {
  await page.goto("/");
  await page.getByLabel("Email address").fill("invalid");
  await page.getByRole("button", { name: "Sign in", exact: true }).click();
  await expect(page.getByLabel("Email address")).toBeFocused();
  await expect(page.getByRole("alert")).toHaveCount(0);
  expect(
    await page
      .getByLabel("Email address")
      .evaluate((input) => input.validity.valid),
  ).toBe(false);
});

for (const reducedMotion of ["no-preference", "reduce"]) {
  test(`error countdown pauses and expires with ${reducedMotion} motion`, async ({
    page,
  }) => {
    await page.emulateMedia({ reducedMotion });
    await page.clock.install();
    await page.goto("/?expired=1");
    const toast = page.getByRole("region", { name: "Error", exact: true });
    await expect(toast).toBeVisible();
    const bar = toast.locator(".toast__progress-bar");
    const track = toast.locator(".toast__progress");
    const fraction = async () => {
      const fill = await bar.boundingBox();
      const full = await track.boundingBox();
      return fill.width / full.width;
    };
    await page.clock.runFor(4000);
    expect(await fraction()).toBeCloseTo(0.5, 1);
    await toast.hover();
    const pausedFraction = await fraction();
    await page.clock.runFor(10000);
    expect(await fraction()).toBeCloseTo(pausedFraction, 3);
    await page.mouse.move(0, 0);
    await page.clock.runFor(4000);
    await expect(toast).toHaveCount(0);
  });
}
