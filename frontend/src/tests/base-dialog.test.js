import { createPinia } from "pinia";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { createApp, h, nextTick, ref } from "vue";
import BaseDialog from "../components/ui/BaseDialog.vue";
import { useNotificationStore } from "../stores/notifications.js";

const dialogPrototype = HTMLDialogElement.prototype;
const originalMethods = Object.fromEntries(
  ["showModal", "close"].map((method) => [
    method,
    Object.getOwnPropertyDescriptor(dialogPrototype, method),
  ]),
);

let app;
let container;
let showModal;
let closeDialog;

beforeEach(() => {
  showModal = vi.fn(function () {
    this.setAttribute("open", "");
  });
  closeDialog = vi.fn(function () {
    this.removeAttribute("open");
    this.dispatchEvent(new Event("close"));
  });
  Object.defineProperty(dialogPrototype, "showModal", {
    configurable: true,
    value: showModal,
  });
  Object.defineProperty(dialogPrototype, "close", {
    configurable: true,
    value: closeDialog,
  });
});

afterEach(async () => {
  app?.unmount();
  app = undefined;
  await settle();
  container?.remove();

  for (const [method, descriptor] of Object.entries(originalMethods)) {
    if (descriptor) Object.defineProperty(dialogPrototype, method, descriptor);
    else delete dialogPrototype[method];
  }
});

async function settle() {
  await nextTick();
  await nextTick();
}

function mountDialog({ closeDisabled = false, focusInput = false } = {}) {
  container = document.createElement("main");
  const pageHeading = document.createElement("h1");
  pageHeading.tabIndex = -1;
  pageHeading.textContent = "Devices";
  const opener = document.createElement("button");
  opener.textContent = "Add device";
  const host = document.createElement("div");
  container.append(pageHeading, opener, host);
  document.body.append(container);
  opener.focus();

  const pinia = createPinia();
  const notifications = useNotificationStore(pinia);
  const isOpen = ref(true);
  const isSaving = ref(closeDisabled);
  const input = ref(null);
  const onClose = vi.fn(() => {
    isOpen.value = false;
  });
  app = createApp({
    setup() {
      return () =>
        isOpen.value
          ? h(
              BaseDialog,
              {
                title: "Add device",
                closeDisabled: isSaving.value,
                initialFocus: focusInput ? () => input.value.focus() : null,
                onClose,
              },
              {
                default: ({ close }) => [
                  h("input", { ref: input, "aria-label": "Device name" }),
                  h("button", { type: "button", onClick: close }, "Cancel"),
                ],
              },
            )
          : null;
    },
  });
  app.use(pinia);
  app.mount(host);

  const dialog = host.querySelector("dialog");
  const close = dialog.querySelector('[aria-label="Close Add device"]');
  const cancel = [...dialog.querySelectorAll("button")].find(
    (button) => button.textContent === "Cancel",
  );

  return {
    dialog,
    close,
    cancel,
    opener,
    pageHeading,
    notifications,
    isOpen,
    isSaving,
    onClose,
    input,
  };
}

it("opens a labelled modal, focuses its title and registers notifications inside it", () => {
  const { dialog, notifications } = mountDialog();
  const heading = dialog.querySelector("h2");

  expect(showModal).toHaveBeenCalledTimes(1);
  expect(dialog.open).toBe(true);
  expect(dialog.getAttribute("aria-labelledby")).toBe(heading.id);
  expect(heading.textContent).toBe("Add device");
  expect(document.activeElement).toBe(heading);
  expect(notifications.target).toBe(dialog);
});

it("allows the caller to focus its own field", () => {
  const { input } = mountDialog({ focusInput: true });
  expect(document.activeElement).toBe(input.value);
});

it.each(["close button", "cancel action", "Escape"])(
  "closes through the %s, cleans up notifications and restores focus",
  async (action) => {
    const { dialog, close, cancel, opener, notifications, onClose } =
      mountDialog();
    if (action === "close button") close.click();
    else if (action === "cancel action") cancel.click();
    else {
      const event = new Event("cancel", { cancelable: true });
      dialog.dispatchEvent(event);
      expect(event.defaultPrevented).toBe(true);
    }
    await settle();

    expect(onClose).toHaveBeenCalledTimes(1);
    expect(dialog.isConnected).toBe(false);
    expect(closeDialog).toHaveBeenCalledTimes(1);
    expect(notifications.target).toBe("body");
    expect(document.activeElement).toBe(opener);
  },
);

it("blocks every requested close while saving and allows closing afterward", async () => {
  const { dialog, close, cancel, isSaving, onClose } = mountDialog({
    closeDisabled: true,
  });
  expect(close.disabled).toBe(true);
  close.click();
  cancel.click();
  const event = new Event("cancel", { cancelable: true });
  dialog.dispatchEvent(event);
  await settle();

  expect(event.defaultPrevented).toBe(true);
  expect(onClose).not.toHaveBeenCalled();
  expect(dialog.open).toBe(true);

  isSaving.value = false;
  await settle();
  expect(close.disabled).toBe(false);
  cancel.click();
  await settle();
  expect(onClose).toHaveBeenCalledTimes(1);
  expect(dialog.isConnected).toBe(false);
});

it("does not dismiss on clicks on the dialog surface", async () => {
  const { dialog, onClose } = mountDialog();
  dialog.click();
  await settle();
  expect(onClose).not.toHaveBeenCalled();
  expect(dialog.open).toBe(true);
});

it("notifies the parent when the native dialog closes", async () => {
  const { dialog, onClose } = mountDialog();
  dialog.close();
  await settle();
  expect(onClose).toHaveBeenCalledTimes(1);
  expect(dialog.isConnected).toBe(false);
});

it.each(["removed", "disabled", "inert"])(
  "focuses the page heading when the opener is %s",
  async (state) => {
    const { opener, pageHeading, cancel } = mountDialog();
    if (state === "removed") opener.remove();
    else if (state === "disabled") opener.disabled = true;
    else opener.setAttribute("inert", "");

    cancel.click();
    await settle();
    expect(document.activeElement).toBe(pageHeading);
  },
);

it("preserves focus deliberately moved elsewhere while closing", async () => {
  const { pageHeading, isOpen } = mountDialog();
  isOpen.value = false;
  pageHeading.focus();
  await settle();
  expect(document.activeElement).toBe(pageHeading);
});

it("cleans up when the parent removes the dialog without a close request", async () => {
  const { isOpen, notifications, onClose } = mountDialog();
  isOpen.value = false;
  await settle();

  expect(closeDialog).toHaveBeenCalledTimes(1);
  expect(notifications.target).toBe("body");
  expect(onClose).not.toHaveBeenCalled();
});
