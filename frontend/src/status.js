// Tiny pure helper used by App.jsx — and the template's example of a
// unit-testable module. Frontend tests live in src/__tests__/ and run with
// Vitest (`npm run test`), both locally and in the CI `test` job. Put logic
// you want tested in plain modules like this one, not inside components.
export function statusLabel(res) {
  return res.ok ? "ok" : `http ${res.status}`;
}
