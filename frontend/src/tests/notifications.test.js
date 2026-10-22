import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { useNotificationStore } from "../stores/notifications.js";

beforeEach(() => {
  setActivePinia(createPinia());
  vi.useFakeTimers();
});
afterEach(() => {
  useNotificationStore().clear();
  vi.useRealTimers();
});

test.each(["error", "success", "info"])(
  "%s expires after eight seconds",
  (variant) => {
    const store = useNotificationStore();
    store.show({ key: "operation", variant, message: "Result" });
    vi.advanceTimersByTime(4000);
    expect(store.visible[0].remaining).toBeGreaterThanOrEqual(4000);
    expect(store.visible[0].remaining).toBeLessThan(4020);
    vi.advanceTimersByTime(3999);
    expect(store.visible).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(store.visible).toHaveLength(0);
    expect(vi.getTimerCount()).toBe(0);
  },
);

test("replaces matching keys and restarts their countdown", () => {
  const store = useNotificationStore();
  const id = store.show({ key: "login", variant: "error", message: "Failed" });
  vi.advanceTimersByTime(4000);
  expect(
    store.show({ key: "login", variant: "error", message: "Try again" }),
  ).toBe(id);
  expect(store.notifications).toHaveLength(1);
  expect(store.visible[0].remaining).toBe(8000);
  vi.advanceTimersByTime(7999);
  expect(store.visible[0].message).toBe("Try again");
  vi.advanceTimersByTime(1);
  expect(store.visible).toHaveLength(0);
});

test("queues without expiring hidden notifications", () => {
  const store = useNotificationStore();
  for (let i = 0; i < 4; i++)
    store.show({ key: String(i), message: String(i) });
  expect(store.visible).toHaveLength(3);
  vi.advanceTimersByTime(8000);
  expect(store.visible).toHaveLength(1);
  expect(store.visible[0].message).toBe("3");
  expect(store.visible[0].remaining).toBe(8000);
  vi.advanceTimersByTime(7999);
  expect(store.visible).toHaveLength(1);
  vi.advanceTimersByTime(1);
  expect(store.visible).toHaveLength(0);
});

test("pauses remaining duration for hover, focus and hidden tabs", () => {
  const store = useNotificationStore();
  const id = store.show({ key: "copy", message: "Copied", variant: "success" });
  vi.advanceTimersByTime(3000);
  store.pause(id, "hover");
  store.pause(id, "focus");
  vi.advanceTimersByTime(10000);
  expect(store.visible[0].remaining).toBe(5000);
  expect(vi.getTimerCount()).toBe(0);
  store.resume(id, "hover");
  vi.advanceTimersByTime(10000);
  expect(store.visible).toHaveLength(1);
  store.resume(id, "focus");
  store.setHidden(true);
  vi.advanceTimersByTime(10000);
  store.setHidden(false);
  vi.advanceTimersByTime(4999);
  expect(store.visible).toHaveLength(1);
  vi.advanceTimersByTime(1);
  expect(store.visible).toHaveLength(0);
});

test("clears timers and restores the previous modal target", () => {
  const store = useNotificationStore();
  const first = {};
  const second = {};
  store.registerTarget(first);
  store.registerTarget(second);
  expect(store.target).toBe(second);
  store.unregisterTarget(second);
  expect(store.target).toBe(first);
  store.unregisterTarget(first);
  expect(store.target).toBe("body");
  store.show({ key: "copy", message: "Copied" });
  store.clear();
  expect(vi.getTimerCount()).toBe(0);
});

test("replacement preserves focus pauses when an error becomes success", () => {
  const store = useNotificationStore();
  const id = store.show({
    key: "operation",
    message: "Failed",
    variant: "error",
  });
  store.pause(id, "focus");
  store.show({ key: "operation", message: "Succeeded", variant: "success" });
  vi.advanceTimersByTime(10000);
  expect(store.visible).toHaveLength(1);
  store.resume(id, "focus");
  vi.advanceTimersByTime(8000);
  expect(store.visible).toHaveLength(0);
});

test("updates progress each frame using elapsed time after delayed rendering", () => {
  const store = useNotificationStore();
  store.show({ key: "copy", message: "Copied" });
  const started = Date.now();
  vi.advanceTimersToNextFrame();
  expect(store.visible[0].remaining).toBe(8000 - (Date.now() - started));
  expect(store.visible[0].remaining).toBeLessThan(8000);
  vi.setSystemTime(Date.now() + 2000);
  vi.advanceTimersToNextFrame();
  expect(store.visible[0].remaining).toBe(8000 - (Date.now() - started));
});

test("shares one animation loop and cancels it when the store is disposed", () => {
  const store = useNotificationStore();
  store.show({ key: "first", message: "First" });
  store.show({ key: "second", message: "Second" });
  expect(vi.getTimerCount()).toBe(3);
  vi.advanceTimersToNextFrame();
  expect(vi.getTimerCount()).toBe(3);
  store.$dispose();
  expect(vi.getTimerCount()).toBe(0);
});
