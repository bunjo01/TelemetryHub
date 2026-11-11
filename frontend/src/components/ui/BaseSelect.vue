<script setup>
import { computed, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";

const props = defineProps({
  id: { type: String, required: true },
  label: { type: String, required: true },
  options: { type: Array, required: true },
  disabled: { type: Boolean, default: false },
  placeholder: { type: String, default: "Choose an option" },
});

const model = defineModel({
  type: String,
  required: true,
});

const root = ref(null);
const trigger = ref(null);
const isOpen = ref(false);
const activeIndex = ref(-1);
const listId = `${useId()}-options`;
const selectedLabel = computed(
  () =>
    props.options.find((option) => option.value === model.value)?.label ??
    props.placeholder,
);
const activeOptionId = computed(() =>
  isOpen.value && activeIndex.value >= 0
    ? `${listId}-${activeIndex.value}`
    : undefined,
);

let typedText = "";
let typingTimer;

function focus(options) {
  trigger.value?.focus(options);
}

function close() {
  isOpen.value = false;
  typedText = "";
  clearTimeout(typingTimer);
}

function open() {
  if (props.disabled || !props.options.length) return;
  activeIndex.value = Math.max(
    0,
    props.options.findIndex((option) => option.value === model.value),
  );
  isOpen.value = true;
}

function toggle() {
  if (isOpen.value) close();
  else open();
}

function choose(index) {
  if (props.disabled || !props.options[index]) return;
  model.value = props.options[index].value;
  close();
  focus();
}

function onKeydown(event) {
  if (props.disabled) return;

  if (event.key === "Escape" || event.key === "Tab") {
    if (event.key === "Escape" && isOpen.value) {
      event.preventDefault();
      event.stopPropagation();
    }
    close();
    return;
  }

  if (["Enter", " "].includes(event.key)) {
    event.preventDefault();
    if (isOpen.value) choose(activeIndex.value);
    else open();
    return;
  }

  if (["ArrowDown", "ArrowUp", "Home", "End"].includes(event.key)) {
    event.preventDefault();
    if (!props.options.length) return;
    const wasOpen = isOpen.value;
    if (!wasOpen) open();
    if (event.key === "Home") activeIndex.value = 0;
    else if (event.key === "End") activeIndex.value = props.options.length - 1;
    else if (wasOpen) {
      const direction = event.key === "ArrowDown" ? 1 : -1;
      activeIndex.value =
        (activeIndex.value + direction + props.options.length) %
        props.options.length;
    }
    return;
  }

  if (
    event.key.length === 1 &&
    !event.ctrlKey &&
    !event.metaKey &&
    !event.altKey
  ) {
    event.preventDefault();
    if (!isOpen.value) open();
    typedText += event.key.toLowerCase();
    clearTimeout(typingTimer);
    typingTimer = setTimeout(() => {
      typedText = "";
    }, 500);
    const index = props.options.findIndex((option) =>
      option.label.toLowerCase().startsWith(typedText),
    );
    if (index >= 0) activeIndex.value = index;
  }
}

function onOutsidePointer(event) {
  if (!root.value?.contains(event.target)) close();
}

watch(() => [props.disabled, model.value, props.options], close);

onMounted(() => document.addEventListener("pointerdown", onOutsidePointer));
onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onOutsidePointer);
  clearTimeout(typingTimer);
});

defineExpose({ focus });
</script>

<template>
  <div ref="root" class="select">
    <button
      :id="id"
      ref="trigger"
      class="select__trigger"
      type="button"
      role="combobox"
      :aria-label="label"
      aria-haspopup="listbox"
      :aria-expanded="isOpen"
      :aria-controls="listId"
      :aria-activedescendant="activeOptionId"
      :disabled="disabled"
      @click="toggle"
      @keydown="onKeydown"
      @blur="close"
    >
      <span class="select__value">{{ selectedLabel }}</span>
      <svg
        class="select__chevron"
        :class="{ 'select__chevron--open': isOpen }"
        viewBox="0 0 16 16"
        aria-hidden="true"
      >
        <path d="m4 6 4 4 4-4" />
      </svg>
    </button>

    <div
      v-if="isOpen"
      :id="listId"
      class="select__options"
      role="listbox"
      :aria-label="label"
    >
      <button
        v-for="(option, index) in options"
        :id="`${listId}-${index}`"
        :key="option.value"
        class="select__option"
        :class="{
          'select__option--selected': option.value === model,
          'select__option--focused': index === activeIndex,
        }"
        type="button"
        role="option"
        :aria-selected="option.value === model"
        tabindex="-1"
        @pointerdown.prevent
        @pointermove="activeIndex = index"
        @click="choose(index)"
      >
        {{ option.label }}
      </button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.select {
  position: relative;
  min-width: 0;
}

.select__trigger {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  width: 100%;
  min-height: 3rem;
  min-width: 0;
  max-width: 100%;
  padding: 0.8rem 1rem;
  font: inherit;
  border: 1px solid #8aa5c02b;
  border-radius: 0.5rem;
  background-color: #09121e;
  color: var(--text);
  cursor: pointer;
  text-align: left;
}

.select__trigger:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}

.select__trigger:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.select__value {
  min-width: 0;
  overflow-wrap: anywhere;
}

.select__chevron {
  width: 1rem;
  height: 1rem;
  flex-shrink: 0;
  fill: none;
  stroke: currentColor;
  stroke-width: 1.5;
}

.select__chevron--open {
  transform: rotate(180deg);
}

.select__options {
  position: absolute;
  inset: calc(100% + 0.5rem) 0 auto;
  z-index: 2;
  display: grid;
  gap: 0.25rem;
  max-height: 16rem;
  overflow-y: auto;
  padding: 0.375rem;
  border: 1px solid #8aa5c02b;
  border-radius: 0.5rem;
  background: #09121e;
  box-shadow: 0 12px 30px #0005;
}

.select__option {
  min-height: 2.75rem;
  padding: 0.65rem 0.75rem;
  border: 1px solid transparent;
  border-radius: 0.35rem;
  background: #09121e;
  color: var(--text);
  font: inherit;
  text-align: left;
  overflow-wrap: anywhere;
  cursor: pointer;
}

.select__option--selected {
  background: #244d51;
  color: var(--accent);
}

.select__option--focused {
  background: #1b3442;
  border-color: var(--accent);
}
</style>
