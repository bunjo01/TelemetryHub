import { expect, it } from "vitest";
import {
  createDeviceListQuery,
  readDeviceListQuery,
} from "../features/devices/device-list-query.js";

it("uses default list state when query parameters are absent", () => {
  expect(readDeviceListQuery({})).toEqual({
    search: "",
    status: "active",
    offset: 0,
  });
});

it("reads filters and pagination while ignoring unrelated parameters", () => {
  expect(
    readDeviceListQuery({
      search: "  Freezer & warehouse  ",
      status: "inactive",
      offset: "20",
      unrelated: "ignored",
    }),
  ).toEqual({
    search: "Freezer & warehouse",
    status: "inactive",
    offset: 20,
  });
});

it.each(["active", "inactive", "all"])("accepts the %s status", (status) => {
  expect(readDeviceListQuery({ status }).status).toBe(status);
});

it.each([
  ["unknown", "online"],
  ["empty", ""],
  ["null", null],
  ["repeated", ["active", "inactive"]],
])("defaults an %s status to active", (_label, status) => {
  expect(readDeviceListQuery({ status }).status).toBe("active");
});

it.each([
  ["null", null],
  ["repeated", ["freezer", "warehouse"]],
  ["whitespace", "   "],
])("uses empty search for %s input", (_label, search) => {
  expect(readDeviceListQuery({ search }).search).toBe("");
});

it("trims search before limiting it to 100 characters", () => {
  const search = "x".repeat(101);

  expect(readDeviceListQuery({ search: `  ${search}  ` }).search).toBe(
    "x".repeat(100),
  );
});

it.each([
  ["negative", "-20"],
  ["fractional", "1.5"],
  ["non-numeric", "next"],
  ["exponent notation", "2e1"],
  ["null", null],
  ["repeated", ["20", "40"]],
  ["unsafe integer", "9007199254740992"],
])("resets %s offsets to zero", (_label, offset) => {
  expect(readDeviceListQuery({ offset }).offset).toBe(0);
});

it("omits default values when creating query parameters", () => {
  expect(
    createDeviceListQuery({
      search: "",
      status: "active",
      offset: 0,
    }),
  ).toEqual({});
});

it("serializes filters and offset without manually encoding search", () => {
  expect(
    createDeviceListQuery({
      search: "Freezer & warehouse",
      status: "all",
      offset: 40,
    }),
  ).toEqual({
    search: "Freezer & warehouse",
    status: "all",
    offset: "40",
  });
});

it("preserves normalized state through serialization and parsing", () => {
  const state = {
    search: "Freezer",
    status: "inactive",
    offset: 20,
  };

  expect(readDeviceListQuery(createDeviceListQuery(state))).toEqual(state);
});
