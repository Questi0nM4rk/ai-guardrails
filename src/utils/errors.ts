/** Returns true if `err` is a Node.js ENOENT (file not found) error. */
export function isEnoent(err: unknown): boolean {
  if (typeof err !== "object" || err === null) return false;
  return "code" in err && err.code === "ENOENT";
}
