import { ApiError, invalidResponse, request } from "./client.js";

export async function inviteOwner(companyId, email, token, signal) {
  let data;
  try {
    data = await request(
      `/companies/${encodeURIComponent(companyId)}/owner-invitations`,
      { token, body: { email: email.trim().toLowerCase() }, signal },
    );
  } catch (error) {
    if (error.status === 409)
      throw new ApiError(
        "This company or email already has an owner, account, or pending invitation. Check the details before trying again.",
        409,
      );
    if (error.status === 404)
      throw new ApiError(
        "This company is no longer available. Choose another company.",
        404,
      );
    throw error;
  }
  if (
    typeof data?.token !== "string" ||
    !/^[A-Za-z0-9_-]{43}$/.test(data.token) ||
    typeof data.email !== "string" ||
    !Number.isFinite(Date.parse(data.expires_at))
  )
    throw invalidResponse();
  return { email: data.email, token: data.token, expiresAt: data.expires_at };
}
