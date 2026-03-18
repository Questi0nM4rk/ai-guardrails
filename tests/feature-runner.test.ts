import { loadFeatures, runFeatures } from "@questi0nm4rk/feats";
import "./steps/language.steps";
import "./steps/pipeline.steps";

const features = await loadFeatures("tests/features/**/*.feature", {
  cwd: process.cwd(),
});
runFeatures(features);
