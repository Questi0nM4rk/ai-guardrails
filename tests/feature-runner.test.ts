import { loadFeatures, runFeatures } from "@questi0nm4rk/feats";
import "./steps/dangerous-cmd.steps";
import "./steps/suppress.steps";
import "./steps/engine.steps";
import "./steps/config.steps";
import "./steps/generator.steps";
import "./steps/language.steps";
import "./steps/check-pipeline.steps";
import "./steps/install-pipeline.steps";
import "./steps/generator-filtering.steps";
import "./steps/ci-workflow.steps";
import "./steps/no-console.steps";

const features = await loadFeatures("tests/features/**/*.feature", {
  cwd: process.cwd(),
});
runFeatures(features);
