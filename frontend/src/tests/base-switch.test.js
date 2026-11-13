import { afterEach, expect, it, vi } from "vitest";
import { createApp, h, nextTick, ref } from "vue";
import BaseSwitch from "../components/ui/BaseSwitch.vue";

let app;
let host;

afterEach(() => {
  app?.unmount();
  host?.remove();
});

function mountSwitch(initial = {}) {
  const props = ref({
    checked: true,
    label: "Device active",
    onLabel: "Active",
    offLabel: "Inactive",
    ...initial,
  });
  const onChange = vi.fn();
  const component = ref(null);
  host = document.createElement("div");
  document.body.append(host);
  app = createApp({
    setup() {
      return () => h(BaseSwitch, { ...props.value, ref: component, onChange });
    },
  });
  app.mount(host);
  return { props, onChange, component, button: host.querySelector("button") };
}

it.each([true, false])(
  "requests the opposite of %s without changing confirmed state",
  async (checked) => {
    const { button, props, onChange } = mountSwitch({ checked });
    expect(button.type).toBe("button");
    expect(button.getAttribute("role")).toBe("switch");
    expect(button.getAttribute("aria-label")).toBe("Device active");
    expect(button.textContent).toContain("Active");
    expect(button.textContent).toContain("Inactive");
    button.click();
    await nextTick();
    expect(onChange).toHaveBeenCalledExactlyOnceWith(!checked);
    expect(button.getAttribute("aria-checked")).toBe(String(checked));

    props.value = { ...props.value, checked: !checked };
    await nextTick();
    expect(button.getAttribute("aria-checked")).toBe(String(!checked));
    expect(button.getAttribute("aria-label")).toBe("Device active");
  },
);

it.each(["disabled", "pending"])(
  "blocks changes while %s and allows them afterward",
  async (state) => {
    const { button, props, onChange } = mountSwitch({ [state]: true });
    expect(button.disabled).toBe(true);
    expect(button.getAttribute("aria-busy")).toBe(String(state === "pending"));
    button.click();
    button.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    expect(onChange).not.toHaveBeenCalled();
    expect(button.getAttribute("aria-checked")).toBe("true");

    props.value = { ...props.value, [state]: false };
    await nextTick();
    expect(button.disabled).toBe(false);
    button.click();
    expect(onChange).toHaveBeenCalledExactlyOnceWith(false);
  },
);

it("allows confirmation to be cancelled without changing selection", async () => {
  const { button, props, onChange } = mountSwitch();
  button.click();
  props.value = { ...props.value, disabled: true };
  await nextTick();
  props.value = { ...props.value, disabled: false };
  await nextTick();
  expect(button.getAttribute("aria-checked")).toBe("true");
  expect(onChange).toHaveBeenCalledTimes(1);
});

it("exposes focus and forwards accessibility attributes to the native button", () => {
  const onFocus = vi.fn();
  const { component, button } = mountSwitch({
    "aria-describedby": "status-hint",
    onFocus,
  });
  const focus = vi.spyOn(button, "focus");
  component.value.focus({ preventScroll: true });
  expect(document.activeElement).toBe(button);
  expect(focus).toHaveBeenCalledWith({ preventScroll: true });
  expect(onFocus).toHaveBeenCalledTimes(1);
  expect(button.getAttribute("aria-describedby")).toBe("status-hint");
});
