import { afterEach, expect, it, vi } from "vitest";
import {
  activateDevice,
  createDevice,
  deactivateDevice,
  getDevice,
  listDevices,
  updateDevice,
} from "../api/devices.api.js";

const device = {
  id: "92967688-13b8-430d-8f0f-cb038f6c011c",
  company_id: "740e0095-d2d2-497a-95ff-7141e16c420c",
  name: "Freezer sensor",
  description: null,
  device_type: "temperature_sensor",
  status: "active",
  created_at: "2026-10-24T12:00:00Z",
  updated_at: "2026-10-24T13:00:00Z",
};

const expectedDevice = {
  id: device.id,
  companyId: device.company_id,
  name: device.name,
  description: null,
  deviceType: "temperature_sensor",
  status: "active",
  createdAt: device.created_at,
  updatedAt: device.updated_at,
};

function mockResponse(body, status = 200) {
  const fetchMock = vi.fn().mockResolvedValue(Response.json(body, { status }));

  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => vi.unstubAllGlobals());

it("loads device details and returns only frontend fields", async () => {
  const fetchMock = mockResponse({
    ...device,
    internal: "not retained",
  });

  await expect(getDevice(device.id, "token")).resolves.toEqual(expectedDevice);

  expect(fetchMock).toHaveBeenCalledWith(
    `/api/devices/${device.id}`,
    expect.objectContaining({
      method: "GET",
      headers: { Authorization: "Bearer token" },
    }),
  );
});

it.each([
  ["empty search", {}, { status: "active", limit: "20", offset: "0" }],
  [
    "whitespace search",
    { search: "   " },
    { status: "active", limit: "20", offset: "0" },
  ],
  [
    "filtered next page",
    { search: "  Cold & wet  ", status: "inactive", offset: 20 },
    {
      status: "inactive",
      limit: "20",
      offset: "20",
      search: "Cold & wet",
    },
  ],
  [
    "all statuses",
    { status: "all" },
    { status: "all", limit: "20", offset: "0" },
  ],
])("lists devices with %s", async (_label, query, expectedQuery) => {
  const offset = query.offset ?? 0;
  const fetchMock = mockResponse({
    items: [device],
    limit: 20,
    offset,
    has_more: true,
  });

  await expect(listDevices(query, "token")).resolves.toEqual({
    items: [expectedDevice],
    limit: 20,
    offset,
    hasMore: true,
  });

  const [url] = fetchMock.mock.calls[0];
  const parsedUrl = new URL(url, "http://localhost");

  expect(parsedUrl.pathname).toBe("/api/devices");
  expect(Object.fromEntries(parsedUrl.searchParams)).toEqual(expectedQuery);
});

it("accepts an empty device list", async () => {
  mockResponse({
    items: [],
    limit: 20,
    offset: 0,
    has_more: false,
  });

  await expect(listDevices({}, "token")).resolves.toEqual({
    items: [],
    limit: 20,
    offset: 0,
    hasMore: false,
  });
});

it.each([
  ["invalid device ID", { id: "invalid" }],
  ["missing company ID", { company_id: undefined }],
  ["blank name", { name: "   " }],
  ["invalid description", { description: 42 }],
  ["unknown type", { device_type: "unknown_sensor" }],
  ["inherited property as type", { device_type: "toString" }],
  ["unknown status", { status: "online" }],
  ["invalid creation date", { created_at: "not a date" }],
  ["non-string update date", { updated_at: 123 }],
])("rejects details with %s", async (_label, overrides) => {
  mockResponse({ ...device, ...overrides });

  await expect(getDevice(device.id, "token")).rejects.toThrow(
    "unexpected response",
  );
});

it("rejects a null details response", async () => {
  mockResponse(null);

  await expect(getDevice(device.id, "token")).rejects.toThrow(
    "unexpected response",
  );
});

it.each([
  ["missing items", { items: undefined }],
  ["too many items", { items: Array(21).fill(device) }],
  ["invalid device item", { items: [null] }],
  ["unexpected page size", { limit: 100 }],
  ["unexpected offset", { offset: 20 }],
  ["invalid pagination flag", { has_more: "false" }],
])("rejects a list with %s", async (_label, overrides) => {
  mockResponse({
    items: [device],
    limit: 20,
    offset: 0,
    has_more: false,
    ...overrides,
  });

  await expect(listDevices({}, "token")).rejects.toThrow("unexpected response");
});

it.each([401, 403, 404, 503])(
  "preserves HTTP status %s for the details page",
  async (status) => {
    mockResponse({ detail: "Internal backend details" }, status);

    await expect(getDevice(device.id, "token")).rejects.toMatchObject({
      status,
    });
  },
);

it.each([
  ["omitted", undefined, null],
  ["provided", "Main warehouse freezer", "Main warehouse freezer"],
])(
  "creates a device with %s description",
  async (_label, description, expectedDescription) => {
    const fetchMock = mockResponse(
      { ...device, description: expectedDescription },
      201,
    );

    await expect(
      createDevice(
        {
          name: "  Freezer sensor  ",
          deviceType: "temperature_sensor",
          ...(description === undefined ? {} : { description }),
        },
        "token",
      ),
    ).resolves.toEqual({
      ...expectedDevice,
      description: expectedDescription,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);

    const [url, options] = fetchMock.mock.calls[0];

    expect(url).toBe("/api/devices");
    expect(options.method).toBe("POST");
    expect(options.headers).toEqual({
      Authorization: "Bearer token",
      "Content-Type": "application/json",
    });
    expect(JSON.parse(options.body)).toEqual({
      name: "Freezer sensor",
      device_type: "temperature_sensor",
      description: expectedDescription,
    });
  },
);

it.each([
  ["name only", { name: "  New name  " }, { name: "New name" }],
  [
    "description only",
    { description: "Updated description" },
    { description: "Updated description" },
  ],
  ["clear description", { description: null }, { description: null }],
  [
    "both editable fields",
    { name: "New name", description: "Updated description" },
    { name: "New name", description: "Updated description" },
  ],
])("updates %s without sending other fields", async (_label, changes, body) => {
  const fetchMock = mockResponse({
    ...device,
    ...body,
    updated_at: "2026-10-24T14:00:00Z",
  });

  await expect(updateDevice(device.id, changes, "token")).resolves.toEqual({
    ...expectedDevice,
    ...body,
    updatedAt: "2026-10-24T14:00:00Z",
  });

  expect(fetchMock).toHaveBeenCalledTimes(1);

  const [url, options] = fetchMock.mock.calls[0];

  expect(url).toBe(`/api/devices/${device.id}`);
  expect(options.method).toBe("PATCH");
  expect(options.headers).toEqual({
    Authorization: "Bearer token",
    "Content-Type": "application/json",
  });
  expect(JSON.parse(options.body)).toEqual(body);
});

it.each([
  ["activate", activateDevice, "active"],
  ["deactivate", deactivateDevice, "inactive"],
])("sends a bodyless request to %s", async (action, operation, status) => {
  const fetchMock = mockResponse({
    ...device,
    status,
    updated_at: "2026-10-24T14:00:00Z",
  });

  await expect(operation(device.id, "token")).resolves.toEqual({
    ...expectedDevice,
    status,
    updatedAt: "2026-10-24T14:00:00Z",
  });

  expect(fetchMock).toHaveBeenCalledTimes(1);
  expect(fetchMock).toHaveBeenCalledWith(
    `/api/devices/${device.id}/${action}`,
    expect.objectContaining({
      method: "POST",
      body: undefined,
      headers: { Authorization: "Bearer token" },
    }),
  );
});

it.each([
  [
    "create",
    () =>
      createDevice(
        { name: "Freezer sensor", deviceType: "temperature_sensor" },
        "token",
      ),
  ],
  ["update", () => updateDevice(device.id, { name: "New name" }, "token")],
  ["activate", () => activateDevice(device.id, "token")],
  ["deactivate", () => deactivateDevice(device.id, "token")],
])("rejects malformed %s responses", async (_label, operation) => {
  mockResponse({ id: device.id });

  await expect(operation()).rejects.toThrow("unexpected response");
});
