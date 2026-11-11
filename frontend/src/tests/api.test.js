import { afterEach, expect, it, vi } from "vitest";
import { getProfile, login } from "../api/auth.api.js";
import { request } from "../api/client.js";

afterEach(() => vi.unstubAllGlobals());

it.each([
  { label: "default GET", options: {}, method: "GET" },
  {
    label: "default POST with JSON",
    options: { body: { name: "Sensor" } },
    method: "POST",
  },
  {
    label: "explicit PATCH",
    options: { method: "PATCH", body: { name: "Renamed sensor" } },
    method: "PATCH",
  },
  {
    label: "bodyless POST",
    options: { method: "POST" },
    method: "POST",
  },
  {
    label: "lowercase method",
    options: { method: "patch", body: { description: null } },
    method: "PATCH",
  },
])(
  "sends $label with the correct method and body",
  async ({ options, method }) => {
    const fetchMock = vi.fn().mockResolvedValue(Response.json({ ok: true }));
    vi.stubGlobal("fetch", fetchMock);

    await expect(
      request("/devices", { ...options, token: "test-token" }),
    ).resolves.toEqual({ ok: true });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    expect(fetchMock).toHaveBeenCalledWith(
      "/api/devices",
      expect.objectContaining({
        method,
        body:
          options.body === undefined ? undefined : JSON.stringify(options.body),
        headers: {
          ...(options.body === undefined
            ? {}
            : { "Content-Type": "application/json" }),
          Authorization: "Bearer test-token",
        },
      }),
    );
  },
);

it.each([
  {
    label: "default GET",
    options: {},
    message: "Unable to reach the server. Please try again.",
  },
  {
    label: "explicit lowercase GET",
    options: { method: "get" },
    message: "Unable to reach the server. Please try again.",
  },
  {
    label: "default POST",
    options: { body: { name: "Sensor" } },
    message:
      "No response received. Your request may have completed; check before trying again.",
  },
  {
    label: "bodyless POST",
    options: { method: "POST" },
    message:
      "No response received. Your request may have completed; check before trying again.",
  },
  {
    label: "PATCH",
    options: { method: "PATCH", body: { name: "Renamed sensor" } },
    message:
      "No response received. Your request may have completed; check before trying again.",
  },
])("explains network failure for $label", async ({ options, message }) => {
  const fetchMock = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"));
  vi.stubGlobal("fetch", fetchMock);

  await expect(request("/devices", options)).rejects.toMatchObject({
    message,
    status: 0,
  });
  expect(fetchMock).toHaveBeenCalledTimes(1);
});

it("rejects unknown roles from the API", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json({ email: "user@example.com", role: "superuser" }),
      ),
  );
  await expect(getProfile("token")).rejects.toThrow("unexpected response");
});
it("does not show backend error details", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValue(
        Response.json({ detail: "private database info" }, { status: 500 }),
      ),
  );
  await expect(request("/auth/me")).rejects.toThrow(
    "The request could not be completed",
  );
});
it("explains bad login credentials", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(Response.json({}, { status: 401 })),
  );
  await expect(login("user@example.com", "bad")).rejects.toThrow(
    "Invalid email or password.",
  );
});
it("retains only display fields from the profile", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      Response.json({
        id: "hidden",
        status: "active",
        email: "user@example.com",
        role: "member",
      }),
    ),
  );
  expect(await getProfile("token")).toEqual({
    email: "user@example.com",
    role: "member",
  });
});
