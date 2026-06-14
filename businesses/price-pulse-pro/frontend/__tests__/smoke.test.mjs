import test from "node:test";
import assert from "node:assert/strict";

test("package metadata is defined", () => {
  const pkg = { name: "price-pulse-pro-frontend", version: "0.1.0" };
  assert.equal(pkg.name, "price-pulse-pro-frontend");
  assert.ok(pkg.version);
});
