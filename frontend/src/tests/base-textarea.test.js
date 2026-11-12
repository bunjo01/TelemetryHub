import { afterEach, expect, it, vi } from "vitest";
import { createApp, h, nextTick, ref } from "vue";
import BaseTextarea from "../components/ui/BaseTextarea.vue";

let app;
let host;

afterEach(() => {
  app?.unmount();
  host?.remove();
});

function mountTextarea(attributes = {}) {
  const value = ref("Initial description");
  const component = ref(null);
  const attrs = ref(attributes);
  host = document.createElement("div");
  document.body.append(host);
  app = createApp({
    setup() {
      return () =>
        h(BaseTextarea, {
          ...attrs.value,
          ref: component,
          modelValue: value.value,
          "onUpdate:modelValue": (updated) => {
            value.value = updated;
          },
        });
    },
  });
  app.mount(host);
  return { value, component, attrs, textarea: host.querySelector("textarea") };
}

it("synchronizes parent updates, multiline input and clearing", async () => {
  const { value, textarea } = mountTextarea();
  expect(textarea.value).toBe("Initial description");
  value.value = "Updated by the form";
  await nextTick();
  expect(textarea.value).toBe("Updated by the form");

  textarea.value = "First line\nSecond line";
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
  await nextTick();
  expect(value.value).toBe("First line\nSecond line");

  textarea.value = "";
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
  await nextTick();
  expect(value.value).toBe("");
});

it("forwards form and accessibility attributes to the native control", () => {
  const { textarea } = mountTextarea({
    id: "description",
    name: "description",
    rows: 4,
    maxlength: 1000,
    placeholder: "Describe this device",
    required: true,
    "aria-describedby": "description-hint",
    "aria-invalid": "true",
  });

  expect(textarea.id).toBe("description");
  expect(textarea.name).toBe("description");
  expect(textarea.rows).toBe(4);
  expect(textarea.maxLength).toBe(1000);
  expect(textarea.placeholder).toBe("Describe this device");
  expect(textarea.required).toBe(true);
  expect(textarea.getAttribute("aria-describedby")).toBe("description-hint");
  expect(textarea.getAttribute("aria-invalid")).toBe("true");
});

it("updates native readonly and disabled states without losing the value", async () => {
  const { attrs, textarea } = mountTextarea({ readonly: true });
  expect(textarea.readOnly).toBe(true);
  expect(textarea.disabled).toBe(false);
  attrs.value = { disabled: true };
  await nextTick();
  expect(textarea.readOnly).toBe(false);
  expect(textarea.disabled).toBe(true);
  expect(textarea.value).toBe("Initial description");
  attrs.value = {};
  await nextTick();
  expect(textarea.disabled).toBe(false);
});

it("exposes focus with options and forwards native focus and blur events", () => {
  const onFocus = vi.fn();
  const onBlur = vi.fn();
  const { component, textarea } = mountTextarea({ onFocus, onBlur });
  const focus = vi.spyOn(textarea, "focus");
  component.value.focus({ preventScroll: true });

  expect(focus).toHaveBeenCalledWith({ preventScroll: true });
  expect(document.activeElement).toBe(textarea);
  expect(onFocus).toHaveBeenCalledTimes(1);
  textarea.blur();
  expect(onBlur).toHaveBeenCalledTimes(1);
});
