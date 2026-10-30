"""Guard the Cloudflare Worker's Sec-MS-GEC token against drift.

Microsoft rotated the token scheme in Oct 2026 (v1 hashes are rejected with
HTTP 403). The worker generates v2 tokens in JS, so it must stay byte-for-byte
identical to the reference implementation in the `edge-tts` package.
"""

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
GEC_JS = ROOT / "cloudflare-proxy" / "src" / "gec.js"

TIMESTAMPS = [
    1700000000.0,
    1782000000.0,
    1782000000.5,
    1782000299.999,
    1782000300.0,
    1782000600.0,
]


def test_proxy_declares_v2_version():
    """The worker must advertise the v2 token version, not the retired v1."""
    source = (ROOT / "cloudflare-proxy" / "src" / "index.js").read_text()
    assert 'SEC_MS_GEC_VERSION = "2-' in source
    assert 'SEC_MS_GEC_VERSION = "1-' not in source


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_worker_token_matches_edge_tts():
    edge_tts = pytest.importorskip("edge_tts")
    from edge_tts.drm import generate_sec_ms_gec_v2

    expected = [generate_sec_ms_gec_v2(ts) for ts in TIMESTAMPS]

    script = f"""
import {{ generateSecMsGecV2 }} from {json.dumps(GEC_JS.as_uri())};
const out = {json.dumps(TIMESTAMPS)}.map((ts) => generateSecMsGecV2(ts));
console.log(JSON.stringify(out));
"""
    result = subprocess.run(
        ["node", "--input-type=module", "-e", script],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert result.returncode == 0, result.stderr

    actual = json.loads(result.stdout)
    assert actual == expected
    assert edge_tts  # keep the import meaningful for older versions
