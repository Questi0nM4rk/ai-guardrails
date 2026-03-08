/**
 * Canonical rule identifier format: "linter/RULE_CODE"
 * Examples: "ruff/E501", "biome/lint/correctness/noUnusedVariables"
 */
export const RULE_PATTERN = /^[\w-]+\/[\w\-./]+$/;
