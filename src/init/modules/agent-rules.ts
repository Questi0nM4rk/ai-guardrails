import { detectAgentTools } from "@/generators/agent-rules";
import type { InitContext, InitModule, InitModuleResult } from "@/init/types";
import { setupAgentInstructionsStep } from "@/steps/setup-agent-instructions";

export const agentRulesModule: InitModule = {
  id: "agent-rules",
  name: "Agent Rules",
  description: "Write AI agent rules files for detected tools",
  category: "agent",
  defaultEnabled: true,
  disableFlag: "--no-agent-rules",

  async detect(ctx: InitContext): Promise<boolean> {
    const tools = await detectAgentTools(ctx.projectDir, ctx.fileManager);
    return (
      tools.claude ||
      tools.cursor ||
      tools.windsurf ||
      tools.copilot ||
      tools.cline ||
      tools.aider
    );
  },

  async execute(ctx: InitContext): Promise<InitModuleResult> {
    const result = await setupAgentInstructionsStep(ctx.projectDir, ctx.fileManager);

    if (result.status === "error") {
      return { status: "error", message: result.message };
    }

    return {
      status: "ok",
      message: result.message,
    };
  },
};
