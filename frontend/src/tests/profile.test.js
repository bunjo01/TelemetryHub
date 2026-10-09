import { afterEach, expect, it, vi } from "vitest";
import { getProfile } from "../api/auth.api.js";

afterEach(() => vi.unstubAllGlobals());
it("keeps the owner's company ID internally for invitations", async () => {
  const companyId = "11111111-1111-4111-8111-111111111111";
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      Response.json({
        email: "owner@example.com",
        role: "company_owner",
        company_id: companyId,
        status: "active",
      }),
    ),
  );
  expect(await getProfile("token")).toEqual({
    email: "owner@example.com",
    role: "company_owner",
    companyId,
  });
});
for (const company_id of [null, undefined, "", "bad"]) {
  it("rejects an owner profile without a usable company", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(
        Response.json({
          email: "owner@example.com",
          role: "company_owner",
          company_id,
        }),
      ),
    );
    await expect(getProfile("token")).rejects.toThrow("unexpected response");
  });
}
