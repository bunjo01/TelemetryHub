import { deviceTypeLabels } from "../features/devices/device-types.js";
import { invalidResponse, request } from "./client.js";
import { isUuid } from "./validation.js";

export const devicePageSize = 20;

function isTimestamp(value) {
  return typeof value === "string" && Number.isFinite(Date.parse(value));
}

function parseDevice(data) {
  if (
    !isUuid(data?.id) ||
    !isUuid(data.company_id) ||
    typeof data.name !== "string" ||
    !data.name.trim() ||
    !(data.description === null || typeof data.description === "string") ||
    typeof data.device_type !== "string" ||
    !Object.hasOwn(deviceTypeLabels, data.device_type) ||
    !["active", "inactive"].includes(data.status) ||
    !isTimestamp(data.created_at) ||
    !isTimestamp(data.updated_at)
  ) {
    throw invalidResponse();
  }

  return {
    id: data.id,
    companyId: data.company_id,
    name: data.name,
    description: data.description,
    deviceType: data.device_type,
    status: data.status,
    createdAt: data.created_at,
    updatedAt: data.updated_at,
  };
}

/**
 * Search matches a literal device-name substring.
 * The API provides hasMore, not a total item count.
 */
export async function listDevices(
  { search = "", status = "active", offset = 0 } = {},
  token,
  signal,
) {
  const params = new URLSearchParams({
    status,
    limit: String(devicePageSize),
    offset: String(offset),
  });

  const normalizedSearch = search.trim();
  if (normalizedSearch) params.set("search", normalizedSearch);

  const data = await request(`/devices?${params}`, { token, signal });

  if (
    !Array.isArray(data?.items) ||
    data.items.length > devicePageSize ||
    data.limit !== devicePageSize ||
    data.offset !== offset ||
    typeof data.has_more !== "boolean"
  ) {
    throw invalidResponse();
  }

  return {
    items: data.items.map(parseDevice),
    limit: data.limit,
    offset: data.offset,
    hasMore: data.has_more,
  };
}

export async function getDevice(deviceId, token, signal) {
  const data = await request(`/devices/${encodeURIComponent(deviceId)}`, {
    token,
    signal,
  });

  return parseDevice(data);
}

export async function createDevice(
  { name, deviceType, description = null },
  token,
  signal,
) {
  const data = await request("/devices", {
    method: "POST",
    token,
    signal,
    body: {
      name: name.trim(),
      device_type: deviceType,
      description,
    },
  });

  return parseDevice(data);
}

/**
 * Callers supply only changed fields.
 * Omitted description preserves it; description: null clears it.
 */
export async function updateDevice(deviceId, changes, token, signal) {
  const body = {};

  if (Object.hasOwn(changes, "name")) {
    body.name = changes.name.trim();
  }

  if (Object.hasOwn(changes, "description")) {
    body.description = changes.description;
  }

  const data = await request(`/devices/${encodeURIComponent(deviceId)}`, {
    method: "PATCH",
    token,
    signal,
    body,
  });

  return parseDevice(data);
}

export async function activateDevice(deviceId, token, signal) {
  const data = await request(
    `/devices/${encodeURIComponent(deviceId)}/activate`,
    {
      method: "POST",
      token,
      signal,
    },
  );

  return parseDevice(data);
}

export async function deactivateDevice(deviceId, token, signal) {
  const data = await request(
    `/devices/${encodeURIComponent(deviceId)}/deactivate`,
    {
      method: "POST",
      token,
      signal,
    },
  );

  return parseDevice(data);
}
