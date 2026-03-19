import { expect } from "bun:test";
import type { World } from "@questi0nm4rk/feats";
import { Given, Then, When } from "@questi0nm4rk/feats";
import type { StepResult } from "@/models/step-result";
import { setupCiStep } from "@/steps/setup-ci";
import { FakeFileManager } from "../fakes/fake-file-manager";

const PROJECT_DIR = "/project";

interface CiWorkflowWorld extends World {
  fm: FakeFileManager;
  workflowContent: string;
  workflowPath: string;
  stepResult: StepResult;
}

Given<CiWorkflowWorld>("a project for CI setup", (world: CiWorkflowWorld) => {
  world.fm = new FakeFileManager();
});

When<CiWorkflowWorld>(
  "the CI workflow is generated",
  async (world: CiWorkflowWorld) => {
    const fm = world.fm ?? new FakeFileManager();
    world.stepResult = await setupCiStep(PROJECT_DIR, fm);
    const entry = fm.written[0];
    if (entry === undefined) {
      world.workflowContent = "";
      world.workflowPath = "";
    } else {
      const [path, content] = entry;
      world.workflowPath = path;
      world.workflowContent = content;
    }
  }
);

Then<CiWorkflowWorld>(
  "the workflow should contain {string}",
  (world: CiWorkflowWorld, text: unknown) => {
    expect(world.workflowContent).toContain(String(text));
  }
);

Then<CiWorkflowWorld>(
  "the workflow should be written to {string}",
  (world: CiWorkflowWorld, relativePath: unknown) => {
    expect(world.workflowPath).toBe(`${PROJECT_DIR}/${String(relativePath)}`);
  }
);

Then<CiWorkflowWorld>(
  "{string} should come before {string} in the workflow",
  (world: CiWorkflowWorld, first: unknown, second: unknown) => {
    const firstIdx = world.workflowContent.indexOf(String(first));
    const secondIdx = world.workflowContent.indexOf(String(second));
    expect(firstIdx).toBeGreaterThanOrEqual(0);
    expect(secondIdx).toBeGreaterThanOrEqual(0);
    expect(firstIdx).toBeLessThan(secondIdx);
  }
);

Then<CiWorkflowWorld>(
  "the CI step result status should be {string}",
  (world: CiWorkflowWorld, status: unknown) => {
    const s = String(status);
    expect(["ok", "error", "warn", "skip"]).toContain(s);
    expect(world.stepResult.status).toBe(
      s === "ok" ? "ok" : s === "error" ? "error" : s === "warn" ? "warn" : "skip"
    );
  }
);
