"""What can code see and reach from where it runs? Standard library only.

Experiment 1 runs this in an ordinary pod and in an isolated-sandbox pod side by side.
Experiment 3 runs it inside the agent's hands, the way hostile repository code would run.
Every check prints PASS when the code is contained and FAIL when it is not."""

import os
import socket


def read(path, default="-"):
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read().strip()
    except OSError:
        return default


def reachable(host, port):
    try:
        socket.create_connection((host, port), timeout=3).close()
        return True
    except OSError:
        return False


def resolves(name):
    try:
        socket.getaddrinfo(name, 443)
        return True
    except OSError:
        return False


print("== what this workload sees ==")
print(f"machine:     {read('/sys/class/dmi/id/product_name')}")
print(f"kernel:      {os.uname().release}")
print(f"uptime:      {read('/proc/uptime').split()[0]} s")
print(f"boot id:     {read('/proc/sys/kernel/random/boot_id')}")
print(f"cpus:        {os.cpu_count()}")
print(f"memory:      {read('/proc/meminfo').splitlines()[0].split(':')[1].strip()}")
print(f"disks:       {' '.join(sorted(os.listdir('/sys/block')))}")
print(f"interfaces:  {' '.join(sorted(os.listdir('/sys/class/net')))}")

routes = [l for l in read('/proc/net/route', '').splitlines()[1:] if l.strip()]
creds = sorted(k for k in os.environ if k.startswith("AWS_CONTAINER") or k.startswith("AWS_ACCESS"))
checks = [
    ("no IPv4 route out of the VM", not routes),
    ("DNS cannot resolve github.com", not resolves("github.com")),
    ("no TCP to 1.1.1.1:443", not reachable("1.1.1.1", 443)),
    ("no instance metadata (169.254.169.254)", not reachable("169.254.169.254", 80)),
    ("no Pod Identity endpoint (169.254.170.23)", not reachable("169.254.170.23", 80)),
    ("no Kubernetes service account token",
     not os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")),
    ("no AWS credential variables", not creds),
]
print("== can it get out? ==")
for label, contained in checks:
    print(f"[{'PASS' if contained else 'FAIL'}] {label}")
