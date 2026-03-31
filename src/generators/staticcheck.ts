import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import { withHashHeader } from "@/utils/hash";

function renderStaticcheckConf(_config: ResolvedConfig): string {
  const content = `[checks]
enabled = ["all"]
`;
  return withHashHeader(content);
}

export const staticcheckGenerator: ConfigGenerator = {
  id: "staticcheck",
  configFile: "staticcheck.conf",
  languages: ["go"],
  generate(config: ResolvedConfig): string {
    return renderStaticcheckConf(config);
  },
};
