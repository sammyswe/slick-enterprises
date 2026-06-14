import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const root = join(dirname(fileURLToPath(import.meta.url)), "..");
const navSource = readFileSync(join(root, "components", "Navigation.tsx"), "utf8");
const layoutSource = readFileSync(join(root, "app", "layout.tsx"), "utf8");

const expectedNavItems = [
  { href: "/competitors", label: "Competitors" },
  { href: "/history", label: "History" },
  { href: "/alerts", label: "Alerts" },
  { href: "/settings", label: "Settings" },
];

for (const { href, label } of expectedNavItems) {
  test(`navigation includes ${label} link to ${href}`, () => {
    assert.match(navSource, new RegExp(`href: "${href}"`));
    assert.match(navSource, new RegExp(`label: "${label}"`));
  });
}

test("root layout renders navigation shell", () => {
  assert.match(layoutSource, /AppShell/);
  assert.match(navSource, /export function Navigation/);
});
