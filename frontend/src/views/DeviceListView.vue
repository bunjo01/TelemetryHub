<script setup>
import { computed, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { devicePageSize } from "../api/devices.api.js";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseInput from "../components/ui/BaseInput.vue";
import BaseSelect from "../components/ui/BaseSelect.vue";
import DeviceFormDialog from "../features/devices/components/DeviceFormDialog.vue";
import DeviceList from "../features/devices/components/DeviceList.vue";
import {
  createDeviceListQuery,
  deviceSearchMaxLength,
  readDeviceListQuery,
} from "../features/devices/device-list-query.js";
import { useDeviceList } from "../features/devices/useDeviceList.js";
import { useAuthStore } from "../stores/auth.js";
import { useNotificationStore } from "../stores/notifications.js";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const notifications = useNotificationStore();
const isOwner = computed(() => auth.user?.role === "company_owner");
const isDeviceFormOpen = ref(false);

const query = computed(() => readDeviceListQuery(route.query));
const listQuery = computed(() => createDeviceListQuery(query.value));
const search = ref(query.value.search);
const isSearchPending = ref(false);
const isRecoveringPage = ref(false);
let recoveryTarget = null;
const statusOptions = [
  { value: "active", label: "Active" },
  { value: "inactive", label: "Inactive" },
  { value: "all", label: "All" },
];

const { devices, hasMore, isLoading, error, refresh } = useDeviceList(query);

const isBusy = computed(
  () => isLoading.value || isSearchPending.value || isRecoveringPage.value,
);
const hasPrevious = computed(() => query.value.offset > 0);
const hasNext = computed(
  () =>
    hasMore.value && Number.isSafeInteger(query.value.offset + devicePageSize),
);

const status = computed({
  get: () => query.value.status,
  set(value) {
    stopSearch();
    router.push({
      name: "devices",
      query: createDeviceListQuery({
        search: search.value.trim(),
        status: value,
        offset: 0,
      }),
    });
  },
});

const errorMessage = computed(() => {
  if (error.value?.status === 403) {
    return "Device access is unavailable for your account or company.";
  }

  return error.value?.message ?? "";
});

const emptyMessage = computed(() => {
  if (query.value.offset > 0) {
    return "There are no devices on this page. Go back to the previous page.";
  }

  if (query.value.search) {
    return "No devices match your search. Try another name or status.";
  }

  if (query.value.status === "all") {
    return "Your company has no devices yet.";
  }

  return `There are no ${query.value.status} devices. Try another status.`;
});

let searchTimer;

async function handleDeviceCreated(device) {
  const returnQuery = { ...listQuery.value };
  isDeviceFormOpen.value = false;

  const failure = await router.push({
    name: "device-details",
    params: { id: device.id },
    query: returnQuery,
  });

  if (
    failure ||
    route.name !== "device-details" ||
    route.params.id !== device.id
  ) {
    return;
  }

  notifications.show({
    key: "device-create",
    variant: "success",
    message: `${device.name} was created successfully.`,
  });
}

function stopSearch() {
  clearTimeout(searchTimer);
  isSearchPending.value = false;
}

function scheduleSearch() {
  stopSearch();
  isSearchPending.value = true;
  searchTimer = setTimeout(applySearch, 250);
}

function applySearch() {
  stopSearch();
  router.replace({
    name: "devices",
    query: createDeviceListQuery({
      ...query.value,
      search: search.value.trim(),
      offset: 0,
    }),
  });
}

function changePage(direction) {
  if (isBusy.value || error.value) return;
  if (direction === "previous" && !hasPrevious.value) return;
  if (direction === "next" && !hasNext.value) return;

  const offset =
    direction === "previous"
      ? Math.max(0, query.value.offset - devicePageSize)
      : query.value.offset + devicePageSize;

  router.push({
    name: "devices",
    query: createDeviceListQuery({ ...query.value, offset }),
  });
}

watch(
  () => route.query,
  (currentQuery) => {
    stopSearch();
    search.value = query.value.search;

    if (
      recoveryTarget &&
      (query.value.search !== recoveryTarget.search ||
        query.value.status !== recoveryTarget.status ||
        query.value.offset !== recoveryTarget.offset)
    ) {
      recoveryTarget = null;
    }

    const normalized = listQuery.value;
    const keys = Object.keys(currentQuery);
    const isNormalized =
      keys.length === Object.keys(normalized).length &&
      keys.every((key) => currentQuery[key] === normalized[key]);

    if (!isNormalized) {
      router.replace({
        name: "devices",
        query: normalized,
      });
    }
  },
  { immediate: true },
);

watch([isLoading, isSearchPending, isRecoveringPage], async () => {
  if (
    isLoading.value ||
    isSearchPending.value ||
    isRecoveringPage.value ||
    !auth.token ||
    route.name !== "devices" ||
    search.value.trim() !== query.value.search
  ) {
    return;
  }

  if (error.value || devices.value.length || query.value.offset === 0) {
    recoveryTarget = null;
    return;
  }

  const isPreviousRecoveryPage =
    recoveryTarget &&
    query.value.search === recoveryTarget.search &&
    query.value.status === recoveryTarget.status &&
    query.value.offset === recoveryTarget.offset;

  const offset = isPreviousRecoveryPage
    ? 0
    : Math.max(0, query.value.offset - devicePageSize);

  recoveryTarget = { ...query.value, offset };
  isRecoveringPage.value = true;

  try {
    await router.replace({
      name: "devices",
      query: createDeviceListQuery(recoveryTarget),
    });
  } finally {
    isRecoveringPage.value = false;
  }
});

watch(error, async (failure) => {
  if (failure?.status !== 401) return;

  auth.logout();
  await router.replace({
    name: "login",
    query: { expired: "1" },
  });
});

onBeforeUnmount(stopSearch);
</script>

<template>
  <main id="main" class="devices-page">
    <header class="devices-page__heading">
      <div class="devices-page__heading-copy">
        <h1 class="devices-page__title" tabindex="-1">Devices</h1>
        <p class="supporting-text devices-page__intro">
          Browse and manage your company's devices.
        </p>
      </div>
      <BaseButton
        v-if="isOwner"
        variant="primary"
        aria-haspopup="dialog"
        :disabled="isBusy || !!error"
        @click="isDeviceFormOpen = true"
      >
        Add device
      </BaseButton>
    </header>

    <form
      class="devices-page__toolbar"
      aria-label="Find devices"
      @submit.prevent="applySearch"
    >
      <div class="devices-page__field">
        <label class="devices-page__label" for="device-search">
          Search devices
        </label>
        <BaseInput
          id="device-search"
          v-model="search"
          type="search"
          placeholder="Search devices by name…"
          autocomplete="off"
          :maxlength="deviceSearchMaxLength"
          @update:model-value="scheduleSearch"
        />
      </div>

      <div class="devices-page__field">
        <label class="devices-page__label" for="device-status"> Status </label>
        <BaseSelect
          id="device-status"
          v-model="status"
          label="Status"
          :options="statusOptions"
        />
      </div>
    </form>

    <p
      class="supporting-text devices-page__announcement"
      role="status"
      aria-atomic="true"
    >
      {{
        isBusy ? "Loading devices…" : error ? "" : `${devices.length} devices shown.`
      }}
    </p>

    <section
      class="devices-page__results"
      aria-label="Device results"
      :aria-busy="isBusy"
    >
      <div v-if="!isBusy && error" class="devices-page__feedback">
        <p class="message message--error devices-page__message" role="alert">
          {{ errorMessage }}
        </p>
        <BaseButton
          v-if="error.status !== 401 && error.status !== 403"
          @click="refresh"
        >
          Retry
        </BaseButton>
      </div>

      <template v-else-if="!isBusy">
        <DeviceList
          v-if="devices.length"
          :devices="devices"
          :list-query="listQuery"
        />

        <p v-else class="supporting-text devices-page__empty">
          {{ emptyMessage }}
        </p>
      </template>
    </section>

    <nav class="devices-page__pagination" aria-label="Device pages">
      <BaseButton
        :disabled="isBusy || !!error || !hasPrevious"
        @click="changePage('previous')"
      >
        Previous
      </BaseButton>
      <BaseButton
        :disabled="isBusy || !!error || !hasNext"
        @click="changePage('next')"
      >
        Next
      </BaseButton>
    </nav>
    <DeviceFormDialog
      v-if="isOwner && isDeviceFormOpen"
      @close="isDeviceFormOpen = false"
      @created="handleDeviceCreated"
    />
  </main>
</template>

<style scoped lang="scss">
.devices-page {
  width: min(1100px, 90%);
  margin: 0 auto;
  padding: clamp(1.5rem, 4svh, 4rem) 0;
}

.devices-page__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 2rem;
}

.devices-page__heading-copy {
  min-width: 0;
}

.devices-page__title {
  margin: 0 0 0.75rem;
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 450;
  letter-spacing: -0.045em;
}

.devices-page__intro {
  margin: 0;
}

.devices-page__toolbar {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 12rem;
  gap: 1rem;
  align-items: end;
}

.devices-page__field {
  display: grid;
  gap: 0.5rem;
  min-width: 0;
}

.devices-page__label {
  font-size: 0.8rem;
  font-weight: 500;
}

.devices-page__announcement {
  min-height: 1.5rem;
  margin: 1.25rem 0;
}

.devices-page__results {
  min-height: 8rem;
}

.devices-page__feedback {
  display: grid;
  justify-items: start;
  gap: 1rem;
}

.devices-page__message {
  margin: 0;
}

.devices-page__empty {
  margin: 0;
  padding: 1.5rem 0;
}

.devices-page__pagination {
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
  margin-top: 1.5rem;
}

@media (max-width: 700px) {
  .devices-page__toolbar {
    grid-template-columns: minmax(0, 1fr);
  }

  .devices-page__pagination {
    justify-content: space-between;
  }
}
</style>
