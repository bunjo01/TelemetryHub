import { invalidResponse, request } from "./client.js";

export async function createCompany(name, token, signal) {
  const data = await request("/companies", { token, body: { name }, signal });
  if (typeof data?.name !== "string" || !data.name) throw invalidResponse();
  return { name: data.name };
}
