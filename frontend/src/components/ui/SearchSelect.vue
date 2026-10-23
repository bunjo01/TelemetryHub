<script setup>
import { computed, nextTick, ref, useId } from "vue";
import BaseButton from "./BaseButton.vue";
import BaseInput from "./BaseInput.vue";

const props = defineProps({
  options: { type: Array, required: true },
  label: { type: String, required: true },
  searchLabel: { type: String, required: true },
  placeholder: { type: String, default: "Select an option" },
  searchPlaceholder: { type: String, default: "Type to search" },
  searchMaxLength: { type: Number, default: 200 },
  loadingText: { type: String, default: "Searching…" },
  emptyText: { type: String, default: "No results found." },
  errorMessage: { type: String, default: "" },
  searchError: { type: String, default: "" },
  paginationMessage: { type: String, default: "" },
  disabled: { type: Boolean, default: false },
  isLoading: { type: Boolean, default: false },
  hasPrevious: { type: Boolean, default: false },
  hasNext: { type: Boolean, default: false },
});

const selected = defineModel({
  type: [Object, null],
  required: true,
});

const query = defineModel("query", {
  type: String,
  required: true,
});

const emit = defineEmits(["previous", "next", "retry"]);

const id = useId();
const selectId = `${id}-select`;
const searchId = `${id}-search`;
const errorId = `${id}-error`;

const dropdown = ref(null);
const summary = ref(null);
const searchInput = ref(null);

const visibleOptions = computed(() => (props.searchError ? [] : props.options));

const hasPagination = computed(
  () => props.hasPrevious || props.hasNext || Boolean(props.paginationMessage),
);

const statusMessage = computed(() => {
  if (props.isLoading) return props.loadingText;
  if (props.searchError) return props.searchError;
  if (!props.options.length) return props.emptyText;
  return props.paginationMessage;
});

const isSelectionOutsideResults = computed(
  () =>
    selected.value !== null &&
    !visibleOptions.value.some(
      (option) => option.value === selected.value.value,
    ),
);

const selectedValue = computed({
  get() {
    return selected.value?.value ?? "";
  },
  set(value) {
    if (props.disabled || props.isLoading || value === selected.value?.value)
      return;

    const option = visibleOptions.value.find((item) => item.value === value);

    if (option) selected.value = option;
  },
});

async function focus() {
  if (props.disabled || !dropdown.value) return;

  dropdown.value.open = true;
  await nextTick();

  if (!props.disabled && dropdown.value?.open) searchInput.value?.focus();
}

function onToggle() {
  if (
    dropdown.value?.open &&
    (document.activeElement === summary.value ||
      document.activeElement === document.body)
  )
    focus();
}

function closePicker() {
  if (props.disabled || !dropdown.value) return;

  dropdown.value.open = false;
  summary.value?.focus();
}

function changePage(direction) {
  if (props.disabled || props.isLoading || props.searchError) return;
  if (direction === "previous" && props.hasPrevious) emit("previous");
  if (direction === "next" && props.hasNext) emit("next");
}

function onEscape(event) {
  if (!dropdown.value?.open) return;

  event.preventDefault();
  event.stopPropagation();
  closePicker();
}

defineExpose({ focus });
</script>

<template>
  <details
    ref="dropdown"
    class="search-select"
    @toggle="onToggle"
    @keydown.esc="onEscape"
  >
    <summary
      ref="summary"
      class="search-select__summary"
      :aria-disabled="disabled"
      :inert="disabled"
    >
      {{ label }}: {{ selected?.label ?? placeholder }}
    </summary>

    <div class="search-select__panel" :inert="disabled">
      <label class="search-select__label" :for="searchId">
        {{ searchLabel }}
      </label>

      <BaseInput
        :id="searchId"
        ref="searchInput"
        v-model="query"
        class="search-select__search"
        type="search"
        :maxlength="searchMaxLength"
        autocomplete="off"
        :placeholder="searchPlaceholder"
        :disabled="disabled"
        @keydown.enter.prevent
      />

      <label class="search-select__label" :for="selectId">
        {{ label }}
      </label>

      <p
        v-if="errorMessage"
        :id="errorId"
        class="message message--error search-select__message"
        role="alert"
      >
        {{ errorMessage }}
      </p>

      <select
        :id="selectId"
        size="4"
        @keydown.enter.prevent="closePicker"
        v-model="selectedValue"
        class="search-select__select"
        :class="{ 'search-select__select--loading': isLoading }"
        :disabled="disabled || isLoading"
        :aria-busy="isLoading"
        :aria-invalid="errorMessage ? true : undefined"
        :aria-describedby="errorMessage ? errorId : undefined"
      >
        <option
          class="search-select__option search-select__option--placeholder"
          disabled
          value=""
        >
          {{ placeholder }}
        </option>

        <option
          v-if="isSelectionOutsideResults"
          class="search-select__option"
          :value="selected.value"
        >
          {{ selected.label }}
        </option>

        <option
          v-for="option in visibleOptions"
          :key="option.value"
          class="search-select__option"
          :value="option.value"
        >
          {{ option.label }}
        </option>
      </select>

      <div class="search-select__status">
        <p
          class="supporting-text search-select__message"
          :role="statusMessage && !searchError ? 'status' : undefined"
        >
          {{ statusMessage }}
        </p>

        <BaseButton
          v-if="searchError && !isLoading"
          type="button"
          variant="secondary"
          :disabled="disabled"
          @click="emit('retry')"
        >
          Retry search
        </BaseButton>
      </div>

      <div
        class="search-select__pagination"
        :class="{ 'search-select__pagination--hidden': !hasPagination }"
        :inert="!hasPagination"
      >
        <BaseButton
          class="search-select__previous"
          type="button"
          variant="secondary"
          :disabled="disabled || isLoading || !!searchError || !hasPrevious"
          @click="changePage('previous')"
        >
          Previous
        </BaseButton>

        <BaseButton
          class="search-select__next"
          type="button"
          variant="secondary"
          :disabled="disabled || isLoading || !!searchError || !hasNext"
          @click="changePage('next')"
        >
          Next
        </BaseButton>
      </div>

      <BaseButton
        type="button"
        variant="secondary"
        :disabled="disabled"
        @click="closePicker"
      >
        Done
      </BaseButton>
    </div>
  </details>
</template>

<style scoped lang="scss">
.search-select {
  min-width: 0;
}

.search-select__summary {
  padding: 0.8rem 1rem;
  border: 1px solid #8aa5c02b;
  border-radius: 0.5rem;
  background: #09121e;
  cursor: pointer;
  overflow-wrap: anywhere;
}

.search-select[open] .search-select__summary {
  display: none;
}

.search-select__panel {
  display: grid;
  gap: 0.75rem;
  min-width: 0;
}

.search-select__label {
  font-size: 0.8rem;
  font-weight: 500;
}

.search-select__search,
.search-select__select {
  width: 100%;
  min-width: 0;
}

.search-select__search:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.search-select__select {
  height: 12rem;
  padding: 0.375rem;
  font: inherit;
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: #507d82 #09121e;
  border: 1px solid #8aa5c02b;
  border-radius: 0.5rem;
  background-color: #09121e;
  color: var(--text);
}

.search-select__select:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}

.search-select__select:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.search-select__select--loading:disabled {
  opacity: 1;
}

.search-select__select::-webkit-scrollbar {
  width: 6px;
}

.search-select__select::-webkit-scrollbar-track {
  background: #09121e;
}

.search-select__select::-webkit-scrollbar-thumb {
  border-radius: 1rem;
  background: #507d82;
}

.search-select__option {
  padding: 0.65rem 0.75rem;
  border-radius: 0.35rem;
  background-color: #09121e;
  color: var(--text);
  font: inherit;
  cursor: pointer;
}

.search-select__option:hover:not(:disabled) {
  background-color: #1b3442;
}

.search-select__option:checked:not(:disabled) {
  background-color: #244d51;
  color: var(--accent);
}

.search-select__option--placeholder,
.search-select__option--placeholder:checked {
  background-color: #09121e;
  color: var(--muted);
  cursor: default;
}

.search-select__message {
  margin: 0;
}

.search-select__status {
  display: grid;
  min-height: 1.5rem;
  justify-items: start;
  gap: 0.75rem;
}

.search-select__pagination {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-items: center;
  gap: 0.5rem;
}

.search-select__pagination--hidden {
  visibility: hidden;
}

.search-select__previous {
  grid-column: 1;
  justify-self: start;
}

.search-select__next {
  grid-column: 2;
  justify-self: end;
}
</style>
