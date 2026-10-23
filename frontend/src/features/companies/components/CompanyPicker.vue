<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from "vue";
import { searchCompanies } from "../../../api/companies.api.js";
import SearchSelect from "../../../components/ui/SearchSelect.vue";
import { useAuthStore } from "../../../stores/auth.js";
import { useNotificationStore } from "../../../stores/notifications.js";

const props = defineProps({
  errorMessage: { type: String, default: "" },
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
const notifications = useNotificationStore();
const searchSelect = ref(null);
const query = ref("");
const companies = ref([]);
const offset = ref(0);
const hasMore = ref(false);
const isLoading = ref(false);
const searchError = ref("");

const options = computed(() =>
  companies.value.map((company) => ({
    value: company.id,
    label: company.name,
  })),
);

const selectedOption = computed({
  get() {
    if (!selected.value) return null;

    return {
      value: selected.value.id,
      label: selected.value.name,
    };
  },
  set(option) {
    if (
      props.disabled ||
      isLoading.value ||
      !option ||
      option.value === selected.value?.id
    )
      return;

    const company = companies.value.find((item) => item.id === option.value);

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
  notifications.remove("company-search");

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

    if (failure.status === 401) {
      emit("unauthorized", failure);
    } else {
      searchError.value = failure.message;
      notifications.show({
        key: "company-search",
        variant: "error",
        message: failure.message,
      });
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
  offset.value = 0;
  hasMore.value = false;
  searchError.value = "";
  notifications.remove("company-search");

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
  notifications.remove("company-search");
  stopSearch();
});

function focus() {
  return searchSelect.value?.focus();
}

function changePage(direction) {
  if (props.disabled || isLoading.value || searchError.value) return;
  if (direction === "previous" && offset.value > 0)
    loadCompanies(offset.value - pageSize);
  if (direction === "next" && hasMore.value && offset.value < maximumOffset)
    loadCompanies(offset.value + pageSize);
}

function retrySearch() {
  loadCompanies(requestedOffset);
}

defineExpose({ focus });
</script>

<template>
  <SearchSelect
    ref="searchSelect"
    v-model="selectedOption"
    v-model:query="query"
    :options="options"
    label="Company"
    search-label="Search companies"
    placeholder="Select a company"
    search-placeholder="Type a company name"
    :search-max-length="200"
    loading-text="Searching companies…"
    empty-text="No companies found. Try a different name or create a company first."
    :disabled="disabled"
    :is-loading="isLoading"
    :error-message="errorMessage"
    :search-error="searchError ? 'Company search is unavailable. Retry or change your search.' : ''"
    :has-previous="offset > 0"
    :has-next="hasMore && offset < maximumOffset"
    :pagination-message="hasMore && offset >= maximumOffset ? 'Narrow your search to find more companies.' : ''"
    @previous="changePage('previous')"
    @next="changePage('next')"
    @retry="retrySearch"
  />
</template>
