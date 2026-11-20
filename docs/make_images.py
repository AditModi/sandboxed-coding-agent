"""Draws every image in docs/images as SVG and PNG. python docs/make_images.py"""

import os

import cairosvg

OUT = os.path.join(os.path.dirname(__file__), "images")
SANS, MONO = "Inter, DejaVu Sans, sans-serif", "DejaVu Sans Mono, monospace"
INK, MUTED, LINE, PAPER, SOFT = "#1B2433", "#5B6475", "#C9CFDA", "#FFFFFF", "#F3F5F8"
ISO, ISO_BG = "#0B7A6B", "#E3F4F1"
CONF, CONF_BG = "#5B3FB0", "#EEE9FB"
RED, RED_BG = "#B83A26", "#FBE9E5"
AMBER, AMBER_BG = "#9A6200", "#FFF4DC"
NIGHT = "#121A2B"
ARROWS = (MUTED, ISO, CONF, RED, INK, AMBER)


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def t(x, y, s, size=20, weight=400, fill=INK, anchor="start", mono=False):
    fam = MONO if mono else SANS
    return (f'<text x="{x}" y="{y}" font-family="{fam}" font-size="{size}" font-weight="{weight}" '
            f'fill="{fill}" text-anchor="{anchor}">{esc(s)}</text>')


def lines(x, y, rows, size=19, gap=30, fill=INK, mono=False, weight=400):
    return "".join(t(x, y + i * gap, r, size, weight, fill, mono=mono) for i, r in enumerate(rows))


def rect(x, y, w, h, fill=PAPER, stroke=LINE, r=14, sw=2, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{r}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{sw}"{d}/>')


def arrow(x1, y1, x2, y2, color=MUTED, sw=2.5, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{sw}" '
            f'marker-end="url(#a{color[1:]})"{d}/>')


def badge(x, y, n, color=INK):
    return (f'<circle cx="{x}" cy="{y}" r="17" fill="{color}"/>'
            + t(x, y + 7, str(n), 18, 700, PAPER, "middle"))


def title(main, sub):
    return t(60, 72, main, 34, 700) + t(60, 110, sub, 20, 400, MUTED)


def svg(w, h, body, bg=PAPER):
    markers = "".join(
        f'<marker id="a{c[1:]}" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="8" markerHeight="8" '
        f'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="{c}"/></marker>' for c in ARROWS + ("#F2B84B",))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<defs>{markers}</defs><rect width="{w}" height="{h}" fill="{bg}"/>{body}</svg>')


def lock(cx, cy, color, s=1.0):
    return (f'<g transform="translate({cx},{cy}) scale({s})"><path d="M-14,-4 v-10 a14,14 0 0 1 28,0 v10" '
            f'fill="none" stroke="{color}" stroke-width="5"/><rect x="-22" y="-6" width="44" height="34" rx="6" '
            f'fill="{color}"/><circle cx="0" cy="8" r="5" fill="{PAPER}"/></g>')


def save(name, content):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, name + ".svg"), "w", encoding="utf-8") as handle:
        handle.write(content)
    cairosvg.svg2png(bytestring=content.encode(), write_to=os.path.join(OUT, name + ".png"))


# 01 cover ---------------------------------------------------------------------------------
def cover():
    b = [t(90, 150, "Untrusted code, trusted token", 60, 700, PAPER),
         t(90, 225, "An AI coding agent on Amazon EKS with AWS Nitro Sandboxes", 34, 500, "#F2B84B"),
         t(90, 280, "What isolated and confidential mode protect, tested one experiment at a time", 24, 400, "#AEB8CC")]
    zones = [(90, "BRAIN", "ordinary pod", ["talks to the model", "holds no secret"], "#2A3550", "#AEB8CC"),
             (590, "HANDS", "isolated-sandbox", ["runs repo code and tests", "no network device"], ISO, "#BFEDE5"),
             (1090, "BROKER", "confidential-sandbox", ["holds the GitHub token", "only opens pull requests"], CONF, "#DCD2FA")]
    for x, name, rc, rows, col, light in zones:
        b.append(rect(x, 360, 420, 270, col, col, 20))
        b.append(t(x + 36, 420, name, 34, 700, PAPER))
        b.append(t(x + 36, 460, rc, 22, 500, light, mono=True))
        b.append(lines(x + 36, 560, rows, 22, 34, PAPER))
    b.append(lock(1450, 425, PAPER, 1.3))
    b.append(t(90, 760, "Adit Modi", 26, 600, PAPER))
    b.append(t(90, 796, "AWS User Group Leader · AWS Ambassador", 20, 400, "#AEB8CC"))
    save("01-cover", svg(1600, 840, "".join(b), NIGHT))


# 02 shared kernel vs own kernel ------------------------------------------------------------
def shared_kernel():
    W, H = 1600, 900
    b = [title("The problem Nitro Sandboxes solve",
               "Same EC2 node, same pods. On the left they share one Linux kernel. On the right each pod has its own.")]
    for x, head, sandboxed in ((50, "Ordinary pods (runc)", False), (820, "Sandboxed pods (runtimeClassName)", True)):
        b.append(rect(x, 150, 730, 690, SOFT, LINE, 22, 2, "8 6"))
        b.append(t(x + 30, 195, head, 24, 700))
        b.append(t(x + 30, 225, "one EC2 instance, EKS node", 17, 400, MUTED))
        names = ["agent session A", "agent session B", "some other team"]
        for i, n in enumerate(names):
            px = x + 30 + i * 230
            if sandboxed:
                b.append(rect(px - 8, 255, 216, 330, ISO_BG, ISO, 14, 2.5))
                b.append(t(px + 100, 285, "Nitro Sandbox (VM)", 15, 600, ISO, "middle"))
                b.append(rect(px + 10, 305, 180, 120, PAPER, LINE, 10))
                b.append(t(px + 100, 360, "container", 18, 600, INK, "middle"))
                b.append(t(px + 100, 388, n, 15, 400, MUTED, "middle"))
                b.append(rect(px + 10, 445, 180, 120, ISO, ISO, 10))
                b.append(t(px + 100, 500, "its own kernel", 17, 600, PAPER, "middle"))
                b.append(t(px + 100, 528, "boots with the pod", 14, 400, "#BFEDE5", "middle"))
            else:
                b.append(rect(px + 10, 305, 180, 120, PAPER, LINE, 10))
                b.append(t(px + 100, 360, "container", 18, 600, INK, "middle"))
                b.append(t(px + 100, 388, n, 15, 400, MUTED, "middle"))
                b.append(arrow(px + 100, 428, px + 100, 470, RED))
        if not sandboxed:
            b.append(rect(x + 40, 475, 650, 110, RED_BG, RED, 12, 2.5))
            b.append(t(x + 365, 520, "ONE shared Linux kernel", 22, 700, RED, "middle"))
            b.append(t(x + 365, 552, "a bug reachable from one pod is reachable from all", 17, 400, INK, "middle"))
        b.append(rect(x + 30, 620, 670, 80, PAPER, LINE, 12))
        b.append(t(x + 365, 668, "Nitro Hypervisor (hardware-enforced CPU and memory)", 18, 600, INK, "middle"))
        b.append(t(x + 30, 745, "What changes:" if sandboxed else "What you rely on:", 18, 700, ISO if sandboxed else RED))
        rows = (["a kernel bug stays inside one pod's VM", "the node and neighbours are protected from the pod",
                 "first-level guest, no nested virtualization"] if sandboxed else
                ["namespaces, cgroups, seccomp on one kernel", "cluster-admin can exec into any pod",
                 "the node can read every pod's memory"])
        b.append(lines(x + 30, 777, rows, 17, 26))
    save("02-shared-kernel", svg(W, H, "".join(b)))


# 03 where it fits --------------------------------------------------------------------------
def where_it_fits():
    W, H = 1600, 930
    b = [title("Where a Nitro Sandbox fits", "Three ways to get a hardware boundary on AWS. Source: AWS Compute Blog, 10 Nov 2026.")]
    cols = [("EC2 instance", INK, SOFT), ("Nitro Enclave", AMBER, AMBER_BG),
            ("Nitro Sandbox", ISO, ISO_BG), ("Nitro Sandbox", CONF, CONF_BG)]
    subs = ["a whole VM", "since 2020", "isolated mode on EKS", "confidential mode on EKS"]
    rowsets = [
        ("Unit of isolation", ["one instance", "carved from an instance", "one pod, child of an instance", "one pod, child of an instance"]),
        ("CPU", ["its own vCPUs", "dedicated full cores", "time-shared with parent", "time-shared with parent"]),
        ("Network and disk", ["ENI, EBS, instance store", "none: vsock channel only", "virtio net and block", "virtio net and block"]),
        ("Who is trusted", ["you and your admins", "only the enclave code", "the node (exec, logs work)", "only the pod (no exec)"]),
        ("Attestation to KMS", ["no", "yes", "no", "yes (PCR17 = policy)"]),
        ("Good for", ["anything", "keys and crypto only", "untrusted code, CI jobs", "secrets, tenant data"]),
    ]
    x0, cw = 330, 315
    for i, (name, col, bg) in enumerate(cols):
        x = x0 + i * cw
        b.append(rect(x, 140, cw - 15, 750, bg, col, 16, 2))
        b.append(t(x + 20, 185, name, 24, 700, col))
        b.append(t(x + 20, 213, subs[i], 16, 500, MUTED))
    for r, (label, cells) in enumerate(rowsets):
        y = 280 + r * 102
        b.append(t(60, y, label, 20, 700))
        b.append(f'<line x1="60" y1="{y - 38}" x2="1550" y2="{y - 38}" stroke="{LINE}" stroke-width="1"/>')
        for i, c in enumerate(cells):
            b.append(t(x0 + i * cw + 20, y, c, 17, 400))
    save("03-where-it-fits", svg(W, H, "".join(b)))


# 04 how a pod becomes a sandbox ----------------------------------------------------------
def pod_to_sandbox():
    W, H = 1600, 1000
    b = [title("What happens when a pod asks for runtimeClassName: isolated-sandbox",
               "Components from the Amazon EKS User Guide, 'How it works'. Same path for confidential-sandbox.")]
    b.append(rect(50, 150, 700, 660, SOFT, LINE, 22, 2, "8 6"))
    b.append(t(80, 192, "Parent EC2 instance (the EKS node)", 20, 700, MUTED))
    steps = [("kubelet", "sees runtimeClassName on the pod"), ("containerd", "the node's container runtime"),
             ("containerd-shim-nitro-sandbox-v2", "launches one sandbox per pod"),
             ("Firecracker", "VMM with virtio-vsock, -blk, -net")]
    for i, (name, sub) in enumerate(steps):
        y = 225 + i * 140
        b.append(rect(100, y, 600, 100, PAPER, LINE, 12))
        b.append(t(130, y + 45, name, 22, 700, mono=(i == 2)))
        b.append(t(130, y + 77, sub, 17, 400, MUTED))
        if i < 3:
            b.append(arrow(400, y + 102, 400, y + 136, INK))
    b.append(rect(850, 150, 700, 660, ISO_BG, ISO, 22, 3))
    b.append(t(880, 192, "Nitro Sandbox (a first-level guest VM, one per pod)", 20, 700, ISO))
    inner = [("nitro-sandbox-agent", "checks the pod's Cedar policy first"), ("containerd (inside)", "loads the images into the guest"),
             ("your containers", "share the guest kernel only")]
    for i, (name, sub) in enumerate(inner):
        y = 225 + i * 140
        b.append(rect(900, y, 600, 100, PAPER, ISO, 12))
        b.append(t(930, y + 45, name, 22, 700, mono=(i == 0)))
        b.append(t(930, y + 77, sub, 17, 400, MUTED))
        if i < 2:
            b.append(arrow(1200, y + 102, 1200, y + 136, ISO))
    b.append(rect(900, 655, 600, 100, ISO, ISO, 12))
    b.append(t(1200, 700, "guest Linux kernel", 22, 700, PAPER, "middle"))
    b.append(t(1200, 730, "owned by this pod alone", 17, 400, "#BFEDE5", "middle"))
    b.append(arrow(702, 705, 896, 705, ISO, 3))
    b.append(t(800, 690, "boots", 15, 600, ISO, "middle"))
    b.append(t(800, 735, "vsock", 15, 600, ISO, "middle"))
    b.append(rect(50, 840, 1500, 120, NIGHT, NIGHT, 14))
    b.append(t(800, 892, "Nitro Hypervisor", 26, 700, PAPER, "middle"))
    b.append(t(800, 930, "enforces CPU and memory isolation between the parent and every sandbox, in hardware", 18, 400, "#AEB8CC", "middle"))
    save("04-pod-to-sandbox", svg(W, H, "".join(b)))


# 05 isolated vs confidential -----------------------------------------------------------------
def modes():
    W, H = 1600, 1000
    b = [title("Isolated or confidential: decide who you do not trust",
               "Built-in Cedar policy profiles, from the Amazon EKS User Guide, 'Run a pod in confidential mode'.")]
    for x, name, col, bg, q, protects in (
            (60, "isolated-sandbox", ISO, ISO_BG, "I don't trust the code in the pod.", "the node and other pods, from the pod"),
            (820, "confidential-sandbox", CONF, CONF_BG, "I don't trust the node or its operators.", "the pod's data, from the node")):
        b.append(rect(x, 150, 720, 210, bg, col, 18, 3))
        b.append(t(x + 30, 205, name, 28, 700, col, mono=True))
        b.append(t(x + 30, 255, q, 22, 600))
        b.append(t(x + 30, 300, "Protects: " + protects, 19, 400))
        b.append(t(x + 30, 335, "Trust boundary: " + ("the host" if col == ISO else "the guest"), 19, 400, MUTED))
    rows = [("Pins image digest, args, env, mounts", "no", "yes"),
            ("kubectl exec", "allowed", "denied"),
            ("stdin", "allowed", "denied"),
            ("Logs", "allowed", "allowed"),
            ("Instance metadata and Pod Identity", "allowed", "allowed"),
            ("Writable layer encrypted", "no", "yes"),
            ("Cedar policy needed", "optional", "required"),
            ("KMS can gate keys on PCR17", "no", "yes")]
    b.append(t(60, 420, "Setting", 19, 700, MUTED))
    b.append(t(880, 420, "isolated", 19, 700, ISO))
    b.append(t(1220, 420, "confidential", 19, 700, CONF))
    for i, (label, a, c) in enumerate(rows):
        y = 470 + i * 58
        b.append(f'<line x1="60" y1="{y - 35}" x2="1540" y2="{y - 35}" stroke="{LINE}" stroke-width="1"/>')
        b.append(t(60, y, label, 20))
        for x, v, col in ((880, a, ISO), (1220, c, CONF)):
            good = v in ("yes", "denied", "required")
            b.append(t(x, y, v, 20, 700 if good else 400, col if good else INK))
    save("05-isolated-vs-confidential", svg(W, H, "".join(b)))


# 06 attestation sequence -------------------------------------------------------------------
def attestation():
    W, H = 1600, 900
    b = [title("How the broker gets the GitHub token without anyone else seeing it",
               "Attested kms:Decrypt. The code is AttestedRecipient from the AWS blueprints, used unchanged.")]
    lanes = [(220, "broker process", CONF), (660, "Nitro Secure Module", AMBER), (1100, "AWS KMS", INK)]
    for x, name, col in lanes:
        b.append(rect(x - 150, 140, 300, 64, PAPER, col, 12, 2.5))
        b.append(t(x, 181, name, 20, 700, col, "middle"))
        b.append(f'<line x1="{x}" y1="206" x2="{x}" y2="860" stroke="{LINE}" stroke-width="2" stroke-dasharray="6 6"/>')
    def self_step(x, y, n, label, col):
        return badge(x - 40, y, n, col) + rect(x + 14, y - 24, 520, 46, PAPER, col, 10, 1.5) + t(x + 30, y + 6, label, 17, 500)
    def msg(x1, x2, y, n, label, col):
        return (badge(min(x1, x2) - 40, y, n, col) + arrow(x1, y, x2 + (-6 if x2 > x1 else 6), y, col, 3)
                + t((x1 + x2) / 2, y - 14, label, 17, 600, col, "middle"))
    b.append(self_step(220, 260, 1, "make a fresh RSA key pair, in memory only", CONF))
    b.append(msg(220, 660, 350, 2, "/dev/nsm: sign my measurements and my public key", AMBER))
    b.append(msg(660, 220, 430, 3, "attestation document: PCR0, PCR8, PCR17 + public key", AMBER))
    b.append(msg(220, 1100, 520, 4, "kms:Decrypt(ciphertext, Recipient = attestation document)", CONF))
    b.append(badge(1140, 600, 5, INK) + rect(700, 576, 386, 46, PAPER, INK, 10, 1.5)
             + t(716, 606, "PCR17 + PCR8 match the key policy?", 17, 500))
    b.append(msg(1100, 220, 690, 6, "CiphertextForRecipient: token encrypted to that public key", INK))
    b.append(self_step(220, 780, 7, "open it with the private key, which never left the process", CONF))
    b.append(rect(1180, 660, 380, 200, RED_BG, RED, 12, 2))
    b.append(lines(1200, 698, ["The node carries these calls", "but sees only ciphertext. It", "never holds the private key,",
                               "so it cannot open step 6.", "Same for anyone holding the", "broker's IAM role elsewhere."], 17, 27))
    save("06-attestation", svg(W, H, "".join(b)))


# 07 architecture ---------------------------------------------------------------------------
def architecture():
    W, H = 1600, 1000
    b = [title("The test system: three trust zones for one coding agent",
               "One EKS Auto Mode cluster. Outside it: Amazon Bedrock, AWS KMS and GitHub.")]
    b.append(rect(40, 150, 1090, 800, SOFT, LINE, 22, 2, "8 6"))
    b.append(t(70, 192, "EKS cluster (Auto Mode, Kubernetes 1.36)", 20, 600, MUTED))
    b.append(rect(80, 230, 330, 260))
    b.append(t(110, 278, "Brain", 28, 700))
    b.append(t(110, 308, "ordinary pod · agent-brain", 17, 400, MUTED))
    b.append(lines(110, 350, ["agent loop on Bedrock", "repo: public download", "no GitHub token",
                              "can create pods only in", "agent-hands"], 18, 27))
    b.append(rect(80, 600, 480, 320, ISO_BG, ISO, 16, 3))
    b.append(t(110, 648, "Hands", 28, 700, ISO))
    b.append(t(110, 678, "isolated-sandbox + network-isolated", 16, 400, ISO, mono=True))
    b.append(lines(110, 722, ["one VM per agent session", "repo files, tests, model's commands",
                              "loopback only, no route, no DNS", "admission policy forces this spec",
                              "deleted at the end of the session"], 18, 32))
    b.append(rect(620, 400, 470, 480, CONF_BG, CONF, 16, 3))
    b.append(t(650, 450, "Broker", 28, 700, CONF))
    b.append(t(650, 480, "confidential-sandbox", 16, 400, CONF, mono=True))
    b.append(lines(650, 530, ["the only holder of the GitHub token", "token released by KMS after attestation",
                              "rules baked into the image:", "  new branch under agent/ only", "  never .github/ or CODEOWNERS",
                              "  never a different repo or base", "kubectl exec denied by Cedar policy"], 18, 34))
    b.append(lock(1045, 450, CONF, 0.9))
    outs = [(1200, 230, "Amazon Bedrock", "the model"), (1200, 470, "AWS KMS", "checks the attestation"),
            (1200, 720, "GitHub", "PRs only via the broker")]
    for x, y, n, s in outs:
        b.append(rect(x, y, 350, 130))
        b.append(t(x + 30, y + 58, n, 24, 700))
        b.append(t(x + 30, y + 92, s, 18, 400, MUTED))
    b.append(arrow(412, 290, 1196, 290))
    b.append(t(800, 278, "Converse API", 17, 500, MUTED, "middle"))
    b.append(arrow(240, 492, 240, 596, ISO))
    b.append(t(254, 540, "kubectl exec over vsock", 17, 500, ISO))
    b.append(arrow(412, 460, 616, 500, CONF))
    b.append(t(420, 520, "POST /pull-requests", 16, 500, CONF))
    b.append(arrow(1092, 535, 1196, 535, CONF))
    b.append(t(1145, 505, "attested", 15, 600, CONF, "middle"))
    b.append(t(1145, 523, "Decrypt", 15, 600, CONF, "middle"))
    b.append(arrow(1092, 790, 1196, 790, CONF))
    b.append(t(1145, 760, "HTTPS +", 15, 600, CONF, "middle"))
    b.append(t(1145, 778, "token", 15, 600, CONF, "middle"))
    save("07-architecture", svg(W, H, "".join(b)))


# 08 one agent run --------------------------------------------------------------------------
def agent_run():
    W, H = 1600, 820
    b = [title("One agent run, step by step", "What scripts/03-run-agent.sh does. Green happens in the hands, purple in the broker.")]
    steps = [("1", "Brain downloads the repo", "public tarball from GitHub, no token", INK, PAPER),
             ("2", "Hands session starts", "new isolated VM, no network", ISO, ISO_BG),
             ("3", "Files go in", "one exec call, base64 argument", ISO, ISO_BG),
             ("4", "Model runs the tests", "3 tests fail: wrong grouping", ISO, ISO_BG),
             ("5", "Model edits money.py", "write_file in the hands", ISO, ISO_BG),
             ("6", "Tests run again", "all pass; the hostile test runs too", ISO, ISO_BG),
             ("7", "Brain reads changed files", "from the hands, full content", INK, PAPER),
             ("8", "Broker checks the rules", "branch, paths, size, fields", CONF, CONF_BG),
             ("9", "Broker opens the PR", "agent/<name> into main", CONF, CONF_BG),
             ("10", "Hands VM is deleted", "nothing from the session remains", ISO, ISO_BG)]
    for i, (n, head, sub, col, bg) in enumerate(steps):
        row, colm = divmod(i, 5)
        x, y = 60 + colm * 300, 170 + row * 300
        b.append(rect(x, y, 270, 210, bg, col, 14, 2.5))
        b.append(badge(x + 36, y + 40, n, col))
        b.append(t(x + 22, y + 100, head, 19, 700))
        words, cur, out = sub.split(), "", []
        for w in words:
            if len(cur) + len(w) > 26:
                out.append(cur.strip()); cur = ""
            cur += w + " "
        out.append(cur.strip())
        b.append(lines(x + 22, y + 140, out, 16, 24, MUTED))
        if colm < 4:
            b.append(arrow(x + 272, y + 105, x + 296, y + 105, INK, 2))
    b.append(arrow(1440, 382, 200, 466, INK, 2, "6 6"))
    b.append(t(60, 790, "The model never sees the token. The token never enters the hands. The hands never touch the network.", 20, 600, INK))
    save("08-agent-run", svg(W, H, "".join(b)))


# 09 measurement chain ----------------------------------------------------------------------
def chain():
    W, H = 1600, 700
    b = [title("Why loosening one rule locks the broker",
               "Each value is computed from the one before. Change anything on the left and the right side stops matching.")]
    steps = [("broker image", ["app.py, rules.py", "broker-policy.json", "pinned libraries"], SOFT, INK),
             ("image digest", ["sha256 in ECR", "the pod uses the", "digest, not a tag"], SOFT, INK),
             ("Cedar policy", ["pins digest, env,", "args, mounts, user", "(genpolicy)"], SOFT, INK),
             ("PCR17", ["measured inside the", "sandbox, signed by", "the Nitro module"], CONF_BG, CONF),
             ("KMS key policy", ["Decrypt only if", "PCR17 matches and", "PCR8 is EKS-signed"], CONF_BG, CONF),
             ("GitHub token", ["encrypted to this", "sandbox's own key", ""], CONF_BG, CONF)]
    for i, (head, rows, bg, col) in enumerate(steps):
        x = 50 + i * 250
        b.append(rect(x, 170, 225, 250, bg, col if bg != SOFT else LINE, 14, 2))
        b.append(t(x + 20, 218, head, 23, 700, col))
        b.append(lines(x + 20, 266, rows, 18, 32))
        if i < 5:
            b.append(arrow(x + 227, 295, x + 248, 295, INK))
    b.append(rect(50, 470, 1500, 170, RED_BG, RED, 14, 2))
    b.append(t(80, 520, "Experiment 7: an insider removes \".github/\" from denied_path_prefixes and redeploys properly.", 21, 700, RED))
    b.append(t(80, 562, "New image → new digest → new policy → new PCR17 → KMS refuses → the broker exits and opens nothing.", 20, 400))
    b.append(t(80, 600, "To finish the job, the insider also needs kms:PutKeyPolicy on this key: a separate permission, logged in CloudTrail.", 20, 400))
    save("09-measurement-chain", svg(W, H, "".join(b)))


# 10 experiments ----------------------------------------------------------------------------
def experiments():
    W, H = 1600, 1080
    b = [title("Seven experiments, and what each one checks", "Each script prints PASS or FAIL lines, or the exact refusal it got.")]
    head = [(60, "#"), (120, "Script"), (560, "Question"), (1100, "Answer comes from")]
    for x, s in head:
        b.append(t(x, 175, s, 19, 700, MUTED))
    rows = [
        ("1", "e1-what-the-workload-sees.sh", ["What does a pod see in each mode?", "kernel, machine, disks, network"], "runtime class", INK),
        ("2", "03-run-agent.sh", ["Can the agent still do its job?", "fix the bug, open a pull request"], "the whole design", INK),
        ("3", "e3-hostile-code.sh", ["Can code in the hands get out?", "DNS, TCP, metadata, credentials"], "network-isolated", ISO),
        ("4", "e4-hijacked-brain.sh", ["Can a hijacked brain start an", "unsandboxed pod?"], "admission policy + RBAC", ISO),
        ("5", "e5-cluster-admin.sh", ["Can cluster-admin read the token?", "exec, pod spec, same IAM role"], "Cedar policy + KMS", CONF),
        ("6", "e6-forged-requests.sh", ["Can a hijacked brain push", "workflows or go to main?"], "broker rules", CONF),
        ("7", "e7-insider-change.sh", ["Can an insider loosen the rules", "and redeploy?"], "attestation (PCR17)", CONF),
    ]
    for i, (n, script, q, layer, col) in enumerate(rows):
        y = 245 + i * 115
        b.append(f'<line x1="50" y1="{y - 45}" x2="1550" y2="{y - 45}" stroke="{LINE}" stroke-width="1"/>')
        b.append(badge(78, y - 7, n, col))
        b.append(t(120, y, script, 17, 500, mono=True))
        b.append(lines(560, y, q, 19, 28))
        b.append(t(1100, y, layer, 19, 700, col))
    b.append(t(60, 1040, "Not on this list on purpose: what a compromised node can still do. The article has a section on that.", 19, 500, RED))
    save("10-experiments", svg(W, H, "".join(b)))


if __name__ == "__main__":
    for fn in (cover, shared_kernel, where_it_fits, pod_to_sandbox, modes, attestation, architecture,
               agent_run, chain, experiments):
        fn()
    print("\n".join(sorted(f for f in os.listdir(OUT) if f.endswith(".png"))))
