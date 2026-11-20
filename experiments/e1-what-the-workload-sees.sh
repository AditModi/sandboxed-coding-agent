#!/usr/bin/env bash
# Experiment 1: the same probe in three pods on the same cluster. Only the runtime class and
# one annotation differ. Compare what each one sees.
source "$(dirname "$0")/../scripts/lib.sh"

say "three pods: ordinary, isolated-sandbox, isolated-sandbox with no network"
kubectl create namespace lab-probe --dry-run=client -o yaml | kubectl apply -f - >/dev/null
kubectl create configmap probe -n lab-probe --from-file="$ROOT/apps/agent/experiments/probe.py" \
  --dry-run=client -o yaml | kubectl apply -f - >/dev/null
for variant in ordinary isolated isolated-no-network; do
  runtime="isolated-sandbox"; annotation=""
  [[ "$variant" == ordinary ]] && runtime=""
  [[ "$variant" == isolated-no-network ]] && annotation='sandbox.amazonaws.com/network-isolated: "true"'
  kubectl delete pod "$variant" -n lab-probe --ignore-not-found --wait=true >/dev/null
  kubectl apply -f - >/dev/null <<YAML
apiVersion: v1
kind: Pod
metadata:
  name: $variant
  namespace: lab-probe
  annotations: { $annotation }
spec:
  ${runtime:+runtimeClassName: $runtime}
  automountServiceAccountToken: false
  restartPolicy: Never
  containers:
    - name: probe
      image: public.ecr.aws/docker/library/python:3.12-slim
      command: ["sh", "-c", "python3 /probe/probe.py; sleep 600"]
      resources: { requests: { cpu: 500m, memory: 512Mi } }
      volumeMounts: [{ name: probe, mountPath: /probe }]
  volumes: [{ name: probe, configMap: { name: probe } }]
YAML
done
kubectl wait pod --all -n lab-probe --for=condition=Ready --timeout=600s >/dev/null
sleep 5
for variant in ordinary isolated isolated-no-network; do
  say "$variant (pod age $(kubectl get pod "$variant" -n lab-probe -o jsonpath='{.status.startTime}'))"
  kubectl logs "$variant" -n lab-probe
done
note "clean up with: kubectl delete namespace lab-probe"
