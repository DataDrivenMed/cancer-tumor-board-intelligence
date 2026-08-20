import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

test("preserves the governed production product and release surfaces", async () => {
  const [page, home, auth, proxy, architecture, intake, evaluation, apiClient] = await Promise.all([
    readFile(new URL("../app/page.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/components/product-home.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/components/authenticated-product.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/api/backend/[...path]/route.ts", import.meta.url), "utf8"),
    readFile(new URL("../app/components/architecture-view.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/components/case-intake-review.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/components/evaluation-release-console.tsx", import.meta.url), "utf8"),
    readFile(new URL("../app/lib/tumor-board-api.ts", import.meta.url), "utf8"),
  ]);

  assert.match(page, /Clinical workspace/i);
  assert.match(page, /Research console/i);
  assert.match(page, /Skip to primary content/i);
  assert.match(home, /Learn with the synthetic case/i);
  assert.match(home, /Start a de-identified case/i);
  assert.match(auth, /Sign in to Tumor Board Intelligence/i);
  assert.match(proxy, /Authorization/i);
  assert.match(architecture, /Deterministic evaluation harness/i);
  assert.match(architecture, /Clinical Red Team/i);
  assert.match(intake, /Guided synthetic packet/i);
  assert.match(intake, /I confirm this document was de-identified before upload/i);
  assert.match(intake, /processed transiently/i);
  assert.match(evaluation, /Clinical release blocked/i);
  assert.match(apiClient, /\/api\/v1\/evaluations\/summary/i);
  assert.match(apiClient, /\/api\/v1\/release\/readiness/i);
  assert.match(apiClient, /\/api\/v1\/product\/cases/i);
});
