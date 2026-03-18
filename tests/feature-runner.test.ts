import { loadFeatures, runFeatures } from "@questi0nm4rk/feats";
import "./steps/engine.steps";
import "./steps/config.steps";
import "./steps/generator.steps";

const features = await loadFeatures("tests/features/**/*.feature", {
  cwd: process.cwd(),
});
runFeatures(features);
