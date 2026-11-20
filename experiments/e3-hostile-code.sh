#!/usr/bin/env bash
# Experiment 3: run the probe inside a real hands session, exactly where the repository's
# tests and the model's commands run. Every line should be PASS.
source "$(dirname "$0")/../scripts/lib.sh"
say "the probe, inside the agent's hands"
brain_job exp-hostile-code '["probe"]'
