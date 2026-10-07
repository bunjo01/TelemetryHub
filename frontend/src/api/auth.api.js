import { ApiError, invalidResponse, request } from "./client.js";

export const roleLabels = {
  system_admin: "System administrator",
  company_owner: "Company owner",
  member: "Member",
};

export async function login(email, password, signal) {
  let data;
  try {
    data = await request("/auth/login", { body: { email, password }, signal });
  } catch (error) {
    if (error.status === 401)
      throw new ApiError("Invalid email or password.", 401);
    throw error;
  }
  if (
    typeof data?.access_token !== "string" ||
    !data.access_token ||
    data.token_type !== "bearer"
  )
    throw invalidResponse();
  return data.access_token;
}

export async function getProfile(token, signal) {
  const data = await request("/auth/me", { token, signal });
  if (
    typeof data?.email !== "string" ||
    !data.email ||
    !Object.hasOwn(roleLabels, data.role)
  )
    throw invalidResponse();
  // Only retain the fields this interface needs; IDs and status are not displayed.
  return { email: data.email, role: data.role };
}
