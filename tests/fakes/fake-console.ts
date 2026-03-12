import type { Console } from "@/infra/console";

export class FakeConsole implements Console {
  readonly infos: string[] = [];
  readonly successes: string[] = [];
  readonly warnings: string[] = [];
  readonly errors: string[] = [];
  readonly steps: string[] = [];

  info(msg: string): void {
    this.infos.push(msg);
  }

  success(msg: string): void {
    this.successes.push(msg);
  }

  warning(msg: string): void {
    this.warnings.push(msg);
  }

  error(msg: string): void {
    this.errors.push(msg);
  }

  step(msg: string): void {
    this.steps.push(msg);
  }
}
