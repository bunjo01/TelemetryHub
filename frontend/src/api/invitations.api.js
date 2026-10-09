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
  return readCreatedInvitation(data);
}

export async function inviteMember(companyId, email, token, signal) {
  let data;
  try {
    data = await request(
      `/companies/${encodeURIComponent(companyId)}/member-invitations`,
      { token, body: { email: email.trim().toLowerCase() }, signal },
    );
  } catch (error) {
    if (error.status === 409)
      throw new ApiError(
        "This email already has an account or a pending invitation. Check the email before trying again.",
        409,
      );
    if (error.status === 404)
      throw new ApiError(
        "Your company is no longer available. Contact your administrator.",
        404,
      );
    throw error;
  }
  return readCreatedInvitation(data);
}

function readCreatedInvitation(data) {
  if (
    typeof data?.token !== "string" ||
    !/^[A-Za-z0-9_-]{43}$/.test(data.token) ||
    typeof data.email !== "string" ||
    !Number.isFinite(Date.parse(data.expires_at))
  )
    throw invalidResponse();
  return { email: data.email, token: data.token, expiresAt: data.expires_at };
}

function invitationFailure(error) {
  if (error.status === 400)
    return new ApiError(
      "This invitation is invalid, expired, or already used. Ask for a new invitation.",
      400,
    );
  if (error.status === 409)
    return new ApiError(
      "This invitation can no longer be accepted because the account or company has changed. Try signing in or contact your administrator.",
      409,
    );
  return error;
}

export async function previewInvitation(invitationToken, signal) {
  let data;
  try {
    data = await request("/invitations/preview", {
      body: { token: invitationToken },
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    if (error.status === 0)
      throw new ApiError("Unable to check your invitation. Please try again.");
    throw invitationFailure(error);
  }
  if (
    typeof data?.email !== "string" ||
    !data.email ||
    !Number.isFinite(Date.parse(data.expires_at))
  )
    throw invalidResponse();
  return { email: data.email, expiresAt: data.expires_at };
}

export async function acceptInvitation(invitationToken, password, signal) {
  let data;
  try {
    data = await request("/invitations/accept", {
      body: { token: invitationToken, password },
      signal,
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    if (error.status === 0)
      throw new ApiError(
        "No confirmation received. Your account may have been created; try signing in before submitting again.",
      );
    throw invitationFailure(error);
  }
  if (
    typeof data?.email !== "string" ||
    !data.email ||
    !["company_owner", "member"].includes(data.role)
  )
    throw new ApiError(
      "The server returned an unexpected response. Your account may have been created; try signing in before submitting again.",
    );
  return { email: data.email, role: data.role };
}
