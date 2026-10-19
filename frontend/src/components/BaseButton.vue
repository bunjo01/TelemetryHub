<script setup>
defineProps({
  variant: {
    type: String,
    default: "secondary",
    validator: (value) => ["primary", "secondary"].includes(value),
  },
  type: {
    type: String,
    default: "button",
    validator: (value) => ["button", "submit", "reset"].includes(value),
  },
  disabled: {
    type: Boolean,
    default: false,
  },
  compact: {
    type: Boolean,
    default: false,
  },
  spread: {
    type: Boolean,
    default: false,
  },
});
</script>

<template>
  <button
    class="button"
    :class="{
      'button--primary': variant === 'primary',
      'button--secondary': variant === 'secondary',
      'button--compact': compact,
      'button--spread': spread,
    }"
    :type="type"
    :disabled="disabled"
  >
    <slot />
  </button>
</template>

<style scoped lang="scss">
.button {
  display: inline-flex;
  justify-content: center;
  align-items: center;
  gap: 0.8rem;
  min-height: 2.9rem;
  padding: 0.7rem 1.1rem;
  font: inherit;
  font-size: 0.85rem;
  font-weight: 600;
  border-radius: 0.5rem;
  border: 1px solid transparent;
  text-decoration: none;
  cursor: pointer;
  transition: background 0.15s;
}

.button--primary {
  background: var(--accent);
  color: #102722;
}

.button--primary:hover:not(:disabled) {
  background: #b7f3e6;
}

.button--secondary {
  background: #162331;
  color: var(--text);
  border-color: #8aa5c02b;
}

.button--secondary:hover:not(:disabled) {
  background: #223547;
}

.button--compact {
  min-height: 2.5rem;
  padding: 0.5rem 0.9rem;
}

.button--spread {
  justify-content: space-between;
}

.button:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}

.button:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

@media (prefers-reduced-motion: reduce) {
  .button {
    transition: none;
  }
}
</style>
