import { loadFeatures, runFeatures } from "@questi0nm4rk/feats";
import "./steps/check-pipeline.steps";
import "./steps/install-pipeline.steps";
import "./steps/language.steps";

const features = await loadFeatures("tests/features/**/*.feature", {
  cwd: process.cwd(),
});
runFeatures(features);
