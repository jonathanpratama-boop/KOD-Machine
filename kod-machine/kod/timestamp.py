"""External timestamps (RFC 3161): proof that a hash existed at a time someone else attests.

A git commit date comes from the committer's clock and can be set to anything, and a
later push does not say when the commit was made. So each anchor line is also sent, as a
SHA-256 digest only, to independent timestamp authorities. Each returns a signed token
carrying its own clock reading. Tokens are committed next to the line and verified
offline against the pinned certificates in tsa/, never against the local CA store.
"""

from __future__ import annotations

import re
import subprocess
import tempfile
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

TSA_DIR = Path(__file__).resolve().parents[1] / "tsa"


class TimestampError(RuntimeError):
    pass


@dataclass(frozen=True)
class Authority:
    name: str
    url: str
    cafile: Path
    untrusted: Path | None = None


AUTHORITIES = (
    Authority(
        "freetsa",
        "https://freetsa.org/tsr",
        TSA_DIR / "freetsa-cacert.pem",
        TSA_DIR / "freetsa-tsa.crt",
    ),
    Authority(
        "sectigo", "https://timestamp.sectigo.com", TSA_DIR / "sectigo-usertrust-rsa-root.pem"
    ),
)


@dataclass(frozen=True)
class Stamp:
    authority: str
    token: bytes
    time: datetime


def _openssl(*args: str) -> str:
    proc = subprocess.run(["openssl", *args], capture_output=True, text=True)
    if proc.returncode != 0:
        raise TimestampError(
            f"openssl {args[0]} {args[1]}: {(proc.stderr or proc.stdout).strip().splitlines()[-1:]}"
        )
    return proc.stdout


def _parse_gen_time(text: str) -> datetime:
    match = re.search(
        r"Time stamp: (\w{3})\s+(\d{1,2}) (\d{2}:\d{2}:\d{2})(?:\.\d+)? (\d{4}) GMT", text
    )
    if not match:
        raise TimestampError("token has no readable time")
    month, day, clock, year = match.groups()
    return datetime.strptime(f"{month} {day} {clock} {year}", "%b %d %H:%M:%S %Y").replace(
        tzinfo=timezone.utc
    )


class RFC3161Timestamper:
    def __init__(self, authorities=AUTHORITIES, timeout: float = 20.0):
        self.authorities = {a.name: a for a in authorities}
        self.timeout = timeout
        self.last_errors: list[str] = []

    def stamp(self, data: bytes) -> list[Stamp]:
        """Ask every authority. Returns the tokens that came back and verified."""
        stamps, errors = [], []
        with tempfile.TemporaryDirectory() as tmp:
            query = Path(tmp) / "q.tsq"
            (Path(tmp) / "data").write_bytes(data)
            _openssl(
                "ts",
                "-query",
                "-data",
                str(Path(tmp) / "data"),
                "-sha256",
                "-cert",
                "-out",
                str(query),
            )
            body = query.read_bytes()
            for authority in self.authorities.values():
                try:
                    req = urllib.request.Request(
                        authority.url,
                        data=body,
                        headers={"Content-Type": "application/timestamp-query"},
                    )
                    with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                        token = resp.read()
                    stamps.append(
                        Stamp(authority.name, token, self.verify(authority.name, token, data))
                    )
                except Exception as exc:  # one authority down must not hide the others
                    errors.append(f"{authority.name}: {exc}")
        self.last_errors = errors
        return stamps

    def verify(self, authority_name: str, token: bytes, data: bytes) -> datetime:
        """Check the token signs this data under the pinned chain; return its time."""
        authority = self.authorities.get(authority_name)
        if authority is None:
            raise TimestampError(f"unknown timestamp authority {authority_name!r}")
        with tempfile.TemporaryDirectory() as tmp:
            tok, dat = Path(tmp) / "r.tsr", Path(tmp) / "data"
            tok.write_bytes(token)
            dat.write_bytes(data)
            args = [
                "ts",
                "-verify",
                "-in",
                str(tok),
                "-data",
                str(dat),
                "-CAfile",
                str(authority.cafile),
            ]
            if authority.untrusted:
                args += ["-untrusted", str(authority.untrusted)]
            if "Verification: OK" not in _openssl(*args):
                raise TimestampError(f"{authority_name} token does not verify")
            return _parse_gen_time(_openssl("ts", "-reply", "-in", str(tok), "-text"))
