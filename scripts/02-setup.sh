#!/usr/bin/env bash
# Build the three zones, encrypt the GitHub token under KMS, and gate the key on the
# broker's measured Cedar policy. Safe to re-run: it reuses what exists and replaces the
# broker pod.
source "$(dirname "$0")/lib.sh"
need aws kubectl docker jq
[[ "$GITHUB_REPO" == */* ]] || die "set GITHUB_REPO=owner/name in .env (your copy of demo-repo/)"
[[ -x "$GENPOLICY" ]] || die "no policy generator at $GENPOLICY; run scripts/01-get-genpolicy.sh"
kubectl get runtimeclass confidential-sandbox >/dev/null ||
  die "no confidential-sandbox runtime class; is this an EKS Auto Mode cluster on 1.36+?"
[[ "$(kubectl get cm amazon-vpc-cni -n kube-system -o jsonpath='{.data.enable-network-policy-controller}')" == true ]] ||
  die "network policy is not enforced; see scripts/00-cluster.sh"
ACCOUNT="$(account_id)"

say "1/7 zones: namespaces, the hands guardrail, the brain's RBAC, the task"
kubectl apply -f "$ROOT/k8s/namespaces.yaml" -f "$ROOT/k8s/hands-guardrail.yaml" \
  -f "$ROOT/k8s/brain-rbac.yaml" >/dev/null
kubectl create configmap task -n agent-brain --from-file=issue.md="$ROOT/demo-repo/issues/1.md" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null

say "2/7 the KMS key, born unable to decrypt"
KEY_ARN="$(aws kms describe-key --key-id "$KMS_ALIAS" --query KeyMetadata.Arn --output text 2>/dev/null || true)"
if [[ -z "$KEY_ARN" || "$KEY_ARN" == None ]]; then
  # Never the default key policy: its "Enable IAM policies" statement is an unconditional
  # kms:Decrypt for anyone in the account with the IAM permission. This birth policy is the
  # gate without its one allow, and with an all-zero PCR17 in the denies.
  jq --arg acct "$ACCOUNT" --arg pcr "$ZERO_PCR17" '
    del(._comment)
    | .Statement |= map(select(.Sid != "AttestedDecryptOnly"))
    | walk(if type == "string" then gsub("<ACCOUNT_ID>"; $acct) | gsub("<EXPECTED_PCR17>"; $pcr) else . end)
  ' "$ROOT/policy/kms-key-policy.json" > "$TMP/birth-policy.json"
  KEY_ARN="$(aws kms create-key --description "$PREFIX: wraps the GitHub token" \
    --policy "file://$TMP/birth-policy.json" --query KeyMetadata.Arn --output text)"
  aws kms create-alias --alias-name "$KMS_ALIAS" --target-key-id "$KEY_ARN"
fi
state_put KMS_KEY_ARN "$KEY_ARN"
note "key $KEY_ARN"

say "3/7 the GitHub token: typed once, encrypted, forgotten"
if [[ -z "$(state_get GITHUB_TOKEN_CIPHERTEXT)" ]]; then
  # A fine-grained token for GITHUB_REPO only: Contents read and write, Pull requests read
  # and write, nothing else. It never touches a file, a command line or a Kubernetes Secret.
  read -rsp "   paste the fine-grained GitHub token for $GITHUB_REPO, then Enter: " token; echo
  [[ -n "$token" ]] || die "no token given"
  ciphertext="$(aws kms encrypt --key-id "$KEY_ARN" --plaintext fileb://<(printf '%s' "$token") \
    --query CiphertextBlob --output text)"
  unset token
  state_put GITHUB_TOKEN_CIPHERTEXT "$ciphertext"
fi
note "ciphertext stored ($(state_get GITHUB_TOKEN_CIPHERTEXT | wc -c) characters); the token itself is gone"

say "4/7 identities: a broker role with no policies, a brain role for Bedrock only"
trust() {
  jq -n --arg c "$CLUSTER_NAME" --arg n "$1" --arg s "$2" '{
    Version: "2012-10-17",
    Statement: [{Effect: "Allow", Principal: {Service: "pods.eks.amazonaws.com"},
      Action: ["sts:AssumeRole", "sts:TagSession"],
      Condition: {StringEquals: {"aws:RequestTag/eks-cluster-name": $c,
        "aws:RequestTag/kubernetes-namespace": $n, "aws:RequestTag/kubernetes-service-account": $s}}}]}'
}
ensure_role() { # <role> <namespace> <service-account>
  aws iam get-role --role-name "$1" >/dev/null 2>&1 ||
    aws iam create-role --role-name "$1" --assume-role-policy-document "$(trust "$2" "$3")" >/dev/null
  aws eks list-pod-identity-associations --cluster-name "$CLUSTER_NAME" --namespace "$2" \
    --service-account "$3" --query 'associations[0].associationId' --output text | grep -qv None ||
    aws eks create-pod-identity-association --cluster-name "$CLUSTER_NAME" --namespace "$2" \
      --service-account "$3" --role-arn "arn:aws:iam::$ACCOUNT:role/$1" >/dev/null
}
# No identity policy on the broker role: everything it may do is in the KMS key policy,
# next to the attestation condition, so there is no second road to kms:Decrypt.
ensure_role "$PREFIX-broker" agent-broker broker
state_put BROKER_ROLE_ARN "arn:aws:iam::$ACCOUNT:role/$PREFIX-broker"
ensure_role "$PREFIX-brain" agent-brain brain
aws iam put-role-policy --role-name "$PREFIX-brain" --policy-name bedrock-invoke --policy-document '{
  "Version": "2012-10-17",
  "Statement": [{"Effect": "Allow",
    "Action": ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"],
    "Resource": "*"}]}'
sed "s|<AWS_REGION>|$AWS_REGION|" "$ROOT/k8s/broker-service.yaml" | kubectl apply -f - >/dev/null

say "5/7 images, pinned by digest"
state_put BRAIN_IMAGE "$(build_push agent "$ROOT/apps/agent" latest)"
note "agent  $(state_get BRAIN_IMAGE)"
state_put BROKER_IMAGE "$(build_push broker "$ROOT/apps/broker" approved)"
note "broker $(state_get BROKER_IMAGE)"

say "6/7 measure the broker, and gate the key on that measurement"
render_broker_pod "$(state_get BROKER_IMAGE)" "$TMP/approved-pod.json"
PCR17="$(gen_policy "$TMP/approved-pod.json" "$TMP/approved-policy.b64")"
[[ "$PCR17" =~ ^[0123456789abcdef]{96}$ && "$PCR17" != "$ZERO_PCR17" ]] ||
  die "no predicted PCR17 in $TMP/genpolicy.log"
state_put PCR17 "$PCR17"
note "predicted PCR17 $PCR17"
put_key_policy "$PCR17"
note "the key now releases the token to that measurement and nothing else"
sleep 15   # let the key policy reach every KMS host before the broker asks

say "7/7 start the broker"
apply_broker "$TMP/approved-pod.json" "$TMP/approved-policy.b64"
wait_broker
