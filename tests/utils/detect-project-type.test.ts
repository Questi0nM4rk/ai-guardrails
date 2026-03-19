import { describe, expect, test } from "bun:test";
import { detectNoConsoleLevel } from "@/utils/detect-project-type";

describe("detectNoConsoleLevel", () => {
  test("returns warn for null", () => {
    expect(detectNoConsoleLevel(null)).toBe("warn");
  });

  test("returns warn for undefined", () => {
    expect(detectNoConsoleLevel(undefined)).toBe("warn");
  });

  test("returns warn for non-object", () => {
    expect(detectNoConsoleLevel("not an object")).toBe("warn");
    expect(detectNoConsoleLevel(42)).toBe("warn");
  });

  test("returns warn for empty package.json", () => {
    expect(detectNoConsoleLevel({})).toBe("warn");
  });

  test("returns warn for a server library with express", () => {
    expect(detectNoConsoleLevel({ dependencies: { express: "^4.0.0" } })).toBe("warn");
  });

  test("returns off for CLI project with bin field", () => {
    expect(detectNoConsoleLevel({ bin: { mycli: "./dist/cli.js" } })).toBe("off");
  });

  test("returns off for CLI project with bin string", () => {
    expect(detectNoConsoleLevel({ bin: "./dist/cli.js" })).toBe("off");
  });

  test("returns error for react in dependencies", () => {
    expect(detectNoConsoleLevel({ dependencies: { react: "^18.0.0" } })).toBe("error");
  });

  test("returns error for react in devDependencies", () => {
    expect(detectNoConsoleLevel({ devDependencies: { react: "^18.0.0" } })).toBe(
      "error"
    );
  });

  test("returns error for vue in dependencies", () => {
    expect(detectNoConsoleLevel({ dependencies: { vue: "^3.0.0" } })).toBe("error");
  });

  test("returns error for svelte in dependencies", () => {
    expect(detectNoConsoleLevel({ dependencies: { svelte: "^4.0.0" } })).toBe("error");
  });

  test("returns error for @angular/core in dependencies", () => {
    expect(detectNoConsoleLevel({ dependencies: { "@angular/core": "^17.0.0" } })).toBe(
      "error"
    );
  });

  test("returns error for next in dependencies", () => {
    expect(detectNoConsoleLevel({ dependencies: { next: "^14.0.0" } })).toBe("error");
  });

  test("returns error for nuxt in dependencies", () => {
    expect(detectNoConsoleLevel({ dependencies: { nuxt: "^3.0.0" } })).toBe("error");
  });

  test("returns error for solid-js in dependencies", () => {
    expect(detectNoConsoleLevel({ dependencies: { "solid-js": "^1.0.0" } })).toBe(
      "error"
    );
  });

  test("returns error for preact in dependencies", () => {
    expect(detectNoConsoleLevel({ dependencies: { preact: "^10.0.0" } })).toBe("error");
  });

  test("returns error for qwik in dependencies", () => {
    expect(detectNoConsoleLevel({ dependencies: { qwik: "^1.0.0" } })).toBe("error");
  });

  test("browser wins over CLI when both react and bin present", () => {
    expect(
      detectNoConsoleLevel({
        bin: { mycli: "./dist/cli.js" },
        dependencies: { react: "^18.0.0" },
      })
    ).toBe("error");
  });

  test("browser wins over CLI when bin and next present", () => {
    expect(
      detectNoConsoleLevel({
        bin: "./dist/cli.js",
        dependencies: { next: "^14.0.0" },
      })
    ).toBe("error");
  });

  test("handles missing dependencies gracefully", () => {
    expect(detectNoConsoleLevel({ name: "my-package", version: "1.0.0" })).toBe("warn");
  });

  test("handles dependencies not being an object", () => {
    expect(detectNoConsoleLevel({ dependencies: "invalid" })).toBe("warn");
  });

  test("handles devDependencies not being an object", () => {
    expect(detectNoConsoleLevel({ devDependencies: null })).toBe("warn");
  });
});
