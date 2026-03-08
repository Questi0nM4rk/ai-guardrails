export interface Console {
  info(msg: string): void;
  success(msg: string): void;
  warning(msg: string): void;
  error(msg: string): void;
  step(msg: string): void;
}

const RESET = "\x1b[0m";
const GREEN = "\x1b[32m";
const CYAN = "\x1b[36m";

export class RealConsole implements Console {
  info(msg: string): void {
    process.stdout.write(`${msg}\n`);
  }

  success(msg: string): void {
    process.stdout.write(`${GREEN}${msg}${RESET}\n`);
  }

  warning(msg: string): void {
    process.stderr.write(`\x1b[33m⚠ ${msg}\x1b[0m\n`);
  }

  error(msg: string): void {
    process.stderr.write(`\x1b[31m✖ ${msg}\x1b[0m\n`);
  }

  step(msg: string): void {
    process.stdout.write(`${CYAN}${msg}${RESET}\n`);
  }
}
