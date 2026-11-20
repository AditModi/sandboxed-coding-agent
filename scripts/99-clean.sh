#!/usr/bin/env bash
# Remove everything this repo created. Pass --cluster to delete the cluster too.
# On GitHub, revoke the token yourself and close the agent's pull requests.
source "$(dirname "$0")/lib.sh"
set +e

say "Kubernetes objects"
kubectl delete namespace agent-brain agent-hands agent-broker lab-probe --ignore-not-found --wait=false
kubectl delete -f "$ROOT/k8s/hands-guardrail.yaml" --ignore-not-found

say "Pod Identity associations and IAM roles"
for pair in agent-broker:broker agent-brain:brain; do
  for id in $(aws eks list-pod-identity-associations --cluster-name "$CLUSTER_NAME" \
      --namespace "${pair%%:*}" --service-account "${pair##*:}" \
      --query 'associations[].associationId' --output text 2>/dev/null); do
    aws eks delete-pod-identity-association --cluster-name "$CLUSTER_NAME" --association-id "$id" >/dev/null
  done
done
aws iam delete-role-policy --role-name "$PREFIX-brain" --policy-name bedrock-invoke 2>/dev/null
aws iam delete-role --role-name "$PREFIX-brain" 2>/dev/null
aws iam delete-role --role-name "$PREFIX-broker" 2>/dev/null

say "ECR repositories"
for repo in agent broker; do
  aws ecr delete-repository --repository-name "$PREFIX-$repo" --force >/dev/null 2>&1
done

say "KMS key (7 days is the shortest wait KMS allows)"
KEY="$(state_get KMS_KEY_ARN)"
if [[ -n "$KEY" ]]; then
  aws kms delete-alias --alias-name "$KMS_ALIAS" 2>/dev/null
  aws kms schedule-key-deletion --key-id "$KEY" --pending-window-in-days 7 \
    --query DeletionDate --output text
fi
rm -rf "$STATE" "$TMP"

if [[ "${1:-}" == "--cluster" ]]; then
  say "the cluster"
  eksctl delete cluster --name "$CLUSTER_NAME" --region "$AWS_REGION"
fi
