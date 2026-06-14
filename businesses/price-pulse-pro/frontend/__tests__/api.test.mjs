import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const apiSource = readFileSync(join(root, "lib", "api.ts"), "utf8");

test("api client reads base URL from env variable", () => {
  assert.match(apiSource, /NEXT_PUBLIC_API_BASE_URL/);
});

test("api client handles non-2xx responses", () => {
  assert.match(apiSource, /class ApiError/);
  assert.match(apiSource, /if \(!response\.ok\)/);
  assert.match(apiSource, /throw new ApiError/);
});
