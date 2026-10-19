<script setup>
import { nextTick, onBeforeUnmount, onMounted, ref, useId, watch } from "vue";
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
const labelId = `${id}-label`;
const selectionId = `${id}-selection`;
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

    // Resume only unfinished searches, including the debounce wait.
    interruptedOffset = isLoading.value ? requestedOffset : null;
    stopSearch();

    if (dropdown.value) {
      dropdown.value.open = false;
    }
  },
);

onMounted(() => {
  loadCompanies(0);
});

onBeforeUnmount(() => {
  isDisposed = true;
  stopSearch();
});

function open() {
  if (props.disabled) return;

  dropdown.value.open = true;
}

async function onDropdownToggle() {
  if (!dropdown.value?.open || props.disabled) return;

  await nextTick();

  if (dropdown.value?.open && !props.disabled) {
    searchInput.value?.focus();
  }
}

function selectCompany(company) {
  if (props.disabled) return;

  selected.value = company;
  dropdown.value.open = false;
  summary.value.focus();
}

function escapeDropdown(event) {
  if (!dropdown.value?.open) return;

  event.preventDefault();
  event.stopPropagation();

  dropdown.value.open = false;
  summary.value.focus();
}

defineExpose({ open });
</script>

<template>
  <div class="company-picker">
    <span :id="labelId" class="company-picker__label"> Company </span>

    <details
      ref="dropdown"
      class="company-picker__dropdown"
      @toggle="onDropdownToggle"
      @keydown.esc="escapeDropdown"
    >
      <summary
        ref="summary"
        class="company-picker__summary"
        :aria-labelledby="`${labelId} ${selectionId}`"
        :aria-disabled="disabled"
        :inert="disabled"
      >
        <span :id="selectionId">
          {{ selected?.name ?? "Select a company" }}
        </span>
        <span aria-hidden="true">⌄</span>
      </summary>

      <div class="company-picker__options" :inert="disabled">
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
          @keydown.enter.prevent
        />

        <p v-if="isLoading" class="muted" role="status">Searching companies…</p>

        <div v-else-if="searchError">
          <p class="message error" role="alert">
            {{ searchError }}
          </p>
          <BaseButton
            type="button"
            variant="secondary"
            @click="loadCompanies(0)"
          >
            Retry search
          </BaseButton>
        </div>

        <template v-else>
          <p v-if="!companies.length" class="muted" role="status">
            No companies found. Try a different name or create a company first.
          </p>

          <ul
            v-else
            class="company-picker__results"
            aria-label="Matching companies"
          >
            <li
              v-for="company in companies"
              :key="company.id"
              class="company-picker__result"
            >
              <button
                type="button"
                class="company-picker__option"
                :aria-pressed="selected?.id === company.id"
                :title="company.name"
                @click="selectCompany(company)"
              >
                <span class="company-picker__node" aria-hidden="true">
                  {{ selected?.id === company.id ? "✓" : "◇" }}
                </span>
                <span class="company-picker__name">
                  {{ company.name }}
                </span>
              </button>
            </li>
          </ul>

          <div class="company-picker__pagination">
            <BaseButton
              v-if="offset > 0"
              type="button"
              variant="secondary"
              @click="loadCompanies(offset - pageSize)"
            >
              Previous
            </BaseButton>
            <BaseButton
              v-if="hasMore && offset < maximumOffset"
              type="button"
              variant="secondary"
              @click="loadCompanies(offset + pageSize)"
            >
              Next
            </BaseButton>
            <p v-if="hasMore && offset >= maximumOffset" class="muted">
              Narrow your search to find more companies.
            </p>
          </div>
        </template>
      </div>
    </details>
  </div>
</template>

<style scoped lang="scss">
.company-picker {
  display: grid;
  gap: 0.75rem;
}

.company-picker__label {
  font-size: 0.8rem;
  font-weight: 500;
}

.company-picker__dropdown {
  position: relative;
  border: 1px solid #8aa5c02b;
  border-radius: 0.5rem;
  background: #09121e;
}

.company-picker__summary {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding: 0.8rem 1rem;
  cursor: pointer;
  overflow-wrap: anywhere;
}

.company-picker__summary::-webkit-details-marker {
  display: none;
}

.company-picker__options {
  position: absolute;
  z-index: 2;
  top: calc(100% + 0.35rem);
  left: -1px;
  right: -1px;
  display: flex;
  flex-direction: column;
  max-height: min(28rem, calc(50svh - 6rem));
  overflow: hidden;
  border: 1px solid #8aa5c040;
  border-radius: 0.65rem;
  padding: 1rem;
  background: #101b28;
  box-shadow: 0 16px 40px #0008;
}

.company-picker__options > :not(.company-picker__results) {
  flex-shrink: 0;
}

.company-picker__search {
  display: block;
  width: 100%;
  margin-top: 0.5rem;
}

.company-picker__results {
  --row-height: 3rem;
  --row-gap: 0.375rem;

  display: flex;
  flex-direction: column;
  gap: var(--row-gap);
  list-style: none;
  padding: 0 0.35rem 0 0;
  margin: 0.75rem 0;
  min-height: 0;
  // Four complete rows at most; smaller screens can show fewer.
  max-height: calc(4 * var(--row-height) + 3 * var(--row-gap));
  overflow-y: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
  scrollbar-color: #507d82 #09121e;
}

.company-picker__results::-webkit-scrollbar {
  width: 6px;
}

.company-picker__results::-webkit-scrollbar-track {
  background: #09121e;
  border-radius: 1rem;
}

.company-picker__results::-webkit-scrollbar-thumb {
  background: #507d82;
  border-radius: 1rem;
}

.company-picker__results::-webkit-scrollbar-thumb:hover {
  background: var(--accent);
}

.company-picker__result {
  flex: 0 0 var(--row-height);
  min-height: 0;
}

.company-picker__option {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  width: 100%;
  height: 100%;
  padding: 0.5rem 0.7rem;
  text-align: left;
  background: linear-gradient(110deg, #1b3442, #132332);
  color: var(--text);
  border: 1px solid #74b9b52b;
  border-radius: 0.4rem;
  box-shadow: inset 2px 0 #76c6bc55;
  transition: background 0.15s, border-color 0.15s, box-shadow 0.15s;
}

.company-picker__option:hover,
.company-picker__option[aria-pressed="true"] {
  background: linear-gradient(110deg, #244d51, #182d3f);
  border-color: #9be5d580;
  box-shadow: inset 3px 0 var(--accent), inset 0 0 18px #9be5d50c;
}

.company-picker__option:focus-visible {
  outline-offset: -3px;
}

.company-picker__node {
  color: var(--accent);
  flex-shrink: 0;
  text-shadow: 0 0 10px #9be5d566;
}

.company-picker__name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.875rem;
}

.company-picker__pagination {
  display: flex;
  justify-content: space-between;
  gap: 0.5rem;
}
</style>
