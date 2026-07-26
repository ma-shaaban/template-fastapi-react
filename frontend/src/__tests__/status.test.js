import { describe, it, expect } from "vitest";
import { statusLabel } from "../status.js";

describe("statusLabel", () => {
  it("labels successful responses ok", () => {
    expect(statusLabel({ ok: true, status: 200 })).toBe("ok");
  });
  it("labels failures with the http status", () => {
    expect(statusLabel({ ok: false, status: 503 })).toBe("http 503");
    expect(statusLabel({ ok: false, status: 404 })).toBe("http 404");
  });
});
