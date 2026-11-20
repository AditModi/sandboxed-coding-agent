"""The agent's hands: one throwaway Nitro Sandbox per session.

Each session gets its own pod in agent-hands, with runtimeClassName isolated-sandbox and
the network-isolated annotation, so the VM boots with no network device besides loopback.
Files go in and output comes back over `kubectl exec`, which uses the VM's internal control
channel (vsock), not the network. activeDeadlineSeconds removes the pod even if this
process dies first.
"""

from __future__ import annotations

import base64
import json
import time
import uuid

from kubernetes import client, config
from kubernetes.stream import stream

NAMESPACE = "agent-hands"
IMAGE = "public.ecr.aws/docker/library/python:3.12-slim"
WORKDIR = "/tmp/work"
MAX_OUTPUT = 8000           # characters returned to the model; output is tokens, tokens are money
COMMAND_TIMEOUT_SECONDS = 60
MAX_REPO_BYTES = 90_000     # files travel as one exec argument; Linux caps one argument at 128 KiB


def kube() -> client.CoreV1Api:
    try:
        config.load_incluster_config()
    except config.ConfigException:
        config.load_kube_config()
    return client.CoreV1Api()


def session_pod(name: str, sandboxed: bool = True) -> dict:
    pod = {
        "apiVersion": "v1",
        "kind": "Pod",
        "metadata": {
            "name": name,
            "labels": {"app": "hands", "session": name},
            "annotations": {"sandbox.amazonaws.com/network-isolated": "true"},
        },
        "spec": {
            "runtimeClassName": "isolated-sandbox",
            "restartPolicy": "Never",
            "activeDeadlineSeconds": 1800,
            "automountServiceAccountToken": False,
            "enableServiceLinks": False,
            "terminationGracePeriodSeconds": 0,
            "securityContext": {
                "runAsUser": 65534, "runAsGroup": 65534, "runAsNonRoot": True,
                "seccompProfile": {"type": "RuntimeDefault"},
            },
            "containers": [{
                "name": "work",
                "image": IMAGE,
                "command": ["sleep", "infinity"],
                "env": [{"name": "HOME", "value": "/tmp"}],
                "securityContext": {
                    "allowPrivilegeEscalation": False,
                    "readOnlyRootFilesystem": True,
                    "capabilities": {"drop": ["ALL"]},
                },
                "volumeMounts": [{"name": "scratch", "mountPath": "/tmp"}],
                # The VM is sized from the requests, so ask for what the tests need.
                "resources": {"requests": {"cpu": "1", "memory": "1Gi"},
                              "limits": {"memory": "1Gi"}},
            }],
            "volumes": [{"name": "scratch", "emptyDir": {"sizeLimit": "256Mi"}}],
        },
    }
    if not sandboxed:
        # Only experiment 4 builds this: the first thing a hijacked brain would try.
        del pod["spec"]["runtimeClassName"]
        del pod["metadata"]["annotations"]
    return pod


class Workspace:
    """with Workspace() as ws: ws.load(files); ws.run("python -m unittest")"""

    def __init__(self) -> None:
        self.api = kube()
        self.name = "hands-" + uuid.uuid4().hex[:8]

    def __enter__(self) -> "Workspace":
        started = time.time()
        self.api.create_namespaced_pod(NAMESPACE, session_pod(self.name))
        while time.time() - started < 300:
            phase = self.api.read_namespaced_pod(self.name, NAMESPACE).status.phase
            if phase == "Running":
                print(f"[hands] {self.name} running after {time.time() - started:.1f}s", flush=True)
                return self
            if phase in ("Failed", "Succeeded"):
                break
            time.sleep(1)
        self.close()
        raise RuntimeError(f"hands pod {self.name} did not start")

    def __exit__(self, *exc) -> None:
        self.close()

    def close(self) -> None:
        try:
            self.api.delete_namespaced_pod(self.name, NAMESPACE, grace_period_seconds=0)
            print(f"[hands] {self.name} deleted", flush=True)
        except client.ApiException:
            pass

    def _exec(self, argv: list[str], truncate: bool = True) -> str:
        output = stream(self.api.connect_get_namespaced_pod_exec, self.name, NAMESPACE,
                        command=argv, stderr=True, stdin=False, stdout=True, tty=False)
        if truncate and len(output) > MAX_OUTPUT:
            output = output[:MAX_OUTPUT] + f"\n[truncated {len(output) - MAX_OUTPUT} characters]"
        return output

    def _python(self, code: str, *args: str, truncate: bool = True) -> str:
        # Code and data are separate argv entries, never pasted into a shell string.
        return self._exec(["python3", "-c", code, *args], truncate=truncate)

    def load(self, files: dict[str, str]) -> None:
        blob = base64.b64encode(json.dumps(files).encode()).decode()
        if len(blob) > MAX_REPO_BYTES:
            raise ValueError("repository too large to load over one exec argument")
        self._python(
            "import base64, json, os, sys\n"
            f"root = {WORKDIR!r}\n"
            "for path, text in json.loads(base64.b64decode(sys.argv[1])).items():\n"
            "    full = os.path.join(root, path)\n"
            "    os.makedirs(os.path.dirname(full), exist_ok=True)\n"
            "    open(full, 'w', encoding='utf-8').write(text)\n",
            blob,
        )

    def run(self, command: str) -> str:
        # The command becomes $0 of the inner shell; the outer shell never parses it.
        return self._exec(["sh", "-c",
                           f'cd {WORKDIR} && timeout {COMMAND_TIMEOUT_SECONDS} sh -c "$0"; '
                           'echo "[exit code $?]"', command])

    def read(self, path: str, truncate: bool = True) -> str:
        return self._python(
            "import os, sys\n"
            f"root = os.path.realpath({WORKDIR!r})\n"
            "full = os.path.realpath(os.path.join(root, sys.argv[1]))\n"
            "assert full.startswith(root + os.sep), 'path outside the workspace'\n"
            "print(open(full, encoding='utf-8').read(), end='')\n",
            path, truncate=truncate,
        )

    def write(self, path: str, content: str) -> str:
        return self._python(
            "import base64, os, sys\n"
            f"root = os.path.realpath({WORKDIR!r})\n"
            "full = os.path.realpath(os.path.join(root, sys.argv[1]))\n"
            "assert full.startswith(root + os.sep), 'path outside the workspace'\n"
            "os.makedirs(os.path.dirname(full), exist_ok=True)\n"
            "open(full, 'w', encoding='utf-8').write(base64.b64decode(sys.argv[2]).decode())\n"
            "print('written', sys.argv[1])\n",
            path, base64.b64encode(content.encode()).decode(),
        )
