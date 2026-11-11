import { onScopeDispose, ref, watch } from "vue";
import { listDevices } from "../../api/devices.api.js";
import { useAuthStore } from "../../stores/auth.js";

export function useDeviceList(query) {
  const auth = useAuthStore();

  const devices = ref([]);
  const hasMore = ref(false);
  const isLoading = ref(false);
  const error = ref(null);

  let activeRequest;
  let isDisposed = false;

  async function refresh() {
    activeRequest?.abort();
    activeRequest = undefined;

    devices.value = [];
    hasMore.value = false;
    error.value = null;
    isLoading.value = false;

    if (isDisposed || !auth.token) return;

    const controller = new AbortController();
    activeRequest = controller;
    isLoading.value = true;

    try {
      const result = await listDevices(
        query.value,
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

      devices.value = result.items;
      hasMore.value = result.hasMore;
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

  watch(
    [
      () => query.value.search,
      () => query.value.status,
      () => query.value.offset,
      () => auth.token,
    ],
    refresh,
    { immediate: true, flush: "sync" },
  );

  onScopeDispose(() => {
    isDisposed = true;
    activeRequest?.abort();
    activeRequest = undefined;
  });

  return {
    devices,
    hasMore,
    isLoading,
    error,
    refresh,
  };
}
