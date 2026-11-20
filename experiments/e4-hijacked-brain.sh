#!/usr/bin/env bash
# Experiment 4: you own the brain. The brain can create pods. Create one WITHOUT the sandbox.
source "$(dirname "$0")/../scripts/lib.sh"
say "the hijacked brain asks for unsandboxed pods"
brain_job exp-hijacked-brain '["escape-pod"]'
