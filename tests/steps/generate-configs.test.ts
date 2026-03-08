import { describe, expect, test } from "bun:test";
import { generateConfigsStep } from "@/steps/generate-configs";
import { ALL_GENERATORS } from "@/generators/registry";
import { FakeFileManager } from "../fakes/fake-file-manager";
import { buildResolvedConfig } from "@/config/schema";
import { MachineConfigSchema, ProjectConfigSchema } from "@/config/schema";

function makeConfig() {
  const machine = MachineConfigSchema.parse({});
  const project = ProjectConfigSchema.parse({});
  return buildResolvedConfig(machine, project);
}

describe("generateConfigsStep", () => {
  test("writes all generator outputs to projectDir", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    const result = await generateConfigsStep("/project", config, fm);

    expect(result.status).toBe("ok");
    expect(fm.written.length).toBe(ALL_GENERATORS.length);
  });

  test("each written file path is under the projectDir", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    await generateConfigsStep("/project", config, fm);

    for (const [path] of fm.written) {
      expect(path.startsWith("/project/")).toBe(true);
    }
  });

  test("written files have non-empty content", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    await generateConfigsStep("/project", config, fm);

    for (const [, content] of fm.written) {
      expect(content.length).toBeGreaterThan(0);
    }
  });

  test("result message lists generated files", async () => {
    const fm = new FakeFileManager();
    const config = makeConfig();

    const result = await generateConfigsStep("/project", config, fm);

    expect(result.message).toContain("Generated");
    expect(result.message).toContain(String(ALL_GENERATORS.length));
  });
});
