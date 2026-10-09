import { afterEach, expect, it, vi } from "vitest";
import { acceptInvitation, previewInvitation } from "../api/invitations.api.js";

afterEach(() => vi.unstubAllGlobals());
for (const data of [{}, { email: "a@b.com", expires_at: "bad" }]) {
  it("rejects malformed preview data", async () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue(Response.json(data)));
    await expect(previewInvitation("a".repeat(43))).rejects.toThrow(
      "unexpected response",
    );
  });
}
it("sends invitation in the body and retains only display data", async () => {
  const fetch = vi
    .fn()
    .mockResolvedValue(
      Response.json({ email: "a@b.com", role: "member", id: "hidden" }),
    );
  vi.stubGlobal("fetch", fetch);
  expect(await acceptInvitation("secret", " long password ")).toEqual({
    email: "a@b.com",
    role: "member",
  });
  const [url, options] = fetch.mock.calls[0];
  expect(url).toBe("/api/invitations/accept");
  expect(options.headers.Authorization).toBeUndefined();
  expect(JSON.parse(options.body)).toEqual({
    token: "secret",
    password: " long password ",
  });
});
it("explains uncertainty after a malformed acceptance response", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response("invalid json")),
  );
  await expect(acceptInvitation("secret", "password")).rejects.toThrow(
    "account may have been created",
  );
});

it("creates a member invitation with authenticated company scope and normalized email", async () => {
  const { inviteMember } = await import("../api/invitations.api.js");
  const fetch = vi.fn().mockResolvedValue(
    Response.json({
      email: "member@example.com",
      token: "a".repeat(43),
      expires_at: "2027-01-01T00:00:00Z",
    }),
  );
  vi.stubGlobal("fetch", fetch);
  const result = await inviteMember(
    "company-id",
    " Member@Example.com ",
    "owner-token",
  );
  expect(result.email).toBe("member@example.com");
  const [url, options] = fetch.mock.calls[0];
  expect(url).toBe("/api/companies/company-id/member-invitations");
  expect(options.headers.Authorization).toBe("Bearer owner-token");
  expect(JSON.parse(options.body)).toEqual({ email: "member@example.com" });
});
it("rejects a member invitation with an invalid token", async () => {
  const { inviteMember } = await import("../api/invitations.api.js");
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      Response.json({
        email: "member@example.com",
        token: "invalid",
        expires_at: "2027-01-01T00:00:00Z",
      }),
    ),
  );
  await expect(
    inviteMember("company-id", "member@example.com", "token"),
  ).rejects.toThrow("unexpected response");
});
