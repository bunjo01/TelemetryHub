import { afterEach, expect, it, vi } from "vitest";
import { getProfile, login } from "../api/auth.api.js";
import { request } from "../api/client.js";

afterEach(() => vi.unstubAllGlobals());
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
