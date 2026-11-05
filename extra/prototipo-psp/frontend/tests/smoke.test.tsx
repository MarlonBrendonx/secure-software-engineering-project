import { describe, expect, it } from "vitest";

describe("Smoke Tests", () => {
  it("environment is configured", () => {
    expect(true).toBe(true);
  });

  it("can import React", async () => {
    const React = await import("react");
    expect(React.useState).toBeDefined();
  });

  it("can import utils", async () => {
    const { cn } = await import("@/lib/utils");
    expect(cn("foo", "bar")).toBe("foo bar");
  });
});
