import { describe, expect, test } from "bun:test";
import { error, ok, skip, warn } from "@/models/step-result";

describe("ok", () => {
  test("sets status to ok", () => {
    const result = ok("all good");
    expect(result.status).toBe("ok");
    expect(result.message).toBe("all good");
  });
});

describe("error", () => {
  test("sets status to error", () => {
    const result = error("something failed");
    expect(result.status).toBe("error");
    expect(result.message).toBe("something failed");
  });
});

describe("skip", () => {
  test("sets status to skip", () => {
    const result = skip("nothing to do");
    expect(result.status).toBe("skip");
    expect(result.message).toBe("nothing to do");
  });
});

describe("warn", () => {
  test("sets status to warn", () => {
    const result = warn("check this");
    expect(result.status).toBe("warn");
    expect(result.message).toBe("check this");
  });
});
