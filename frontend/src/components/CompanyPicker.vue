<script setup>
import {
  computed,
  nextTick,
  onBeforeUnmount,
  onMounted,
  ref,
  useId,
  watch,
} from "vue";
import { searchCompanies } from "../api/companies.api.js";
import { useAuthStore } from "../stores/auth.js";
import BaseButton from "./BaseButton.vue";
import BaseInput from "./BaseInput.vue";

const props = defineProps({
  disabled: {
    type: Boolean,
    default: false,
  },
});

const selected = defineModel({
  type: [Object, null],
  required: true,
});

const emit = defineEmits(["unauthorized"]);

const auth = useAuthStore();
const id = useId();
const selectId = `${id}-company`;
const searchId = `${id}-search`;

const dropdown = ref(null);
const summary = ref(null);
const searchInput = ref(null);
const query = ref("");
const companies = ref([]);
const offset = ref(0);
const hasMore = ref(false);
const isLoading = ref(false);
const searchError = ref("");

const visibleCompanies = computed(() =>
  isLoading.value || searchError.value ? [] : companies.value,
);

const isSelectionOutsideResults = computed(
  () =>
    selected.value !== null &&
    !visibleCompanies.value.some((company) => company.id === selected.value.id),
);

const selectedCompanyId = computed({
  get() {
    return selected.value?.id ?? "";
  },
  set(companyId) {
    if (props.disabled || companyId === selected.value?.id) return;

    const company = visibleCompanies.value.find(
      (item) => item.id === companyId,
    );

    if (company) selected.value = company;
  },
});

const pageSize = 20;
const maximumOffset = 10000;
const searchDelay = 250;

let searchRequest;
let debounce;
let isDisposed = false;
let requestedOffset = 0;
let interruptedOffset = null;

function stopSearch() {
  clearTimeout(debounce);
  searchRequest?.abort();
  searchRequest = undefined;
  isLoading.value = false;
}

async function loadCompanies(nextOffset) {
  stopSearch();

  if (props.disabled || isDisposed) return;

  requestedOffset = nextOffset;
  const controller = new AbortController();
  searchRequest = controller;
  isLoading.value = true;
  searchError.value = "";

  try {
    const result = await searchCompanies(
      query.value,
      nextOffset,
      auth.token,
      controller.signal,
    );

    if (controller.signal.aborted || isDisposed) return;

    companies.value = result.items;
    hasMore.value = result.hasMore;
    offset.value = nextOffset;
  } catch (failure) {
    if (controller.signal.aborted || isDisposed) return;

    companies.value = [];
    hasMore.value = false;

    if (failure.status === 401) {
      emit("unauthorized", failure);
    } else {
      searchError.value = failure.message;
    }
  } finally {
    if (searchRequest === controller) {
      searchRequest = undefined;
      isLoading.value = false;
    }
  }
}

watch(query, () => {
  stopSearch();

  companies.value = [];
  hasMore.value = false;
  searchError.value = "";

  if (props.disabled || isDisposed) return;

  requestedOffset = 0;
  isLoading.value = true;
  debounce = setTimeout(() => loadCompanies(0), searchDelay);
});

watch(
  () => props.disabled,
  (isDisabled) => {
    if (!isDisabled) {
      if (interruptedOffset !== null) {
        const nextOffset = interruptedOffset;
        interruptedOffset = null;
        loadCompanies(nextOffset);
      }
      return;
    }

    interruptedOffset = isLoading.value ? requestedOffset : null;
    stopSearch();
  },
);

onMounted(() => {
  loadCompanies(0);
});

onBeforeUnmount(() => {
  isDisposed = true;
  stopSearch();
});

async function focus() {
  if (props.disabled) return;

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
  if (props.disabled) return;

  dropdown.value.open = false;
  summary.value?.focus();
}

function onEscape(event) {
  if (!dropdown.value?.open) return;

  event.preventDefault();
  event.stopPropagation();
  closePicker();
}

function retrySearch() {
  loadCompanies(requestedOffset);
}

defineExpose({ focus });
</script>

<template>
  <details
    ref="dropdown"
    class="company-picker"
    @toggle="onToggle"
    @keydown.esc="onEscape"
  >
    <summary
      ref="summary"
      class="company-picker__summary"
      :aria-disabled="disabled"
      :inert="disabled"
    >
      Company: {{ selected?.name ?? "Select a company" }}
    </summary>

    <div class="company-picker__panel" :inert="disabled">
      <label class="company-picker__label" :for="searchId">
        Search companies
      </label>

      <BaseInput
        :id="searchId"
        ref="searchInput"
        v-model="query"
        class="company-picker__search"
        type="search"
        maxlength="200"
        autocomplete="off"
        placeholder="Type a company name"
        :disabled="disabled"
        @keydown.enter.prevent
      />

      <label class="company-picker__label" :for="selectId"> Company </label>

      <select
        :id="selectId"
        size="4"
        @keydown.enter.prevent="closePicker"
        v-model="selectedCompanyId"
        class="company-picker__select"
        :disabled="disabled"
        :aria-busy="isLoading"
      >
        <option
          class="company-picker__option company-picker__option--placeholder"
          disabled
          value=""
        >
          Select a company
        </option>

        <option
          v-if="isSelectionOutsideResults"
          class="company-picker__option"
          :value="selected.id"
        >
          {{ selected.name }}
        </option>

        <option
          v-for="company in visibleCompanies"
          :key="company.id"
          class="company-picker__option"
          :value="company.id"
        >
          {{ company.name }}
        </option>
      </select>

      <p
        v-if="isLoading"
        class="supporting-text company-picker__message"
        role="status"
      >
        Searching companies…
      </p>

      <div v-else-if="searchError" class="company-picker__error">
        <p
          class="message message--error company-picker__message"
          role="alert"
        >
          {{ searchError }}
        </p>

        <BaseButton
          type="button"
          variant="secondary"
          :disabled="disabled"
          @click="retrySearch"
        >
          Retry search
        </BaseButton>
      </div>

      <template v-else>
        <p
          v-if="!companies.length"
          class="supporting-text company-picker__message"
          role="status"
        >
          No companies found. Try a different name or create a company first.
        </p>

        <div v-if="offset > 0 || hasMore" class="company-picker__pagination">
          <BaseButton
            v-if="offset > 0"
            type="button"
            variant="secondary"
            :disabled="disabled"
            @click="loadCompanies(offset - pageSize)"
          >
            Previous
          </BaseButton>

          <BaseButton
            v-if="hasMore && offset < maximumOffset"
            type="button"
            variant="secondary"
            :disabled="disabled"
            @click="loadCompanies(offset + pageSize)"
          >
            Next
          </BaseButton>

          <p
            v-if="hasMore && offset >= maximumOffset"
            class="supporting-text company-picker__message"
          >
            Narrow your search to find more companies.
          </p>
        </div>
      </template>

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
.company-picker {
  min-width: 0;
}

.company-picker__summary {
  padding: 0.8rem 1rem;
  border: 1px solid #8aa5c02b;
  border-radius: 0.5rem;
  background: #09121e;
  cursor: pointer;
  overflow-wrap: anywhere;
}

.company-picker[open] .company-picker__summary {
  display: none;
}

.company-picker__panel {
  display: grid;
  gap: 0.75rem;
  min-width: 0;
}

.company-picker__label {
  font-size: 0.8rem;
  font-weight: 500;
}

.company-picker__search,
.company-picker__select {
  width: 100%;
  min-width: 0;
}

.company-picker__search:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.company-picker__select {
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

.company-picker__select:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}

.company-picker__select:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.company-picker__select::-webkit-scrollbar {
  width: 6px;
}

.company-picker__select::-webkit-scrollbar-track {
  background: #09121e;
}

.company-picker__select::-webkit-scrollbar-thumb {
  border-radius: 1rem;
  background: #507d82;
}

.company-picker__option {
  padding: 0.65rem 0.75rem;
  border-radius: 0.35rem;
  background-color: #09121e;
  color: var(--text);
  font: inherit;
  cursor: pointer;
}

.company-picker__option:hover:not(:disabled) {
  background-color: #1b3442;
}

.company-picker__option:checked:not(:disabled) {
  background-color: #244d51;
  color: var(--accent);
}

.company-picker__option--placeholder,
.company-picker__option--placeholder:checked {
  background-color: #09121e;
  color: var(--muted);
  cursor: default;
}

.company-picker__message {
  margin: 0;
}

.company-picker__error {
  display: grid;
  justify-items: start;
  gap: 0.75rem;
}

.company-picker__pagination {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
</style>
