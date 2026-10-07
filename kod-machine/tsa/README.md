# Pinned timestamp-authority certificates

RFC 3161 tokens on every KOD anchor are verified against these files, not against
whatever CA bundle the verifying machine happens to have.

| File | Authority | Retrieved | SHA-256 |
|---|---|---|---|
| freetsa-cacert.pem | freetsa.org root CA (https://freetsa.org/files/cacert.pem) | 2026-10-07 | 2151b61137ffa86bf664691ba67e7da0b19f98c758e3d228d5d8ebf27e044438 |
| freetsa-tsa.crt | freetsa.org TSA signing cert (https://freetsa.org/files/tsa.crt) | 2026-10-07 | 8bfb0305bb64e2571ca507552ef3245cb1c2fee8728e0ff8689225081ea13467 |
| sectigo-usertrust-rsa-root.pem | USERTrust RSA Certification Authority, root of Sectigo's public time-stamping chain (intermediates arrive inside each token) | 2026-10-07, Mozilla CA store | 8a3dbcb92ab1c6277647fe2ab8536b5c982abbfdb1f1df5728e01b906aba953a (file); cert fingerprint e793c9b0…c3d4cbd2 |

Replacing a file here changes what verifies. Add new files; do not edit these.
