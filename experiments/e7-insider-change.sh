#!/usr/bin/env bash
# Experiment 7: you are an insider who can build, push, generate a policy and redeploy.
# You make ONE change: let the broker touch .github/ (so the agent can "fix CI"). You do
# everything else by the book. Then the approved broker is put back.
source "$(dirname "$0")/../scripts/lib.sh"

say "7a: loosen the broker's rules and build it"
CHANGED="$TMP/changed-broker"
rm -rf "$CHANGED" && cp -r "$ROOT/apps/broker" "$CHANGED"
jq '.denied_path_prefixes -= [".github/"]' "$ROOT/apps/broker/broker-policy.json" > "$CHANGED/broker-policy.json"
diff <(jq -S .denied_path_prefixes "$ROOT/apps/broker/broker-policy.json") \
     <(jq -S .denied_path_prefixes "$CHANGED/broker-policy.json") || true
IMAGE="$(build_push broker "$CHANGED" changed)"
note "changed image $IMAGE"

say "7b: generate a fresh, valid Cedar policy for it"
render_broker_pod "$IMAGE" "$TMP/changed-pod.json"
PCR="$(gen_policy "$TMP/changed-pod.json" "$TMP/changed-policy.b64")"
note "approved PCR17 $(state_get PCR17)"
note "changed  PCR17 $PCR"

say "7c: replace the broker"
apply_broker "$TMP/changed-pod.json" "$TMP/changed-policy.b64"
wait_broker

say "7d: put the approved broker back"
apply_broker "$TMP/approved-pod.json" "$TMP/approved-policy.b64"
wait_broker
