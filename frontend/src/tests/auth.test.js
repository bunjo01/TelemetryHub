import { createPinia, setActivePinia } from "pinia";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { getProfile, login } from "../api/auth.api.js";
import { useAuthStore } from "../stores/auth.js";

vi.mock("../api/auth.api.js", () => ({ login: vi.fn(), getProfile: vi.fn() }));
beforeEach(() => {
  vi.resetAllMocks();
  setActivePinia(createPinia());
});
describe("session", () => {
  it("publishes a session only after loading the profile and clears it on logout", async () => {
    const auth = useAuthStore();
    login.mockResolvedValue("token");
    getProfile.mockResolvedValue({ email: "user@example.com", role: "member" });
    await auth.signIn(" User@Example.com ", "password");
    expect(login).toHaveBeenCalledWith(
      "user@example.com",
      "password",
      expect.any(AbortSignal),
    );
    expect(auth.isAuthenticated).toBe(true);
    auth.logout();
    expect(auth.user).toBeNull();
    expect(auth.token).toBe("");
  });
  it("does not keep a token if profile loading fails", async () => {
    login.mockResolvedValue("token");
    getProfile.mockRejectedValue(new Error("Unavailable"));
    const auth = useAuthStore();
    await expect(auth.signIn("a@b.com", "password")).rejects.toThrow(
      "Unavailable",
    );
    expect(auth.isAuthenticated).toBe(false);
    expect(auth.token).toBe("");
  });
  it("cannot restore an obsolete session after logout", async () => {
    let finish;
    login.mockResolvedValue("token");
    getProfile.mockImplementation(
      () =>
        new Promise((resolve) => {
          finish = resolve;
        }),
    );
    const auth = useAuthStore();
    const pending = auth.signIn("a@b.com", "password");
    await vi.waitFor(() => expect(finish).toBeTypeOf("function"));
    auth.logout();
    finish({ email: "a@b.com", role: "member" });
    expect(await pending).toBe(false);
    expect(auth.isAuthenticated).toBe(false);
  });
});
