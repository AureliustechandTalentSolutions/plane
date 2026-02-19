import { describe, it, expect } from "vitest";

describe("Web App Smoke Test", () => {
  it("environment is configured correctly", () => {
    expect(typeof window).toBe("object");
    expect(typeof document).toBe("object");
  });

  it("basic arithmetic sanity check", () => {
    expect(1 + 1).toBe(2);
  });
});
