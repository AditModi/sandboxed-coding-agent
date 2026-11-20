#!/usr/bin/env bash
# Download the Cedar policy generator and prove AWS published it.
# You are about to gate a bank token on this tool's output, so check it first.
source "$(dirname "$0")/lib.sh"
need curl openssl sha256sum tar
[[ "$(uname -s)-$(uname -m)" == "Linux-x86_64" ]] ||
  die "this script fetches the Linux x86_64 build; run it on Linux x86_64 or in AWS CloudShell"

BASE="https://d1uvmbvklg8rt.cloudfront.net/latest/x86_64"
WORK="$TMP/genpolicy-download"
rm -rf "$WORK" && mkdir -p "$WORK" && cd "$WORK" || exit 1

say "download the runtime release"
curl -fsSLO "$BASE/nitro-sandboxes-runtime.tar.gz"
curl -fsSLO "$BASE/SHA256SUM"
curl -fsSLO "$BASE/SHA256SUM.sig"

say "verify the signature on the checksum manifest"
# The release signing key from the Amazon EKS User Guide, "Download and verify the runtime
# binaries". ECDSA P-384, so the digest is SHA-384.
cat > nitro-sandboxes-runtime-v1.pub <<'KEY'
-----BEGIN PUBLIC KEY-----
MHYwEAYHKoZIzj0CAQYFK4EEACIDYgAESqdVXO82n+Zh5+IFLh1xjmxZLkjjZWvf
DCS927SdVYjP0AZ92XCxS+ucrs9cjuNlTaDARTHov2XVfMVgau8TEPFKGDRmVZXJ
c25CVihKHLFK8T8hNMIL+fbGcvE2fwIO
-----END PUBLIC KEY-----
KEY
openssl dgst -sha384 -verify nitro-sandboxes-runtime-v1.pub -signature SHA256SUM.sig SHA256SUM

say "verify the archive and the binaries against it"
# Extract into a subfolder so the archive's own SHA256SUM cannot overwrite the signed one.
mkdir -p x && tar -xzf nitro-sandboxes-runtime.tar.gz -C x 2>/dev/null
( cd x && cp ../nitro-sandboxes-runtime.tar.gz . && sha256sum -c ../SHA256SUM )

mkdir -p "$ROOT/.bin"
install -m 0755 x/eks-nitro-sandbox-genpolicy "$ROOT/.bin/"
note "installed $ROOT/.bin/eks-nitro-sandbox-genpolicy"
