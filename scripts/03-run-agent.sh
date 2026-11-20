#!/usr/bin/env bash
# Let the agent fix issue #1. Its whole conversation, every tool call and every result is
# printed as it happens.
source "$(dirname "$0")/lib.sh"
say "the agent works on demo-repo/issues/1.md against $GITHUB_REPO"
brain_job agent-run '["run"]'
say "what the broker did"
kubectl logs broker -n agent-broker | grep -E 'pr_(opened|refused)|github_error' || note "nothing"
