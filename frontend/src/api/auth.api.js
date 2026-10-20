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
  if (
    data.role === "company_owner" &&
    (typeof data.company_id !== "string" ||
      !/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
        data.company_id,
      ))
  )
    throw invalidResponse();
  return {
    email: data.email,
    role: data.role,
    ...(data.role === "company_owner" ? { companyId: data.company_id } : {}),
  };
}
