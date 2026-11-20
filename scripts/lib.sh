# shellcheck shell=bash
# Shared by every script in scripts/ and experiments/. Source it; don't run it.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
# shellcheck disable=SC1091
[[ -f "$ROOT/.env" ]] && source "$ROOT/.env"

: "${CLUSTER_NAME:=sandboxed-agent}"
: "${AWS_REGION:=us-west-2}"
: "${MODEL_ID:=us.anthropic.claude-sonnet-5-5}"
: "${GENPOLICY:=$ROOT/.bin/eks-nitro-sandbox-genpolicy}"
: "${GITHUB_REPO:=}"
export AWS_REGION AWS_DEFAULT_REGION="$AWS_REGION"

PREFIX="sandboxed-agent"
KMS_ALIAS="alias/$PREFIX-broker"
STATE="$ROOT/.state"
TMP="$ROOT/.tmp"
ZERO_PCR17="$(printf '0%.0s' $(seq 96))"
mkdir -p "$TMP"
touch "$STATE"

say() { printf '\n\033[1m== %s ==\033[0m\n' "$*"; }
note() { printf '   %s\n' "$*"; }
die() { printf '\033[31merror:\033[0m %s\n' "$*" >&2; exit 1; }
need() { for tool in "$@"; do command -v "$tool" >/dev/null || die "$tool is not installed"; done; }

state_put() { grep -v "^$1=" "$STATE" > "$STATE.new" || true; echo "$1=$2" >> "$STATE.new"; mv "$STATE.new" "$STATE"; }
state_get() { grep "^$1=" "$STATE" | tail -1 | cut -d= -f2- || true; }

account_id() { aws sts get-caller-identity --query Account --output text; }
registry() { echo "$(account_id).dkr.ecr.$AWS_REGION.amazonaws.com"; }

# build_push <repo> <context-dir> <tag>  -> prints repo@digest
# The digest, never the tag, is what the broker pod and its Cedar policy refer to: a tag can
# be moved to another image, a digest cannot.
build_push() {
  local repo="$PREFIX-$1" context="$2" tag="$3" reg
  reg="$(registry)"
  aws ecr describe-repositories --repository-names "$repo" >/dev/null 2>&1 ||
    aws ecr create-repository --repository-name "$repo" \
      --image-scanning-configuration scanOnPush=true >/dev/null
  aws ecr get-login-password | docker login --username AWS --password-stdin "$reg" >/dev/null
  docker build --quiet --platform linux/amd64 -t "$reg/$repo:$tag" "$context" >/dev/null
  docker push --quiet "$reg/$repo:$tag" >/dev/null
  local digest
  digest="$(aws ecr describe-images --repository-name "$repo" --image-ids imageTag="$tag" \
    --query 'imageDetails[0].imageDigest' --output text)"
  echo "$reg/$repo@$digest"
}

# render_broker_pod <image@digest> <out.json>
render_broker_pod() {
  sed -e "s|<BROKER_IMAGE>|$1|" \
      -e "s|<AWS_REGION>|$AWS_REGION|g" \
      -e "s|<KMS_KEY_ARN>|$(state_get KMS_KEY_ARN)|" \
      -e "s|<GITHUB_REPO>|$GITHUB_REPO|" \
      -e "s|<GITHUB_TOKEN_CIPHERTEXT>|$(state_get GITHUB_TOKEN_CIPHERTEXT)|" \
      "$ROOT/k8s/broker-pod.yaml" |
    kubectl create --dry-run=client -o json -f - > "$2"
}

# gen_policy <pod.json> <out.b64>  -> prints the predicted PCR17
# The generator resolves the image in ECR, so it gets registry credentials through a
# throwaway HOME, never on a command line.
gen_policy() {
  local home="$TMP/genpolicy-home" reg log="$TMP/genpolicy.log"
  reg="$(registry)"
  rm -rf "$home" && mkdir -p "$home/.docker"
  ( umask 077
    aws ecr get-login-password | { printf 'AWS:'; cat; } | base64 | tr -d '\r\n' |
      jq -Rn --arg r "$reg" '{auths: {($r): {auth: input}}}' > "$home/.docker/config.json" )
  HOME="$home" "$GENPOLICY" \
    --profile "$ROOT/policy/confidential-profile.yaml" \
    --with-pod-identity --image-architecture amd64 \
    --output-file-b64 "$2" "$1" > "$log"
  rm -rf "$home"
  awk '/--- Predicted PCR17 ---/ {found = 1; next}
       found { v = tolower($0); gsub(/[[:space:]]/, "", v)
               if (v ~ /^[0123456789abcdef]{96}$/) { print v; exit } }' "$log"
}

# put_key_policy <pcr17> : the gate. Retried, because IAM takes a moment to let KMS see a
# role that was just created, and KMS rejects a policy naming a principal it cannot see.
put_key_policy() {
  local doc="$TMP/kms-key-policy.json"
  jq --arg acct "$(account_id)" --arg role "$(state_get BROKER_ROLE_ARN)" --arg pcr "$1" '
    del(._comment)
    | walk(if type == "string" then
             gsub("<ACCOUNT_ID>"; $acct) | gsub("<BROKER_ROLE_ARN>"; $role) | gsub("<EXPECTED_PCR17>"; $pcr)
           else . end)' "$ROOT/policy/kms-key-policy.json" > "$doc"
  for _ in $(seq 12); do
    aws kms put-key-policy --key-id "$(state_get KMS_KEY_ARN)" --policy-name default \
      --policy "file://$doc" 2>/dev/null && return 0
    sleep 5
  done
  die "could not put the key policy (is the broker role visible to KMS yet?)"
}

# apply_broker <pod.json> <policy.b64> : replace the broker pod with this spec and policy.
# The policy annotation is immutable, so the old pod is deleted, never patched.
apply_broker() {
  jq --rawfile p "$2" '.metadata.annotations["sandbox.amazonaws.com/policy"] = ($p | gsub("\\s"; ""))' \
    "$1" > "$TMP/broker-rendered.json"
  kubectl delete pod broker -n agent-broker --ignore-not-found --wait=true --timeout=5m >/dev/null
  kubectl apply -f "$TMP/broker-rendered.json" >/dev/null
}

# wait_broker : until the broker logs that it unsealed or sealed, then print that line.
wait_broker() {
  for _ in $(seq 120); do
    if kubectl logs broker -n agent-broker 2>/dev/null | grep -qE 'broker_(un)?sealed'; then
      kubectl logs broker -n agent-broker | grep -E 'broker_(un)?sealed' | tail -1
      return 0
    fi
    sleep 5
  done
  kubectl get pod broker -n agent-broker -o wide
  die "the broker did not report within 10 minutes"
}

# brain_job <name> <args-as-json-array> : run the brain image once and print its logs.
brain_job() {
  local name="$1" args="$2" image
  image="$(state_get BRAIN_IMAGE)"
  kubectl delete job "$name" -n agent-brain --ignore-not-found --wait=true >/dev/null
  kubectl apply -f - >/dev/null <<EOF
apiVersion: batch/v1
kind: Job
metadata: { name: $name, namespace: agent-brain }
spec:
  backoffLimit: 0
  ttlSecondsAfterFinished: 3600
  template:
    metadata: { labels: { app: brain } }
    spec:
      serviceAccountName: brain
      restartPolicy: Never
      nodeSelector: { kubernetes.io/arch: amd64 }
      securityContext: { runAsUser: 65534, runAsNonRoot: true, seccompProfile: { type: RuntimeDefault } }
      containers:
        - name: brain
          image: $image
          args: $args
          env:
            - { name: MODEL_ID, value: "$MODEL_ID" }
            - { name: GITHUB_REPO, value: "$GITHUB_REPO" }
            - { name: AWS_REGION, value: "$AWS_REGION" }
            - { name: AWS_DEFAULT_REGION, value: "$AWS_REGION" }
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: ["ALL"] }
          volumeMounts: [{ name: task, mountPath: /task, readOnly: true }]
      volumes: [{ name: task, configMap: { name: task } }]
EOF
  # Stream the logs as soon as the container has started, until it exits.
  for _ in $(seq 120); do
    kubectl logs "job/$name" -n agent-brain >/dev/null 2>&1 && break
    sleep 3
  done
  kubectl logs -f "job/$name" -n agent-brain
}
