import { afterEach, expect, it, vi } from "vitest";
import { createApp, h, nextTick, ref } from "vue";
import BaseSelect from "../components/ui/BaseSelect.vue";

let app;
let host;

afterEach(() => {
  app?.unmount();
  host?.remove();
});

function mountSelect(attributes = {}) {
  const attrs = ref(attributes);
  const value = ref("active");
  const component = ref(null);
  host = document.createElement("div");
  document.body.append(host);
  app = createApp({
    setup() {
      return () =>
        h(BaseSelect, {
          ...attrs.value,
          ref: component,
          id: "status",
          label: "Status",
          options: [
            { value: "active", label: "Active" },
            { value: "inactive", label: "Inactive" },
          ],
          modelValue: value.value,
          "onUpdate:modelValue": (updated) => {
            value.value = updated;
          },
        });
    },
  });
  app.mount(host);
  const trigger = host.querySelector('[role="combobox"]');
  return { attrs, value, component, trigger, root: trigger.parentElement };
}

it("places accessibility attributes on the interactive control", () => {
  const { trigger, root } = mountSelect({
    "aria-describedby": "status-hint status-error",
    "aria-invalid": "true",
    "aria-required": "true",
  });

  for (const [attribute, value] of Object.entries({
    "aria-describedby": "status-hint status-error",
    "aria-invalid": "true",
    "aria-required": "true",
  })) {
    expect(trigger.getAttribute(attribute)).toBe(value);
    expect(root.hasAttribute(attribute)).toBe(false);
  }
  expect(trigger.id).toBe("status");
  expect(trigger.getAttribute("aria-label")).toBe("Status");
});

it("updates and removes forwarded attributes as validation changes", async () => {
  const { attrs, trigger } = mountSelect({
    "aria-invalid": "true",
    "aria-describedby": "status-hint status-error",
  });
  attrs.value = { "aria-describedby": "status-hint" };
  await nextTick();

  expect(trigger.hasAttribute("aria-invalid")).toBe(false);
  expect(trigger.getAttribute("aria-describedby")).toBe("status-hint");
  attrs.value = {};
  await nextTick();
  expect(trigger.hasAttribute("aria-describedby")).toBe(false);
});

it("keeps contextual layout classes and styles on the wrapper", async () => {
  const { attrs, trigger, root } = mountSelect({
    class: "device-form__type",
    style: { marginTop: "12px" },
  });
  expect(root.classList.contains("device-form__type")).toBe(true);
  expect(root.style.marginTop).toBe("12px");
  expect(trigger.classList.contains("device-form__type")).toBe(false);
  expect(trigger.style.marginTop).toBe("");

  attrs.value = {};
  await nextTick();
  expect(root.classList.contains("device-form__type")).toBe(false);
  expect(root.style.marginTop).toBe("");
});

it("forwards focus and blur events while retaining dropdown close behavior", async () => {
  const onFocus = vi.fn();
  const onBlur = vi.fn();
  const { component, trigger } = mountSelect({ onFocus, onBlur });
  component.value.focus({ preventScroll: true });
  expect(document.activeElement).toBe(trigger);
  expect(onFocus).toHaveBeenCalledTimes(1);

  trigger.click();
  await nextTick();
  expect(trigger.getAttribute("aria-expanded")).toBe("true");
  trigger.blur();
  await nextTick();

  expect(onBlur).toHaveBeenCalledTimes(1);
  expect(trigger.getAttribute("aria-expanded")).toBe("false");
  expect(host.querySelector('[role="listbox"]')).toBeNull();
});

it("forwards key events without replacing keyboard selection", async () => {
  const onKeydown = vi.fn();
  const { trigger, value } = mountSelect({ onKeydown });
  for (const key of ["ArrowDown", "ArrowDown", "Enter"]) {
    trigger.dispatchEvent(
      new KeyboardEvent("keydown", {
        key,
        bubbles: true,
        cancelable: true,
      }),
    );
    await nextTick();
  }

  expect(onKeydown).toHaveBeenCalledTimes(3);
  expect(value.value).toBe("inactive");
  expect(trigger.textContent).toContain("Inactive");
  expect(trigger.getAttribute("aria-expanded")).toBe("false");
});
