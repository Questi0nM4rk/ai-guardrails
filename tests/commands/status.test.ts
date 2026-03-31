import { describe, expect, test } from "bun:test";
import { printVersionStatus } from "@/commands/status";
import { getVersion } from "@/utils/version";
import { FakeConsole } from "../fakes/fake-console";

const INSTALLED = getVersion();

describe("printVersionStatus — no min_version configured", () => {
  test("prints (not pinned) message when minVersion is undefined", () => {
    const cons = new FakeConsole();
    const warning = printVersionStatus(INSTALLED, undefined, cons);

    expect(warning).toBeUndefined();
    expect(cons.infos).toHaveLength(1);
    expect(cons.infos[0]).toContain("not pinned");
    expect(cons.infos[0]).toContain(INSTALLED);
  });
});

describe("printVersionStatus — installed meets or exceeds pinned", () => {
  test("prints version info without warning when installed equals pinned", () => {
    const cons = new FakeConsole();
    const warning = printVersionStatus(INSTALLED, INSTALLED, cons);

    expect(warning).toBeUndefined();
    expect(cons.infos).toHaveLength(1);
    expect(cons.infos[0]).toContain(INSTALLED);
    expect(cons.infos[0]).toContain("pinned:");
  });

  test("prints version info without warning when installed is higher than pinned", () => {
    const cons = new FakeConsole();
    const warning = printVersionStatus("99.0.0", "1.0.0", cons);

    expect(warning).toBeUndefined();
    expect(cons.infos).toHaveLength(1);
    expect(cons.infos[0]).toContain("99.0.0");
    expect(cons.infos[0]).toContain("pinned: >=1.0.0");
  });
});

describe("printVersionStatus — installed is older than pinned", () => {
  test("returns warning string when installed < pinned", () => {
    const cons = new FakeConsole();
    const warning = printVersionStatus("1.0.0", "99.0.0", cons);

    expect(warning).toBeDefined();
    expect(warning).toContain("Version mismatch");
    expect(warning).toContain(">=99.0.0");
    expect(warning).toContain("installed 1.0.0");
  });

  test("still logs version info to console when mismatch occurs", () => {
    const cons = new FakeConsole();
    printVersionStatus("1.0.0", "99.0.0", cons);

    expect(cons.infos).toHaveLength(1);
    expect(cons.infos[0]).toContain("1.0.0");
    expect(cons.infos[0]).toContain("pinned: >=99.0.0");
  });

  test("returns undefined (no warning) when installed equals pinned exactly", () => {
    const cons = new FakeConsole();
    const warning = printVersionStatus("3.1.0", "3.1.0", cons);

    expect(warning).toBeUndefined();
  });
});
