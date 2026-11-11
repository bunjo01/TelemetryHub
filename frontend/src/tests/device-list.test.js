import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref } from "vue";
import { listDevices } from "../api/devices.api.js";
import { useDeviceList } from "../features/devices/useDeviceList.js";
import { useAuthStore } from "../stores/auth.js";

vi.mock("../api/devices.api.js", () => ({
  listDevices: vi.fn(),
}));

let scopes;
let requests;

beforeEach(() => {
  vi.resetAllMocks();
  setActivePinia(createPinia());
  scopes = [];
  requests = [];

  listDevices.mockImplementation((_query, _token, signal) => {
    let resolve;
    let reject;

    const promise = new Promise((resolvePromise, rejectPromise) => {
      resolve = resolvePromise;
      reject = rejectPromise;
    });

    requests.push({ resolve, reject, signal });
    return promise;
  });
});

afterEach(() => {
  for (const scope of scopes) scope.stop();
});

function createList(token = "token") {
  const auth = useAuthStore();
  auth.token = token;

  const query = ref({
    search: "",
    status: "active",
    offset: 0,
  });

  const scope = effectScope();
  scopes.push(scope);

  const state = scope.run(() => useDeviceList(query));

  return { auth, query, scope, state };
}

it("loads immediately and publishes results and pagination", async () => {
  const { query, state } = createList();

  expect(state.isLoading.value).toBe(true);
  expect(state.error.value).toBeNull();
  expect(listDevices).toHaveBeenCalledWith(
    query.value,
    "token",
    expect.any(AbortSignal),
  );

  requests[0].resolve({
    items: [{ id: "first-device" }],
    hasMore: true,
  });

  await nextTick();

  expect(state.devices.value).toEqual([{ id: "first-device" }]);
  expect(state.hasMore.value).toBe(true);
  expect(state.isLoading.value).toBe(false);
});

it.each([
  ["search", "freezer"],
  ["status", "inactive"],
  ["offset", 20],
])("reloads when %s changes", async (field, value) => {
  const { query, state } = createList();

  requests[0].resolve({
    items: [{ id: "old-device" }],
    hasMore: true,
  });
  await nextTick();

  query.value = { ...query.value, [field]: value };

  expect(listDevices).toHaveBeenCalledTimes(2);
  expect(listDevices).toHaveBeenLastCalledWith(
    query.value,
    "token",
    expect.any(AbortSignal),
  );
  expect(state.devices.value).toEqual([]);
  expect(state.hasMore.value).toBe(false);
  expect(state.isLoading.value).toBe(true);
});

it.each(["success", "failure"])(
  "ignores an obsolete request's late %s",
  async (outcome) => {
    const { query, state } = createList();

    query.value = { ...query.value, status: "inactive" };

    expect(requests[0].signal.aborted).toBe(true);

    if (outcome === "success") {
      requests[0].resolve({
        items: [{ id: "obsolete-device" }],
        hasMore: true,
      });
    } else {
      requests[0].reject(new Error("Obsolete failure"));
    }

    await nextTick();

    expect(state.devices.value).toEqual([]);
    expect(state.error.value).toBeNull();
    expect(state.isLoading.value).toBe(true);

    requests[1].resolve({
      items: [{ id: "current-device" }],
      hasMore: false,
    });

    await nextTick();

    expect(state.devices.value).toEqual([{ id: "current-device" }]);
    expect(state.isLoading.value).toBe(false);
  },
);

it("exposes a failure and allows a successful retry", async () => {
  const { state } = createList();
  const failure = Object.assign(new Error("Service unavailable"), {
    status: 503,
  });

  requests[0].reject(failure);
  await nextTick();

  expect(state.error.value).toMatchObject({
    message: "Service unavailable",
    status: 503,
  });
  expect(state.isLoading.value).toBe(false);

  const retry = state.refresh();

  expect(state.error.value).toBeNull();
  expect(state.isLoading.value).toBe(true);
  expect(listDevices).toHaveBeenCalledTimes(2);

  requests[1].resolve({ items: [], hasMore: false });
  await retry;

  expect(state.devices.value).toEqual([]);
  expect(state.error.value).toBeNull();
  expect(state.isLoading.value).toBe(false);
});

it("clears data on logout and ignores a pending response", async () => {
  const { auth, state } = createList();

  requests[0].resolve({
    items: [{ id: "private-device" }],
    hasMore: true,
  });
  await nextTick();

  const pending = state.refresh();
  auth.logout();

  expect(requests[1].signal.aborted).toBe(true);
  expect(state.devices.value).toEqual([]);
  expect(state.hasMore.value).toBe(false);
  expect(state.error.value).toBeNull();
  expect(state.isLoading.value).toBe(false);
  expect(listDevices).toHaveBeenCalledTimes(2);

  requests[1].resolve({
    items: [{ id: "private-device" }],
    hasMore: true,
  });
  await pending;

  expect(state.devices.value).toEqual([]);
  expect(state.hasMore.value).toBe(false);
});

it("waits for a token before requesting devices", () => {
  const { auth, state } = createList("");

  expect(listDevices).not.toHaveBeenCalled();
  expect(state.isLoading.value).toBe(false);

  auth.token = "new-token";

  expect(listDevices).toHaveBeenCalledTimes(1);
  expect(listDevices).toHaveBeenLastCalledWith(
    { search: "", status: "active", offset: 0 },
    "new-token",
    expect.any(AbortSignal),
  );
});

it("cancels work on disposal and stops watching query changes", async () => {
  const { query, scope, state } = createList();

  scope.stop();

  expect(requests[0].signal.aborted).toBe(true);

  requests[0].resolve({
    items: [{ id: "late-device" }],
    hasMore: true,
  });
  await nextTick();

  expect(state.devices.value).toEqual([]);
  expect(state.hasMore.value).toBe(false);

  query.value = { ...query.value, search: "freezer" };

  expect(listDevices).toHaveBeenCalledTimes(1);
});
