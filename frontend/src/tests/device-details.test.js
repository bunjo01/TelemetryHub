import { createPinia, setActivePinia } from "pinia";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { effectScope, nextTick, ref } from "vue";
import { ApiError } from "../api/client.js";
import { getDevice } from "../api/devices.api.js";
import { useDeviceDetails } from "../features/devices/useDeviceDetails.js";
import { useAuthStore } from "../stores/auth.js";

vi.mock("../api/devices.api.js", () => ({
  getDevice: vi.fn(),
}));

const firstId = "92967688-13b8-430d-8f0f-cb038f6c011c";
const secondId = "740e0095-d2d2-497a-95ff-7141e16c420c";

let scopes;
let requests;

beforeEach(() => {
  vi.resetAllMocks();
  setActivePinia(createPinia());
  scopes = [];
  requests = [];

  getDevice.mockImplementation((_id, _token, signal) => {
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

function createDetails(id = firstId, token = "token") {
  const auth = useAuthStore();
  auth.token = token;
  const deviceId = ref(id);
  const scope = effectScope();
  scopes.push(scope);
  const state = scope.run(() => useDeviceDetails(deviceId));

  return { auth, deviceId, scope, state };
}

it("loads immediately and publishes the device", async () => {
  const { state } = createDetails();
  const device = { id: firstId, name: "Freezer sensor" };

  expect(state.isLoading.value).toBe(true);
  expect(state.device.value).toBeNull();
  expect(state.error.value).toBeNull();
  expect(getDevice).toHaveBeenCalledWith(
    firstId,
    "token",
    expect.any(AbortSignal),
  );

  requests[0].resolve(device);
  await nextTick();

  expect(state.device.value).toEqual(device);
  expect(state.isLoading.value).toBe(false);
});

it("clears the previous device when the ID changes", async () => {
  const { deviceId, state } = createDetails();
  requests[0].resolve({ id: firstId });
  await nextTick();

  deviceId.value = secondId;

  expect(state.device.value).toBeNull();
  expect(state.isLoading.value).toBe(true);
  expect(getDevice).toHaveBeenLastCalledWith(
    secondId,
    "token",
    expect.any(AbortSignal),
  );

  requests[1].resolve({ id: secondId });
  await nextTick();
  expect(state.device.value).toEqual({ id: secondId });
});

it("rejects an invalid ID without a request and recovers after navigation", async () => {
  const { deviceId, state } = createDetails("invalid-id");

  expect(getDevice).not.toHaveBeenCalled();
  expect(state.error.value).toMatchObject({
    message: "Device not found.",
    status: 404,
  });
  expect(state.isLoading.value).toBe(false);

  deviceId.value = firstId;

  expect(state.error.value).toBeNull();
  expect(state.isLoading.value).toBe(true);
  requests[0].resolve({ id: firstId });
  await nextTick();
  expect(state.device.value).toEqual({ id: firstId });
});

it.each(["success", "failure"])(
  "ignores an obsolete request's late %s while another device loads",
  async (outcome) => {
    const { deviceId, state } = createDetails();
    deviceId.value = secondId;

    expect(requests[0].signal.aborted).toBe(true);
    if (outcome === "success") requests[0].resolve({ id: firstId });
    else requests[0].reject(new ApiError("Obsolete failure", 503));
    await nextTick();

    expect(state.device.value).toBeNull();
    expect(state.error.value).toBeNull();
    expect(state.isLoading.value).toBe(true);

    requests[1].resolve({ id: secondId });
    await nextTick();
    expect(state.device.value).toEqual({ id: secondId });
    expect(state.isLoading.value).toBe(false);
  },
);

it("keeps the new device when the older request finishes last", async () => {
  const { deviceId, state } = createDetails();
  deviceId.value = secondId;
  requests[1].resolve({ id: secondId });
  await nextTick();
  requests[0].resolve({ id: firstId });
  await nextTick();

  expect(state.device.value).toEqual({ id: secondId });
  expect(state.error.value).toBeNull();
  expect(state.isLoading.value).toBe(false);
});

it.each([401, 403, 404, 503, 0])(
  "exposes a status %s failure to the view and supports retry",
  async (status) => {
    const { state } = createDetails();
    requests[0].reject(new ApiError("Request failed", status));
    await nextTick();

    expect(state.error.value).toMatchObject({
      message: "Request failed",
      status,
    });
    expect(state.device.value).toBeNull();
    expect(state.isLoading.value).toBe(false);

    const retry = state.refresh();
    expect(state.error.value).toBeNull();
    expect(state.isLoading.value).toBe(true);
    requests[1].resolve({ id: firstId });
    await retry;

    expect(state.device.value).toEqual({ id: firstId });
    expect(state.isLoading.value).toBe(false);
  },
);

it("clears loaded data on logout and ignores a pending response", async () => {
  const { auth, state } = createDetails();
  requests[0].resolve({ id: firstId });
  await nextTick();

  auth.logout();
  expect(state.device.value).toBeNull();
  expect(getDevice).toHaveBeenCalledTimes(1);

  auth.token = "new-token";
  auth.logout();
  expect(requests[1].signal.aborted).toBe(true);
  requests[1].resolve({ id: firstId });
  await nextTick();

  expect(state.device.value).toBeNull();
  expect(state.error.value).toBeNull();
  expect(state.isLoading.value).toBe(false);
});

it("waits for authentication and reloads when the token changes", async () => {
  const { auth, state } = createDetails(firstId, "");
  expect(getDevice).not.toHaveBeenCalled();
  expect(state.isLoading.value).toBe(false);

  auth.token = "first-token";
  requests[0].resolve({ id: firstId });
  await nextTick();
  auth.token = "second-token";

  expect(state.device.value).toBeNull();
  expect(getDevice).toHaveBeenLastCalledWith(
    firstId,
    "second-token",
    expect.any(AbortSignal),
  );
});

it("cancels loading when navigation changes to an invalid ID", async () => {
  const { deviceId, state } = createDetails();
  deviceId.value = "invalid-id";

  expect(requests[0].signal.aborted).toBe(true);
  requests[0].resolve({ id: firstId });
  await nextTick();

  expect(getDevice).toHaveBeenCalledTimes(1);
  expect(state.device.value).toBeNull();
  expect(state.error.value.status).toBe(404);
  expect(state.isLoading.value).toBe(false);
});

it("cancels work on disposal and prevents further requests", async () => {
  const { deviceId, scope, state } = createDetails();
  scope.stop();

  expect(requests[0].signal.aborted).toBe(true);
  requests[0].resolve({ id: firstId });
  await nextTick();
  expect(state.device.value).toBeNull();

  deviceId.value = secondId;
  await state.refresh();
  expect(getDevice).toHaveBeenCalledTimes(1);
});
