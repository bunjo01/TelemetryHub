import { defineStore } from "pinia";
import { computed, onScopeDispose, ref, shallowRef } from "vue";

export const useNotificationStore = defineStore("notifications", () => {
  const notifications = ref([]);
  const targets = shallowRef([]);
  const visible = computed(() => notifications.value.slice(0, 3));
  const target = computed(() => targets.value.at(-1) ?? "body");
  const timers = new Map();
  const origins = new Map();
  const interactions = new Map();
  const duration = 8000;
  let progressFrame;
  let nextId = 0;
  let isHidden = false;

  function stopTimer(id) {
    const timer = timers.get(id);
    if (!timer?.handle) return;
    clearTimeout(timer.handle);
    timer.remaining = Math.max(
      0,
      timer.remaining - (Date.now() - timer.started),
    );
    timer.notification.remaining = timer.remaining;
    timer.handle = undefined;
  }

  function updateProgress() {
    for (const timer of timers.values()) {
      if (timer.handle) {
        timer.notification.remaining = Math.max(
          0,
          timer.remaining - (Date.now() - timer.started),
        );
      }
    }
    progressFrame = requestAnimationFrame(updateProgress);
  }

  function syncTimers() {
    const visibleIds = new Set(visible.value.map((item) => item.id));
    for (const [id, timer] of timers) {
      if (!visibleIds.has(id) || isHidden || timer.reasons.size) {
        stopTimer(id);
      } else if (!timer.handle) {
        timer.started = Date.now();
        timer.handle = setTimeout(() => dismiss(id), timer.remaining);
      }
    }
    const isRunning = [...timers.values()].some((timer) => timer.handle);
    if (isRunning && progressFrame === undefined) {
      progressFrame = requestAnimationFrame(updateProgress);
    } else if (!isRunning && progressFrame !== undefined) {
      cancelAnimationFrame(progressFrame);
      progressFrame = undefined;
    }
  }

  function dismiss(id, restoreFocus = false) {
    const origin = origins.get(id);
    stopTimer(id);
    timers.delete(id);
    origins.delete(id);
    interactions.delete(id);
    notifications.value = notifications.value.filter((item) => item.id !== id);
    syncTimers();
    if (!restoreFocus) return;

    const dialog = targets.value.at(-1);
    if (
      origin?.isConnected &&
      !origin.matches(":disabled") &&
      !origin.closest("[inert], dialog:not([open])") &&
      origin.getClientRects().length &&
      getComputedStyle(origin).visibility === "visible" &&
      (!dialog || dialog.contains(origin))
    ) {
      origin.focus({ preventScroll: true });
      if (document.activeElement === origin) return;
    }

    const fallback = dialog ?? document.querySelector("main h1[tabindex]");
    fallback?.focus({ preventScroll: true });
  }

  function remove(key) {
    const item = notifications.value.find(
      (notification) => notification.key === key,
    );
    if (item) dismiss(item.id);
  }

  function show({ key, message, variant = "info", origin }) {
    const existing = notifications.value.find((item) => item.key === key);
    const id = existing?.id ?? ++nextId;
    const reasons = interactions.get(id) ?? new Set();
    interactions.set(id, reasons);
    if (existing) {
      stopTimer(id);
      timers.delete(id);
      existing.message = message;
      existing.variant = variant;
      existing.revision += 1;
    } else {
      notifications.value.push({
        id,
        key,
        message,
        variant,
        revision: 0,
        duration,
        remaining: duration,
      });
      if (typeof document !== "undefined")
        origins.set(id, origin ?? document.activeElement);
    }
    const notification = notifications.value.find((item) => item.id === id);
    notification.remaining = duration;
    timers.set(id, {
      notification,
      remaining: duration,
      started: 0,
      handle: undefined,
      reasons,
    });
    syncTimers();
    return id;
  }

  function pause(id, reason) {
    interactions.get(id)?.add(reason);
    syncTimers();
  }

  function resume(id, reason) {
    interactions.get(id)?.delete(reason);
    syncTimers();
  }

  function setHidden(value) {
    isHidden = value;
    syncTimers();
  }

  function clear() {
    for (const item of [...notifications.value]) dismiss(item.id);
  }

  function registerTarget(element) {
    targets.value = [
      ...targets.value.filter((target) => target !== element),
      element,
    ];
  }

  function unregisterTarget(element) {
    targets.value = targets.value.filter((target) => target !== element);
  }

  onScopeDispose(clear);

  return {
    notifications,
    visible,
    target,
    show,
    dismiss,
    remove,
    clear,
    pause,
    resume,
    setHidden,
    registerTarget,
    unregisterTarget,
  };
});
