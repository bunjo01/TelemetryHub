import { createPinia } from "pinia";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { createApp, h, nextTick } from "vue";
import { ApiError } from "../api/client.js";
import { createDevice } from "../api/devices.api.js";
import DeviceFormDialog from "../features/devices/components/DeviceFormDialog.vue";
import { useAuthStore } from "../stores/auth.js";

const { replace } = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("vue-router", () => ({ useRouter: () => ({ replace }) }));
vi.mock("../api/devices.api.js", () => ({ createDevice: vi.fn() }));

const createdDevice = {
  id: "11111111-1111-4111-8111-111111111111",
  name: "Freezer sensor",
};
const dialogPrototype = HTMLDialogElement.prototype;
const originalMethods = Object.fromEntries(
  ["showModal", "close"].map((method) => [
    method,
    Object.getOwnPropertyDescriptor(dialogPrototype, method),
  ]),
);
let app;
let host;

beforeEach(() => {
  vi.resetAllMocks();
  createDevice.mockResolvedValue(createdDevice);
  replace.mockResolvedValue(undefined);
  Object.defineProperty(dialogPrototype, "showModal", {
    configurable: true,
    value() {
      this.setAttribute("open", "");
    },
  });
  Object.defineProperty(dialogPrototype, "close", {
    configurable: true,
    value() {
      this.removeAttribute("open");
    },
  });
});

afterEach(async () => {
  app?.unmount();
  app = undefined;
  await settle();
  host?.remove();
  for (const [method, descriptor] of Object.entries(originalMethods)) {
    if (descriptor) Object.defineProperty(dialogPrototype, method, descriptor);
    else delete dialogPrototype[method];
  }
});

async function settle() {
  await nextTick();
  await nextTick();
  await nextTick();
}

function mountForm() {
  const pinia = createPinia();
  const auth = useAuthStore(pinia);
  auth.token = "test-token";
  auth.user = { role: "company_owner" };
  const onCreated = vi.fn();
  const onClose = vi.fn();
  host = document.createElement("div");
  document.body.append(host);
  app = createApp({
    render: () => h(DeviceFormDialog, { onCreated, onClose }),
  });
  app.use(pinia);
  app.mount(host);
  return {
    auth,
    onCreated,
    onClose,
    form: host.querySelector("form"),
    dialog: host.querySelector("dialog"),
    name: host.querySelector('input[name="name"]'),
    type: host.querySelector('[role="combobox"]'),
    description: host.querySelector('textarea[name="description"]'),
  };
}

async function fill(input, value) {
  input.value = value;
  input.dispatchEvent(new Event("input", { bubbles: true }));
  await nextTick();
}

async function chooseType(control, label = "Temperature sensor") {
  control.click();
  await nextTick();
  const option = [...host.querySelectorAll('[role="option"]')].find(
    (item) => item.textContent.trim() === label,
  );
  expect(option).toBeDefined();
  option.click();
  await nextTick();
}

async function submit(form) {
  form.dispatchEvent(new Event("submit", { bubbles: true, cancelable: true }));
  await settle();
}

function errorText(control) {
  return (control.getAttribute("aria-describedby") ?? "")
    .split(" ")
    .map((id) => document.getElementById(id)?.textContent.trim())
    .join(" ");
}

it("focuses the name and offers the three supported device types", async () => {
  const { name, type } = mountForm();
  expect(document.activeElement).toBe(name);
  expect(type.textContent).toContain("Choose a device type");
  expect(errorText(type)).toContain(
    "Device type cannot be changed after creation.",
  );
  type.click();
  await nextTick();
  expect(
    [...host.querySelectorAll('[role="option"]')].map((option) =>
      option.textContent.trim(),
    ),
  ).toEqual(["Temperature sensor", "Environment sensor", "GPS tracker"]);
});

it.each(["", "   ", "N".repeat(101)])(
  "rejects an invalid name (%s) and focuses its error",
  async (value) => {
    const { name, form } = mountForm();
    await fill(name, value);
    await submit(form);
    expect(createDevice).not.toHaveBeenCalled();
    expect(document.activeElement).toBe(name);
    expect(name.getAttribute("aria-invalid")).toBe("true");
    expect(errorText(name)).toContain(
      value.trim() ? "Use 100 characters or fewer." : "Enter a device name.",
    );
    await fill(name, "Freezer sensor");
    expect(name.hasAttribute("aria-invalid")).toBe(false);
  },
);

it("focuses the enabled type selector when its required choice is missing", async () => {
  const { name, type, form } = mountForm();
  await fill(name, "Freezer sensor");
  await submit(form);
  expect(createDevice).not.toHaveBeenCalled();
  expect(type.disabled).toBe(false);
  expect(document.activeElement).toBe(type);
  expect(type.getAttribute("aria-invalid")).toBe("true");
  expect(errorText(type)).toContain("Choose a device type.");
  await chooseType(type);
  expect(type.hasAttribute("aria-invalid")).toBe(false);
  expect(errorText(type)).toBe("Device type cannot be changed after creation.");
});

it("rejects descriptions over the limit and focuses the textarea", async () => {
  const { name, type, description, form } = mountForm();
  await fill(name, "Freezer sensor");
  await chooseType(type);
  await fill(description, "D".repeat(1001));
  await submit(form);
  expect(createDevice).not.toHaveBeenCalled();
  expect(document.activeElement).toBe(description);
  expect(errorText(description)).toContain("Use 1,000 characters or fewer.");
});

it("trims the name, sends an empty description as null and emits the returned device", async () => {
  const { name, type, form, onCreated } = mountForm();
  await fill(name, "  Freezer sensor  ");
  await chooseType(type, "GPS tracker");
  await submit(form);
  expect(createDevice).toHaveBeenCalledWith(
    {
      name: "Freezer sensor",
      deviceType: "gps_tracker",
      description: null,
    },
    "test-token",
    expect.any(AbortSignal),
  );
  expect(onCreated).toHaveBeenCalledExactlyOnceWith(createdDevice);
});

it("accepts boundary lengths and preserves description whitespace and newlines", async () => {
  const { name, type, description, form } = mountForm();
  const text = `  First line\n${"D".repeat(985)}  `;
  expect(text.length).toBe(1000);
  await fill(name, "N".repeat(100));
  await chooseType(type, "Environment sensor");
  await fill(description, text);
  await submit(form);
  expect(createDevice).toHaveBeenCalledWith(
    {
      name: "N".repeat(100),
      deviceType: "environment_sensor",
      description: text,
    },
    "test-token",
    expect.any(AbortSignal),
  );
});

it("blocks duplicate submissions and closing while the request is pending", async () => {
  let resolve;
  createDevice.mockReturnValue(
    new Promise((done) => {
      resolve = done;
    }),
  );
  const { name, type, description, form, dialog, onClose, onCreated } =
    mountForm();
  await fill(name, "Freezer sensor");
  await chooseType(type);
  form.dispatchEvent(new Event("submit", { cancelable: true }));
  form.dispatchEvent(new Event("submit", { cancelable: true }));
  await settle();
  await submit(form);
  expect(createDevice).toHaveBeenCalledTimes(1);
  expect(form.getAttribute("aria-busy")).toBe("true");
  expect(name.readOnly).toBe(true);
  expect(description.readOnly).toBe(true);
  expect(type.disabled).toBe(true);
  for (const button of host.querySelectorAll('button:not([role="combobox"])')) {
    expect(button.disabled).toBe(true);
    button.click();
  }
  dialog.dispatchEvent(new Event("cancel", { cancelable: true }));
  expect(onClose).not.toHaveBeenCalled();
  resolve(createdDevice);
  await settle();
  expect(onCreated).toHaveBeenCalledTimes(1);
});

it.each([403, 422, 0, 503])(
  "preserves input on status %s failure without retrying automatically",
  async (status) => {
    createDevice.mockRejectedValue(
      new ApiError("Request was rejected.", status),
    );
    const { name, type, description, form, onCreated } = mountForm();
    await fill(name, "Freezer sensor");
    await chooseType(type);
    await fill(description, "Warehouse\nFreezer");
    await submit(form);
    expect(name.value).toBe("Freezer sensor");
    expect(type.textContent).toContain("Temperature sensor");
    expect(description.value).toBe("Warehouse\nFreezer");
    expect(form.getAttribute("aria-busy")).toBe("false");
    expect(host.querySelector('[role="alert"]').textContent).toContain(
      status === 0 || status >= 500
        ? "Check the device list before trying again."
        : "Request was rejected.",
    );
    expect(onCreated).not.toHaveBeenCalled();
    expect(createDevice).toHaveBeenCalledTimes(1);
  },
);

it("clears the session and redirects after an unauthorized response", async () => {
  createDevice.mockRejectedValue(new ApiError("Session expired", 401));
  const { auth, name, type, form, onCreated } = mountForm();
  await fill(name, "Freezer sensor");
  await chooseType(type);
  await submit(form);
  expect(auth.token).toBe("");
  expect(auth.user).toBeNull();
  expect(replace).toHaveBeenCalledWith({
    name: "login",
    query: { expired: "1" },
  });
  expect(onCreated).not.toHaveBeenCalled();
});

it.each(["success", "failure"])(
  "aborts on unmount and ignores late %s",
  async (outcome) => {
    let resolve;
    let reject;
    createDevice.mockReturnValue(
      new Promise((done, fail) => {
        resolve = done;
        reject = fail;
      }),
    );
    const { auth, name, type, form, onCreated } = mountForm();
    await fill(name, "Freezer sensor");
    await chooseType(type);
    await submit(form);
    const signal = createDevice.mock.calls[0][2];
    app.unmount();
    app = undefined;
    expect(signal.aborted).toBe(true);
    if (outcome === "success") resolve(createdDevice);
    else reject(new ApiError("Session expired", 401));
    await settle();
    expect(onCreated).not.toHaveBeenCalled();
    expect(replace).not.toHaveBeenCalled();
    expect(auth.token).toBe("test-token");
  },
);
