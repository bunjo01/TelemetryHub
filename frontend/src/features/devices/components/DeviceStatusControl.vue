<script setup>
import { nextTick, onBeforeUnmount, ref, watch } from "vue";
import { useRouter } from "vue-router";
import {
  activateDevice,
  deactivateDevice,
  getDevice,
} from "../../../api/devices.api.js";
import BaseButton from "../../../components/ui/BaseButton.vue";
import BaseDialog from "../../../components/ui/BaseDialog.vue";
import BaseSwitch from "../../../components/ui/BaseSwitch.vue";
import { useAuthStore } from "../../../stores/auth.js";
import { useNotificationStore } from "../../../stores/notifications.js";

const props = defineProps({
  device: { type: Object, required: true },
  disabled: { type: Boolean, default: false },
});
const emit = defineEmits(["updated", "busy"]);
const auth = useAuthStore();
const router = useRouter();
const notifications = useNotificationStore();
const isConfirmOpen = ref(false);
const isPending = ref(false);
const needsRefresh = ref(false);
const error = ref("");
let request;
let isDisposed = false;

watch(
  [isPending, needsRefresh],
  () => {
    emit("busy", isPending.value || needsRefresh.value);
  },
  { flush: "sync" },
);

function requestStatus(active) {
  if (
    props.disabled ||
    isPending.value ||
    needsRefresh.value ||
    auth.user?.role !== "company_owner"
  )
    return;
  if (active === (props.device.status === "active")) return;
  error.value = "";
  if (active) changeStatus(true);
  else isConfirmOpen.value = true;
}

async function publish(device, message, variant) {
  isConfirmOpen.value = false;
  await nextTick();
  if (isDisposed || request?.signal.aborted) return;
  notifications.show({ key: `device-status-${device.id}`, message, variant });
  emit("updated", device);
}

async function handleUnauthorized(failure) {
  if (failure.status !== 401) return false;
  auth.logout();
  await router.replace({ name: "login", query: { expired: "1" } });
  return true;
}

async function reconcile(controller) {
  try {
    const device = await getDevice(
      props.device.id,
      auth.token,
      controller.signal,
    );
    if (isDisposed || controller.signal.aborted) return;
    needsRefresh.value = false;
    error.value = "";
    await publish(
      device,
      "Device status refreshed. Check its current state before trying again.",
      "info",
    );
  } catch (failure) {
    if (isDisposed || controller.signal.aborted) return;
    if (await handleUnauthorized(failure)) return;
    error.value =
      "The current device status could not be verified. Refresh its status before making more changes.";
  }
}

async function refreshStatus() {
  if (isPending.value || !needsRefresh.value) return;
  const controller = new AbortController();
  request = controller;
  isPending.value = true;
  try {
    await reconcile(controller);
  } finally {
    if (!isDisposed) isPending.value = false;
    if (request === controller) request = undefined;
  }
}

async function changeStatus(active) {
  if (
    props.disabled ||
    isPending.value ||
    needsRefresh.value ||
    auth.user?.role !== "company_owner"
  )
    return;
  const controller = new AbortController();
  request = controller;
  isPending.value = true;
  error.value = "";
  try {
    const change = active ? activateDevice : deactivateDevice;
    const device = await change(props.device.id, auth.token, controller.signal);
    if (isDisposed || controller.signal.aborted) return;
    await publish(
      device,
      `${device.name} was ${active ? "activated" : "deactivated"}.`,
      "success",
    );
  } catch (failure) {
    if (isDisposed || controller.signal.aborted) return;
    if (await handleUnauthorized(failure)) return;
    if (!failure.status || failure.status >= 500) {
      needsRefresh.value = true;
      isConfirmOpen.value = false;
      await reconcile(controller);
    } else {
      error.value =
        failure.status === 404 ? "Device not found." : failure.message;
    }
  } finally {
    if (!isDisposed) isPending.value = false;
    if (request === controller) request = undefined;
  }
}

watch(
  () => auth.token,
  () => {
    request?.abort();
    isConfirmOpen.value = false;
  },
  { flush: "sync" },
);

onBeforeUnmount(() => {
  isDisposed = true;
  request?.abort();
  emit("busy", false);
});
</script>

<template>
  <div class="device-status-control">
    <BaseSwitch
      :checked="device.status === 'active'"
      :label="`${device.name}: device active`"
      on-label="Active"
      off-label="Inactive"
      :pending="isPending"
      :disabled="disabled || needsRefresh"
      @change="requestStatus"
    />
    <p
      v-if="error && !isConfirmOpen"
      class="message message--error device-status-control__message"
      role="alert"
    >
      {{ error }}
    </p>
    <BaseButton
      v-if="needsRefresh"
      :disabled="isPending"
      @click="refreshStatus"
    >
      Refresh status
    </BaseButton>
    <BaseDialog
      v-if="isConfirmOpen"
      v-slot="{ close }"
      :title="`Deactivate “${device.name}”?`"
      :close-disabled="isPending"
      @close="isConfirmOpen = false"
    >
      <div class="device-status-control__confirmation" :aria-busy="isPending">
        <p class="supporting-text device-status-control__message">
          This device will be marked inactive and hidden from the default Active
          devices list. Its details will remain available, and you can
          reactivate it anytime.
        </p>
        <p
          v-if="error"
          class="message message--error device-status-control__message"
          role="alert"
        >
          {{ error }}
        </p>
        <div class="device-status-control__actions">
          <BaseButton :disabled="isPending" @click="close">Cancel</BaseButton>
          <BaseButton :disabled="isPending" @click="changeStatus(false)">
            {{ isPending ? "Deactivating…" : "Deactivate device" }}
          </BaseButton>
        </div>
      </div>
    </BaseDialog>
  </div>
</template>

<style scoped lang="scss">
.device-status-control {
  display: grid;
  justify-items: start;
  gap: 0.75rem;
  min-width: 0;
}

.device-status-control__message {
  margin: 0;
  overflow-wrap: anywhere;
}

.device-status-control__confirmation {
  display: grid;
  gap: 1.25rem;
}

.device-status-control__actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 0.75rem;
}
</style>
