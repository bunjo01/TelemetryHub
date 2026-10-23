<script setup>
import { computed, onBeforeUnmount } from "vue";

const props = defineProps({
  notification: { type: Object, required: true },
});
const emit = defineEmits(["dismiss", "pause", "resume"]);
const title = computed(
  () =>
    ({ error: "Error", success: "Success", info: "Information" })[
      props.notification.variant
    ],
);

function onFocusOut(event) {
  if (!event.currentTarget.contains(event.relatedTarget))
    emit("resume", "focus");
}

onBeforeUnmount(() => {
  emit("resume", "hover");
  emit("resume", "focus");
});
</script>

<template>
  <section
    :aria-label="title"
    class="toast"
    :class="`toast--${notification.variant}`"
    @mouseenter="emit('pause', 'hover')"
    @mouseleave="emit('resume', 'hover')"
    @focusin="emit('pause', 'focus')"
    @focusout="onFocusOut"
  >
    <div
      :role="notification.variant === 'error' ? 'alert' : 'status'"
      aria-atomic="true"
    >
      <p class="toast__title">{{ title }}</p>
      <p :key="notification.revision" class="toast__message">
        {{ notification.message }}
      </p>
    </div>
    <button
      class="toast__dismiss"
      type="button"
      :aria-label="`Dismiss ${title.toLowerCase()} notification`"
      @click="emit('dismiss', $event.currentTarget === $event.currentTarget.ownerDocument.activeElement)"
    >
      <span aria-hidden="true">×</span>
    </button>
    <div class="toast__progress" aria-hidden="true">
      <div
        class="toast__progress-bar"
        :style="{ transform: `scaleX(${notification.remaining / notification.duration})` }"
      />
    </div>
  </section>
</template>

<style scoped lang="scss">
.toast {
  --toast-accent: var(--accent);

  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 0.75rem;
  padding: 1rem;
  border: 1px solid var(--line);
  border-left: 3px solid var(--toast-accent);
  border-radius: 0.65rem;
  background: #142331;
  color: var(--text);
  box-shadow: 0 8px 28px #0006;
  pointer-events: auto;
  overflow-wrap: anywhere;
}

.toast--error {
  --toast-accent: #ffc5cb;
}

.toast--success {
  --toast-accent: var(--accent);
}

.toast--info {
  --toast-accent: #a9cffa;
}

.toast__title {
  margin: 0 0 0.35rem;
  font-size: 0.9rem;
  font-weight: 600;
}

.toast__message {
  margin: 0;
  font-size: 0.85rem;
  line-height: 1.5;
}

.toast__dismiss {
  display: grid;
  place-items: center;
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: 1px solid var(--line);
  border-radius: 0.4rem;
  background: transparent;
  color: var(--text);
  font-size: 1.25rem;
}

.toast__dismiss:hover {
  background: #ffffff12;
}

.toast__progress {
  position: absolute;
  inset: -1px -1px -1px -3px;
  overflow: hidden;
  border-radius: inherit;
  pointer-events: none;
}

.toast__progress::before {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 3px;
  background: #ffffff12;
  content: "";
}

.toast__progress-bar {
  position: absolute;
  right: 0;
  bottom: 0;
  left: 0;
  height: 3px;
  background: var(--toast-accent);
  transform-origin: left;
}
</style>
