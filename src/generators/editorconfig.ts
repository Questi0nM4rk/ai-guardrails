import type { ResolvedConfig } from "@/config/schema";
import type { ConfigGenerator } from "@/generators/types";
import { makeHashHeader } from "@/utils/hash";

function renderEditorconfig(_config: ResolvedConfig): string {
  const content = `root = true

[*]
charset = utf-8
end_of_line = lf
insert_final_newline = true
trim_trailing_whitespace = true
indent_style = space
indent_size = 4
max_line_length = 88

[*.{ts,js,tsx,jsx,json,yaml,yml,toml,md}]
indent_size = 2

[Makefile]
indent_style = tab

[*.go]
indent_style = tab
`;
  const header = makeHashHeader(content);
  return `${header}\n${content}`;
}

export const editorconfigGenerator: ConfigGenerator = {
  id: "editorconfig",
  configFile: ".editorconfig",
  generate(config: ResolvedConfig): string {
    return renderEditorconfig(config);
  },
};
