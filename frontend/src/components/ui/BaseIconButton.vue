<script setup>
defineProps({
  label: { type: String, required: true },
  disabled: { type: Boolean, default: false },
});
</script>

<template>
  <button
    class="icon-button"
    type="button"
    :aria-label="label"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>

<style scoped lang="scss">
.icon-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 2.25rem;
  height: 2.25rem;
  padding: 0.5rem;
  border: 1px solid transparent;
  border-radius: 0.4rem;
  background: transparent;
  color: var(--muted);
  cursor: pointer;
}

.icon-button:hover:not(:disabled) {
  background: #223547;
  color: var(--text);
}

.icon-button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.icon-button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
