"""The real RFC 3161 code path, against a throwaway OpenSSL timestamp authority served on
localhost. No network: the same openssl commands, request format and verification the
production authorities go through."""

import http.server
import subprocess
import tempfile
import threading
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from kod.timestamp import Authority, RFC3161Timestamper, TimestampError

TSA_CONFIG = """
[ tsa ]
default_tsa = tsa_config1

[ tsa_config1 ]
dir = {dir}
serial = $dir/serial
crypto_device = builtin
signer_cert = $dir/tsa.crt
certs = $dir/ca.crt
signer_key = $dir/tsa.key
signer_digest = sha256
default_policy = 1.2.3.4.1
digests = sha256
accuracy = secs:1
ordering = yes
tsa_name = yes
ess_cert_id_chain = no
ess_cert_id_alg = sha256
"""


def sh(*args, cwd):
    subprocess.run(list(args), cwd=cwd, check=True, capture_output=True)


class LocalAuthority:
    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.dir = d
        sh(
            "openssl",
            "req",
            "-x509",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            "ca.key",
            "-out",
            "ca.crt",
            "-subj",
            "/CN=KOD Test CA",
            "-days",
            "2",
            "-addext",
            "basicConstraints=critical,CA:TRUE",
            "-addext",
            "keyUsage=critical,keyCertSign,cRLSign",
            cwd=d,
        )
        sh(
            "openssl",
            "req",
            "-newkey",
            "rsa:2048",
            "-nodes",
            "-keyout",
            "tsa.key",
            "-out",
            "tsa.csr",
            "-subj",
            "/CN=KOD Test TSA",
            cwd=d,
        )
        (d / "ext.cnf").write_text(
            "extendedKeyUsage=critical,timeStamping\nkeyUsage=critical,digitalSignature\n"
        )
        sh(
            "openssl",
            "x509",
            "-req",
            "-in",
            "tsa.csr",
            "-CA",
            "ca.crt",
            "-CAkey",
            "ca.key",
            "-CAcreateserial",
            "-out",
            "tsa.crt",
            "-days",
            "2",
            "-extfile",
            "ext.cnf",
            cwd=d,
        )
        (d / "serial").write_text("01\n")
        (d / "tsa.cnf").write_text(TSA_CONFIG.format(dir=d))
        authority = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                query = authority.dir / "q.tsq"
                query.write_bytes(self.rfile.read(int(self.headers["Content-Length"])))
                sh(
                    "openssl",
                    "ts",
                    "-reply",
                    "-config",
                    "tsa.cnf",
                    "-queryfile",
                    "q.tsq",
                    "-out",
                    "r.tsr",
                    cwd=authority.dir,
                )
                body = (authority.dir / "r.tsr").read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", "application/timestamp-reply")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *args):
                pass

        self.server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.authority = Authority(
            "local", f"http://127.0.0.1:{self.server.server_port}/tsr", d / "ca.crt", d / "tsa.crt"
        )

    def close(self):
        self.server.shutdown()
        self.tmp.cleanup()


class RFC3161Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.local = LocalAuthority()

    @classmethod
    def tearDownClass(cls):
        cls.local.close()

    def test_stamp_and_verify_round_trip(self):
        ts = RFC3161Timestamper([self.local.authority])
        stamps = ts.stamp(b'{"kind":"CASE","record_id":"KOD-P-X","sha256":"ab"}')
        self.assertEqual([s.authority for s in stamps], ["local"])
        now = datetime.now(timezone.utc)
        self.assertLess(abs(stamps[0].time - now), timedelta(minutes=2))
        again = ts.verify(
            "local", stamps[0].token, b'{"kind":"CASE","record_id":"KOD-P-X","sha256":"ab"}'
        )
        self.assertEqual(again, stamps[0].time)

    def test_token_does_not_verify_for_other_data(self):
        ts = RFC3161Timestamper([self.local.authority])
        stamp = ts.stamp(b"original line")[0]
        with self.assertRaises(TimestampError):
            ts.verify("local", stamp.token, b"rewritten line")

    def test_token_does_not_verify_against_another_ca(self):
        ts = RFC3161Timestamper([self.local.authority])
        stamp = ts.stamp(b"line")[0]
        other = LocalAuthority()
        try:
            impostor = RFC3161Timestamper(
                [Authority("local", "", other.authority.cafile, other.authority.untrusted)]
            )
            with self.assertRaises(TimestampError):
                impostor.verify("local", stamp.token, b"line")
        finally:
            other.close()

    def test_unreachable_authority_is_reported_not_fatal(self):
        dead = Authority("dead", "http://127.0.0.1:9/tsr", self.local.authority.cafile)
        ts = RFC3161Timestamper([dead, self.local.authority], timeout=2)
        stamps = ts.stamp(b"line")
        self.assertEqual([s.authority for s in stamps], ["local"])
        self.assertTrue(ts.last_errors and ts.last_errors[0].startswith("dead:"))

    def test_pinned_production_certificates_are_present(self):
        from kod.timestamp import AUTHORITIES

        for a in AUTHORITIES:
            self.assertTrue(a.cafile.exists(), a.cafile)
            self.assertTrue(a.url.startswith("https://"))


if __name__ == "__main__":
    unittest.main()
