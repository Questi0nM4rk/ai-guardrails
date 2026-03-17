import { loadFeatures, runFeatures } from "@questi0nm4rk/feats";
import "./steps/project.steps";
import "./steps/init.steps";
import "./steps/check.steps";

const features = await loadFeatures("tests/e2e/features/*.feature", {
  cwd: process.cwd(),
});
runFeatures(features);
