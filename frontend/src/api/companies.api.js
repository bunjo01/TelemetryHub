import { invalidResponse, request } from "./client.js";

export async function createCompany(name, token, signal) {
  const data = await request("/companies", { token, body: { name }, signal });
  if (typeof data?.name !== "string" || !data.name) throw invalidResponse();
  return { name: data.name };
}

export async function searchCompanies(query, offset, token, signal) {
  const params = new URLSearchParams({
    q: query.trim(),
    offset: String(offset),
    limit: "20",
  });
  const data = await request(`/companies?${params}`, { token, signal });
  if (
    !Array.isArray(data?.items) ||
    data.items.length > 20 ||
    typeof data.has_more !== "boolean" ||
    data.items.some(
      (item) =>
        typeof item?.id !== "string" ||
        !/^[0-9a-f-]{36}$/i.test(item.id) ||
        typeof item.name !== "string" ||
        !item.name,
    )
  )
    throw invalidResponse();
  return {
    items: data.items.map(({ id, name }) => ({ id, name })),
    hasMore: data.has_more,
  };
}
