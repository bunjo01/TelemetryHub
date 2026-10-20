export class ApiError extends Error {
  constructor(message, status = 0) {
    super(message);
    this.status = status;
  }
}

export async function request(path, { token, body, signal } = {}) {
  let response;
  try {
    response = await fetch(`/api${path}`, {
      method: body === undefined ? "GET" : "POST",
      headers: {
        ...(body === undefined ? {} : { "Content-Type": "application/json" }),
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: AbortSignal.any([
        signal ?? new AbortController().signal,
        AbortSignal.timeout(15000),
      ]),
      cache: "no-store",
    });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new ApiError(
      body === undefined
        ? "Unable to reach the server. Please try again."
        : "No response received. Your request may have completed; check before trying again.",
    );
  }
  if (!response.ok) {
    const messages = {
      401: "Your session has expired. Please sign in again.",
      403: "You do not have permission to do this.",
      422: "Please check your details and try again.",
      503: "Service temporarily unavailable. Please try again shortly.",
    };
    throw new ApiError(
      messages[response.status] ??
        "The request could not be completed. Please try again later.",
      response.status,
    );
  }
  try {
    return await response.json();
  } catch {
    throw new ApiError("The server returned an unexpected response.");
  }
}

export function invalidResponse() {
  return new ApiError("The server returned an unexpected response.");
}
