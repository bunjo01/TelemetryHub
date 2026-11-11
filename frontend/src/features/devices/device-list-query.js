export const deviceSearchMaxLength = 100;

export function readDeviceListQuery(query) {
  const search =
    typeof query.search === "string"
      ? query.search.trim().slice(0, deviceSearchMaxLength)
      : "";

  const status =
    typeof query.status === "string" &&
    ["active", "inactive", "all"].includes(query.status)
      ? query.status
      : "active";

  const requestedOffset =
    typeof query.offset === "string" && /^\d+$/.test(query.offset)
      ? Number(query.offset)
      : 0;

  const offset = Number.isSafeInteger(requestedOffset) ? requestedOffset : 0;

  return { search, status, offset };
}

export function createDeviceListQuery({ search, status, offset }) {
  return {
    ...(search ? { search } : {}),
    ...(status !== "active" ? { status } : {}),
    ...(offset > 0 ? { offset: String(offset) } : {}),
  };
}
