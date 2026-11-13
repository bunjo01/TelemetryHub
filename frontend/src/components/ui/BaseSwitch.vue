<script setup>
import { ref } from "vue";

const props = defineProps({
  checked: { type: Boolean, required: true },
  label: { type: String, required: true },
  onLabel: { type: String, default: "On" },
  offLabel: { type: String, default: "Off" },
  disabled: { type: Boolean, default: false },
  pending: { type: Boolean, default: false },
});

const emit = defineEmits(["change"]);
const button = ref(null);

function requestChange() {
  if (props.disabled || props.pending) return;
  emit("change", !props.checked);
}

function focus(options) {
  button.value?.focus(options);
}

defineExpose({ focus });
</script>

<template>
  <button
    ref="button"
    class="switch"
    :class="{
      'switch--checked': checked,
      'switch--pending': pending,
    }"
    type="button"
    role="switch"
    :aria-label="label"
    :aria-checked="checked"
    :aria-busy="pending"
    :disabled="disabled || pending"
    @click="requestChange"
  >
    <span class="switch__selection" aria-hidden="true"></span>
    <span class="switch__label switch__label--on" aria-hidden="true">
      {{ onLabel }}
    </span>
    <span class="switch__label switch__label--off" aria-hidden="true">
      {{ offLabel }}
    </span>
    <span v-if="pending" class="switch__spinner" aria-hidden="true"></span>
  </button>
</template>

<style scoped lang="scss">
.switch {
  position: relative;
  display: inline-grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: center;
  width: 12rem;
  max-width: 100%;
  min-height: 2.5rem;
  padding: 0.25rem;
  border: 1px solid var(--line);
  border-radius: 0.5rem;
  background: #09121e;
  color: var(--muted);
  font: inherit;
  cursor: pointer;
}

.switch__selection {
  position: absolute;
  inset: 0.25rem auto 0.25rem 0.25rem;
  width: calc(50% - 0.25rem);
  border: 1px solid #e5a0a340;
  border-radius: 0.3rem;
  background: #e5a0a31a;
  transform: translateX(100%);
  transition:
    transform 180ms ease,
    background-color 180ms ease,
    border-color 180ms ease;
}

.switch--checked .switch__selection {
  border-color: #8ae7d629;
  background: #8ae7d60d;
  transform: translateX(0);
}

.switch__label {
  position: relative;
  padding: 0.25rem 0.65rem;
  font-size: 0.8rem;
  font-weight: 500;
  line-height: 1.4;
  overflow-wrap: anywhere;
  transition: color 180ms ease;
}

.switch__label--off {
  color: #efb4b7;
}

.switch--checked .switch__label--on {
  color: var(--accent);
}

.switch--checked .switch__label--off {
  color: var(--muted);
}

.switch:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}

.switch:hover:not(:disabled) {
  border-color: #8aa5c066;
}

.switch:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.switch--pending:disabled {
  cursor: progress;
  opacity: 1;
}

.switch__spinner {
  position: absolute;
  top: calc(50% - 0.4rem);
  left: calc(50% - 0.4rem);
  width: 0.8rem;
  height: 0.8rem;
  border: 2px solid var(--line);
  border-top-color: var(--text);
  border-radius: 50%;
  animation: switch-spin 700ms linear infinite;
}

@keyframes switch-spin {
  to {
    transform: rotate(360deg);
  }
}

@media (prefers-reduced-motion: reduce) {
  .switch__selection,
  .switch__label {
    transition: none;
  }

  .switch__spinner {
    animation: none;
  }
}
</style>
