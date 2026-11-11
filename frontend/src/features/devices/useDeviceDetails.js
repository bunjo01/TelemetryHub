import { onScopeDispose, ref, watch } from "vue";
import { ApiError } from "../../api/client.js";
import { getDevice } from "../../api/devices.api.js";
import { isUuid } from "../../api/validation.js";
import { useAuthStore } from "../../stores/auth.js";

export function useDeviceDetails(deviceId) {
  const auth = useAuthStore();

  const device = ref(null);
  const isLoading = ref(false);
  const error = ref(null);

  let activeRequest;
  let isDisposed = false;

  async function refresh() {
    activeRequest?.abort();
    activeRequest = undefined;

    device.value = null;
    error.value = null;
    isLoading.value = false;

    if (isDisposed || !auth.token) return;

    if (!isUuid(deviceId.value)) {
      error.value = new ApiError("Device not found.", 404);
      return;
    }

    const controller = new AbortController();
    activeRequest = controller;
    isLoading.value = true;

    try {
      const result = await getDevice(
        deviceId.value,
        auth.token,
        controller.signal,
      );

      if (
        isDisposed ||
        controller.signal.aborted ||
        activeRequest !== controller
      ) {
        return;
      }

      device.value = result;
    } catch (failure) {
      if (
        isDisposed ||
        controller.signal.aborted ||
        activeRequest !== controller
      ) {
        return;
      }

      error.value = failure;
    } finally {
      if (activeRequest === controller) {
        activeRequest = undefined;
        isLoading.value = false;
      }
    }
  }

  watch([() => deviceId.value, () => auth.token], refresh, {
    immediate: true,
    flush: "sync",
  });

  onScopeDispose(() => {
    isDisposed = true;
    activeRequest?.abort();
    activeRequest = undefined;
  });

  return {
    device,
    isLoading,
    error,
    refresh,
  };
}
