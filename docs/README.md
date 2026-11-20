# Diagrams

All ten diagrams in reading order. Each PNG has an SVG next to it, and `make_images.py` redraws them all (`pip install cairosvg`, then `python docs/make_images.py`).

## 1. Sandboxed coding agent on EKS
![Cover](images/01-cover.png)

## 2. The problem Nitro Sandboxes solve
Same EC2 node, same pods. Ordinary pods share one Linux kernel; sandboxed pods each get their own.
![Shared kernel](images/02-shared-kernel.png)

## 3. Where a Nitro Sandbox fits
Three ways to get a hardware boundary on AWS: EC2 instances, Nitro Enclaves and Nitro Sandboxes.
![Where it fits](images/03-where-it-fits.png)

## 4. What happens when a pod asks for `runtimeClassName: isolated-sandbox`
![Pod to sandbox](images/04-pod-to-sandbox.png)

## 5. Isolated or confidential: decide who you do not trust
![Isolated vs confidential](images/05-isolated-vs-confidential.png)

## 6. How the broker gets the GitHub token without anyone else seeing it
AWS KMS releases the token only to a sandbox whose measured policy matches the key policy.
![Attestation](images/06-attestation.png)

## 7. The test system: three trust zones for one coding agent
Brain (ordinary pod), hands (isolated sandbox, no network), broker (confidential sandbox, holds the token).
![Architecture](images/07-architecture.png)

## 8. One agent run, step by step
What `scripts/03-run-agent.sh` does.
![Agent run](images/08-agent-run.png)

## 9. Why loosening one rule locks the broker
The broker's rules are baked into its image, the image is pinned in its Cedar policy, and the policy sets PCR17. Change a rule and the KMS key policy no longer matches.
![Measurement chain](images/09-measurement-chain.png)

## 10. Seven experiments, and what each one checks
![Experiments](images/10-experiments.png)
