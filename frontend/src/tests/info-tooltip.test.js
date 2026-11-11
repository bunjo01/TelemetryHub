import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { createApp, nextTick } from "vue";
import InfoTooltip from "../components/ui/InfoTooltip.vue";

let app;
let host;

beforeEach(() => {
  vi.stubGlobal("innerWidth", 320);
  vi.stubGlobal("innerHeight", 600);
});

afterEach(() => {
  app?.unmount();
  app = undefined;
  host?.remove();
  vi.unstubAllGlobals();
});

function mountTooltip({ top = 200, right = 280, height = 64 } = {}) {
  host = document.createElement("div");
  document.body.append(host);
  app = createApp(InfoTooltip, {
    label: "Created time zone",
    text: "Your local time zone: Europe/Belgrade.",
  });
  app.mount(host);

  const button = host.querySelector("button");
  const tooltip = host.querySelector('[role="tooltip"]');
  const root = button.parentElement;
  vi.spyOn(root, "getBoundingClientRect").mockReturnValue({
    top,
    bottom: top + 36,
    right,
    left: right - 36,
    width: 36,
    height: 36,
  });
  vi.spyOn(tooltip, "getBoundingClientRect").mockReturnValue({ height });

  return { button, tooltip, root };
}

async function settle() {
  await nextTick();
  await nextTick();
}

function pointer(target, type, pointerType = "mouse") {
  const event = new Event(type, { bubbles: true });
  Object.defineProperty(event, "pointerType", { value: pointerType });
  target.dispatchEvent(event);
}

it("opens on focus, describes the icon, and closes on blur", async () => {
  const { button, tooltip } = mountTooltip();

  expect(button.type).toBe("button");
  expect(button.getAttribute("aria-label")).toBe("Created time zone");
  expect(button.getAttribute("aria-describedby")).toBe(tooltip.id);
  button.focus();
  await settle();

  expect(tooltip.style.visibility).toBe("visible");
  expect(tooltip.textContent).toContain("Europe/Belgrade");

  button.blur();
  await settle();
  expect(tooltip.style.display).toBe("none");
});

it("stays open while the pointer moves from the icon to its tooltip", async () => {
  const { root, tooltip } = mountTooltip();
  pointer(root, "pointerenter");
  await settle();
  expect(tooltip.style.visibility).toBe("visible");

  pointer(tooltip, "pointerover");
  await settle();
  expect(tooltip.style.display).not.toBe("none");

  pointer(root, "pointerleave");
  await settle();
  expect(tooltip.style.display).toBe("none");
});

it("toggles with taps without relying on hover", async () => {
  const { root, button, tooltip } = mountTooltip();
  pointer(root, "pointerenter", "touch");
  await settle();
  expect(tooltip.style.display).toBe("none");

  button.focus();
  button.click();
  await settle();
  expect(tooltip.style.visibility).toBe("visible");

  button.click();
  await settle();
  expect(tooltip.style.display).toBe("none");
});

it("dismisses with Escape without moving focus or reopening immediately", async () => {
  const { button, tooltip } = mountTooltip();
  button.focus();
  await settle();
  button.dispatchEvent(
    new KeyboardEvent("keydown", { key: "Escape", bubbles: true }),
  );
  await settle();

  expect(tooltip.style.display).toBe("none");
  expect(document.activeElement).toBe(button);
});

it.each(["outside", "resize", "scroll"])("dismisses on %s", async (action) => {
  const { button, tooltip } = mountTooltip();
  button.click();
  await settle();

  if (action === "outside") pointer(document.body, "pointerdown");
  else window.dispatchEvent(new Event(action));
  await settle();

  expect(tooltip.style.display).toBe("none");
});

it.each([
  { top: 200, right: 280, expectedTop: 136, expectedLeft: 24 },
  { top: 4, right: 40, expectedTop: 40, expectedLeft: 16 },
  { top: 550, right: 320, expectedTop: 486, expectedLeft: 48 },
])("keeps the tooltip within the viewport at $top/$right", async (bounds) => {
  const { button, tooltip } = mountTooltip(bounds);
  button.focus();
  await settle();

  expect(tooltip.style.top).toBe(`${bounds.expectedTop}px`);
  expect(tooltip.style.left).toBe(`${bounds.expectedLeft}px`);
  expect(tooltip.style.width).toBe("256px");
  expect(tooltip.style.maxHeight).toBe("568px");
});

it("does not reopen after dismissal during position measurement", async () => {
  const { button, tooltip } = mountTooltip();
  button.focus();
  pointer(document.body, "pointerdown");
  await settle();

  expect(tooltip.style.display).toBe("none");
});

it("allows scrolling long tooltip content without dismissing it", async () => {
  const { button, tooltip } = mountTooltip();
  button.focus();
  await settle();
  tooltip.dispatchEvent(new Event("scroll"));
  await settle();

  expect(tooltip.style.display).not.toBe("none");
});

it("removes global listeners and cancels measurement on unmount", async () => {
  const documentRemove = vi.spyOn(document, "removeEventListener");
  const windowRemove = vi.spyOn(window, "removeEventListener");
  const { button } = mountTooltip();
  button.focus();
  app.unmount();
  app = undefined;
  await settle();

  expect(documentRemove).toHaveBeenCalledWith(
    "pointerdown",
    expect.any(Function),
  );
  expect(documentRemove).toHaveBeenCalledWith("keydown", expect.any(Function));
  expect(windowRemove).toHaveBeenCalledWith("resize", expect.any(Function));
  expect(windowRemove).toHaveBeenCalledWith(
    "scroll",
    expect.any(Function),
    true,
  );
});
