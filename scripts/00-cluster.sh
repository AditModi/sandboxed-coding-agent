#!/usr/bin/env bash
# An EKS Auto Mode cluster on Kubernetes 1.36, with network policy enforced.
# About 15 minutes. Skip it if you already have an Auto Mode cluster on 1.36 or later.
source "$(dirname "$0")/lib.sh"
need eksctl kubectl aws

say "create the cluster $CLUSTER_NAME in $AWS_REGION"
# --version matters: eksctl's default is older than 1.36, and Nitro Sandboxes need 1.36+.
eksctl create cluster --name "$CLUSTER_NAME" --region "$AWS_REGION" \
  --version 1.36 --enable-auto-mode

say "turn on network policy enforcement"
# Auto Mode accepts NetworkPolicy objects without enforcing them until this is on.
kubectl patch configmap -n kube-system amazon-vpc-cni --type merge \
  -p '{"data":{"enable-network-policy-controller":"true"}}'

say "the two runtime classes Auto Mode ships"
kubectl get runtimeclass isolated-sandbox confidential-sandbox
