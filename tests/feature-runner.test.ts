import { loadFeatures, runFeatures } from "@questi0nm4rk/feats";
import "./steps/dangerous-cmd.steps";
import "./steps/suppress.steps";
import "./steps/engine.steps";
import "./steps/config.steps";
import "./steps/generator.steps";

const features = await loadFeatures("tests/features/**/*.feature", {
  cwd: process.cwd(),
});
runFeatures(features);
