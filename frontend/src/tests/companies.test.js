import { afterEach, expect, it, vi } from "vitest";
import { searchCompanies } from "../api/companies.api.js";

afterEach(() => vi.unstubAllGlobals());

it.each([
  ["missing", undefined],
  ["null", null],
  ["number", 123],
  ["empty", ""],
  ["only hyphens", "-".repeat(36)],
  ["no hyphens", "a".repeat(36)],
  ["misplaced hyphen", "28f63fb-6b64f-4607-bb79-a6e815ab9131"],
  ["non-hexadecimal character", "28f63fb6-b64f-4607-bb79-a6e815ab913z"],
  ["leading whitespace", " 28f63fb6-b64f-4607-bb79-a6e815ab9131"],
  ["truncated", "28f63fb6-b64f-4607-bb79-a6e815ab913"],
])("rejects company search IDs that are %s", async (_description, id) => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      Response.json({
        items: [{ id, name: "Orbital Labs" }],
        has_more: false,
      }),
    ),
  );

  await expect(searchCompanies("Orbital", 0, "token")).rejects.toThrow(
    "unexpected response",
  );
});

it.each([
  "28f63fb6-b64f-4607-bb79-a6e815ab9131",
  "28F63FB6-B64F-4607-BB79-A6E815AB9131",
])("preserves a valid company ID: %s", async (id) => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(
      Response.json({
        items: [{ id, name: "Orbital Labs", internal: "not retained" }],
        has_more: true,
      }),
    ),
  );

  await expect(searchCompanies("Orbital", 0, "token")).resolves.toEqual({
    items: [{ id, name: "Orbital Labs" }],
    hasMore: true,
  });
});
