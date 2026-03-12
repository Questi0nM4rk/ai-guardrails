export interface Console {
  info(msg: string): void;
  success(msg: string): void;
  warning(msg: string): void;
  error(msg: string): void;
  step(msg: string): void;
}

const RESET = "\x1b[0m";
const GREEN = "\x1b[32m";
const YELLOW = "\x1b[33m";
const RED = "\x1b[31m";
const CYAN = "\x1b[36m";

export class RealConsole implements Console {
  info(msg: string): void {
    process.stdout.write(`${msg}\n`);
  }

  success(msg: string): void {
    process.stdout.write(`${GREEN}${msg}${RESET}\n`);
  }

  warning(msg: string): void {
    process.stdout.write(`${YELLOW}${msg}${RESET}\n`);
  }

  error(msg: string): void {
    process.stdout.write(`${RED}${msg}${RESET}\n`);
  }

  step(msg: string): void {
    process.stdout.write(`${CYAN}${msg}${RESET}\n`);
  }
}
