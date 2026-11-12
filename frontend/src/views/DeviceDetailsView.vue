<script setup>
import { computed, nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import BaseButton from "../components/ui/BaseButton.vue";
import BaseIconButton from "../components/ui/BaseIconButton.vue";
import InfoTooltip from "../components/ui/InfoTooltip.vue";
import DeviceFormDialog from "../features/devices/components/DeviceFormDialog.vue";
import DeviceStatus from "../features/devices/components/DeviceStatus.vue";
import {
  createDeviceListQuery,
  readDeviceListQuery,
} from "../features/devices/device-list-query.js";
import { deviceTypeLabels } from "../features/devices/device-types.js";
import { useDeviceDetails } from "../features/devices/useDeviceDetails.js";
import { useAuthStore } from "../stores/auth.js";
import { useNotificationStore } from "../stores/notifications.js";

const route = useRoute();
const router = useRouter();
const auth = useAuthStore();
const notifications = useNotificationStore();
const isOwner = computed(() => auth.user?.role === "company_owner");
const isEditOpen = ref(false);

const deviceId = computed(() => route.params.id);
const listQuery = computed(() =>
  createDeviceListQuery(readDeviceListQuery(route.query)),
);
const { device, isLoading, error, refresh } = useDeviceDetails(deviceId);

const isCopying = ref(false);
let isUnmounted = false;

const dateFormatter = new Intl.DateTimeFormat(undefined, {
  dateStyle: "medium",
  timeStyle: "short",
});

const timeZoneMessage = `Your local time zone: ${dateFormatter.resolvedOptions().timeZone}.`;

const errorMessage = computed(() => {
  if (error.value?.status === 404) {
    return "Device not found.";
  }

  if (error.value?.status === 403) {
    return "Device access is unavailable for your account or company.";
  }

  return error.value?.message ?? "";
});

const canRetry = computed(
  () => error.value && ![401, 403, 404].includes(error.value.status),
);

function formatTimestamp(value) {
  return dateFormatter.format(new Date(value));
}

async function handleDeviceUpdated(updatedDevice) {
  if (isUnmounted || updatedDevice.id !== deviceId.value) return;

  device.value = updatedDevice;
  isEditOpen.value = false;
  await nextTick();

  if (isUnmounted || updatedDevice.id !== deviceId.value) return;

  notifications.show({
    key: "device-edit",
    variant: "success",
    message: "Device changes saved.",
  });
}

watch(deviceId, () => {
  isEditOpen.value = false;
});

async function copyDeviceId() {
  if (!device.value || isCopying.value) return;

  const copiedDevice = device.value;
  const origin = document.activeElement;
  isCopying.value = true;
  notifications.remove("device-copy");

  try {
    await navigator.clipboard.writeText(copiedDevice.id);

    if (isUnmounted || device.value !== copiedDevice) return;

    notifications.show({
      key: "device-copy",
      variant: "success",
      message: "Device ID copied.",
      origin,
    });
  } catch {
    if (isUnmounted || device.value !== copiedDevice) return;

    notifications.show({
      key: "device-copy",
      variant: "error",
      message: "Unable to copy the device ID. Select and copy it manually.",
      origin,
    });
  } finally {
    if (!isUnmounted && device.value === copiedDevice) {
      isCopying.value = false;
    }
  }
}

watch(device, () => {
  isCopying.value = false;
  notifications.remove("device-copy");
});

watch(error, async (failure) => {
  if (failure?.status !== 401) return;

  auth.logout();
  await router.replace({
    name: "login",
    query: { expired: "1" },
  });
});

onBeforeUnmount(() => {
  isUnmounted = true;
  notifications.remove("device-copy");
});
</script>

<template>
  <main id="main" class="device-details">
    <RouterLink
      class="device-details__back"
      :to="{ name: 'devices', query: listQuery }"
    >
      <svg
        class="device-details__back-icon"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="1.75"
        aria-hidden="true"
      >
        <path d="m10 5-7 7 7 7M3 12h18" />
      </svg>
      <span class="device-details__back-label">Back to devices</span>
    </RouterLink>

    <header class="device-details__heading">
      <div class="device-details__heading-main">
        <h1 class="device-details__title" tabindex="-1">
          {{ device?.name ?? "Device details" }}
        </h1>
        <DeviceStatus v-if="device" :status="device.status" />
      </div>
      <BaseButton
        v-if="isOwner && device"
        aria-haspopup="dialog"
        @click="isEditOpen = true"
      >
        Edit device
      </BaseButton>
    </header>

    <p
      class="supporting-text device-details__announcement"
      :class="{ 'device-details__announcement--hidden': !isLoading }"
      role="status"
      aria-atomic="true"
    >
      {{
        isLoading ? "Loading device…" : device ? "Device details loaded." : ""
      }}
    </p>

    <section
      class="device-details__content"
      aria-label="Device information"
      :aria-busy="isLoading"
    >
      <div v-if="error" class="device-details__feedback">
        <p class="message message--error device-details__message" role="alert">
          {{ errorMessage }}
        </p>
        <BaseButton v-if="canRetry" @click="refresh"> Retry </BaseButton>
      </div>

      <div v-else-if="device" class="panel device-details__panel">
        <dl class="device-details__metadata">
          <div class="device-details__field device-details__field--wide">
            <dt class="device-details__label">Description</dt>
            <dd class="device-details__value device-details__description">
              {{ device.description || "No description provided." }}
            </dd>
          </div>

          <div class="device-details__field">
            <dt class="device-details__label">Device type</dt>
            <dd class="device-details__value">
              {{ deviceTypeLabels[device.deviceType] }}
            </dd>
          </div>

          <div class="device-details__field">
            <dt class="device-details__label">Device ID</dt>
            <dd class="device-details__value device-details__identifier">
              <span class="device-details__id">{{ device.id }}</span>
              <BaseIconButton
                :label="isCopying ? 'Copying device ID' : 'Copy device ID'"
                :disabled="isCopying"
                @click="copyDeviceId"
              >
                <svg
                  width="18"
                  height="18"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  stroke-width="1.75"
                  aria-hidden="true"
                >
                  <rect x="8" y="8" width="12" height="12" rx="2" />
                  <path
                    d="M16 8V4a2 2 0 0 0-2-2H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h4"
                  />
                </svg>
              </BaseIconButton>
            </dd>
          </div>

          <div class="device-details__field">
            <dt class="device-details__label">Created</dt>
            <dd class="device-details__value device-details__timestamp">
              <time :datetime="device.createdAt">
                {{ formatTimestamp(device.createdAt) }}
              </time>
              <InfoTooltip label="Created time zone" :text="timeZoneMessage" />
            </dd>
          </div>

          <div class="device-details__field">
            <dt class="device-details__label">Last updated</dt>
            <dd class="device-details__value device-details__timestamp">
              <time :datetime="device.updatedAt">
                {{ formatTimestamp(device.updatedAt) }}
              </time>
              <InfoTooltip
                label="Last updated time zone"
                :text="timeZoneMessage"
              />
            </dd>
          </div>
        </dl>
      </div>
    </section>
    <DeviceFormDialog
      v-if="isOwner && device && isEditOpen"
      :key="device.id"
      mode="edit"
      :device="device"
      @close="isEditOpen = false"
      @updated="handleDeviceUpdated"
    />
  </main>
</template>

<style scoped lang="scss">
.device-details {
  width: min(1100px, 90%);
  margin: 0 auto;
  padding: clamp(1.5rem, 4svh, 4rem) 0;
}

.device-details__back {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  min-height: 2.75rem;
  margin-bottom: 1.5rem;
  color: var(--accent);
  text-decoration: none;
}

.device-details__back:hover .device-details__back-label,
.device-details__back:focus-visible .device-details__back-label {
  text-decoration: underline;
  text-underline-offset: 0.2em;
}

.device-details__back-icon {
  flex-shrink: 0;
}

.device-details__back:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 4px;
}

.device-details__heading {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1rem;
  margin-bottom: 1.5rem;
}

.device-details__heading-main {
  display: flex;
  flex: 1 1 20rem;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1rem;
  min-width: 0;
}

.device-details__title {
  min-width: 0;
  margin: 0;
  font-size: clamp(2rem, 4vw, 3rem);
  font-weight: 450;
  letter-spacing: -0.045em;
  overflow-wrap: anywhere;
}

.device-details__announcement {
  min-height: 1.5rem;
  margin: 0 0 1rem;
}

.device-details__announcement--hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  min-height: 0;
  margin: -1px;
  padding: 0;
  overflow: hidden;
  clip-path: inset(50%);
  white-space: nowrap;
}

.device-details__content {
  min-height: 8rem;
}

.device-details__feedback {
  display: grid;
  justify-items: start;
  gap: 1rem;
}

.device-details__message {
  margin: 0;
}

.device-details__panel {
  padding: 2rem;
}

.device-details__metadata {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 2rem;
  margin: 0;
}

.device-details__field {
  min-width: 0;
}

.device-details__field--wide {
  grid-column: 1 / -1;
}

.device-details__label {
  margin-bottom: 0.65rem;
  color: var(--muted);
  font-size: 0.8rem;
}

.device-details__value {
  margin: 0;
  line-height: 1.6;
  overflow-wrap: anywhere;
}

.device-details__description {
  white-space: pre-wrap;
}

.device-details__identifier,
.device-details__timestamp {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.device-details__id {
  min-width: 0;
  color: var(--muted);
  font-size: 0.8rem;
}

.device-details__timestamp {
  flex-wrap: wrap;
}

@media (max-width: 700px) {
  .device-details__panel {
    padding: 1.25rem;
  }

  .device-details__metadata {
    grid-template-columns: minmax(0, 1fr);
    gap: 1.5rem;
  }
}
</style>
