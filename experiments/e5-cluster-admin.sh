#!/usr/bin/env bash
# Experiment 5: you are cluster-admin. Get the GitHub token out of the broker.
source "$(dirname "$0")/../scripts/lib.sh"

say "5a: kubectl exec into the broker (RBAC allows it; does the guest?)"
kubectl auth can-i create pods/exec -n agent-broker
kubectl exec -n agent-broker broker -- cat /proc/1/environ 2>&1 | head -3 || true

say "5b: read the token from the pod spec"
CT="$(kubectl get pod broker -n agent-broker \
  -o jsonpath='{.spec.containers[0].env[?(@.name=="GITHUB_TOKEN_CIPHERTEXT")].value}')"
note "GITHUB_TOKEN_CIPHERTEXT = ${CT:0:40}... (${#CT} characters of KMS ciphertext)"

say "5c: your own ordinary pod, as the broker's service account, asks KMS to decrypt"
kubectl delete pod thief -n agent-broker --ignore-not-found --wait=true >/dev/null
kubectl apply -f - >/dev/null <<YAML
apiVersion: v1
kind: Pod
metadata: { name: thief, namespace: agent-broker, labels: { app: thief } }
spec:
  serviceAccountName: broker        # EKS Pod Identity gives this pod the broker's IAM role
  restartPolicy: Never
  securityContext: { runAsUser: 65534, runAsNonRoot: true, seccompProfile: { type: RuntimeDefault } }
  containers:
    - name: aws
      image: public.ecr.aws/aws-cli/aws-cli:2.17.0
      command: ["sh", "-c"]
      args:
        - |
          echo "role: \$(aws sts get-caller-identity --query Arn --output text | sed 's|/[^/]*\$|/<session>|')"
          printf '%s' "\$CT" | base64 -d > /tmp/ct
          if aws kms decrypt --key-id "\$KEY" --ciphertext-blob fileb:///tmp/ct \
               --query Plaintext --output text > /tmp/pt 2> /tmp/err; then
            echo "[FAIL] KMS decrypted it (\$(wc -c < /tmp/pt) bytes, not shown): the key policy is broken"
          else
            echo "[PASS] KMS refused:"; sed 's/[0-9]\{12\}/<ACCOUNT_ID>/g' /tmp/err
          fi
      env:
        - { name: CT, value: "$CT" }
        - { name: KEY, value: "$(state_get KMS_KEY_ARN)" }
        - { name: HOME, value: /tmp }
        - { name: AWS_REGION, value: "$AWS_REGION" }
      securityContext:
        allowPrivilegeEscalation: false
        capabilities: { drop: ["ALL"] }
YAML
kubectl wait pod/thief -n agent-broker --for=jsonpath='{.status.phase}'=Succeeded --timeout=300s >/dev/null || true
kubectl logs thief -n agent-broker
kubectl delete pod thief -n agent-broker --wait=false >/dev/null
