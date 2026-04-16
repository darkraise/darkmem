"""One-off emitter for shared-base batch-152 — technical domain (applied cryptography: AEAD, signatures, KDFs, TLS 1.3, PQC, HSMs, Sigstore).

Writes 50 rows to data/v2/shared/batch_152.tmp.jsonl with ids shared-07551..07600.
"""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "shared" / "batch_152.tmp.jsonl"
ID_OFFSET = 7550

# (text, memory_type, domain, noise, entities, relationships, qq, qk)
ENTRIES: list[tuple] = [
    # --- 1 ---
    ("Switched the session transport from AES-CBC with HMAC-SHA256 to AES-GCM with 96-bit nonces; the encrypt-then-MAC glue code is gone and the AEAD primitive handles integrity in one pass.", "milestone", "technical", False,
     [("AES-CBC", "algorithm"), ("HMAC-SHA256", "algorithm"), ("AES-GCM", "algorithm"), ("AEAD", "concept")],
     [("AES-GCM", "AES-CBC", "REPLACES"), ("AES-GCM", "AEAD", "IS_A")],
     "which AEAD construction replaced the encrypt-then-MAC pipeline on the session transport",
     "aes gcm cbc hmac sha256 aead nonce session transport replace"),
    # --- 2 ---
    ("Mobile builds prefer ChaCha20-Poly1305 over AES-GCM because ARM cores without dedicated AES instructions ran the GCM path about three times slower and blew the battery budget on long uploads.", "preference", "technical", False,
     [("ChaCha20-Poly1305", "algorithm"), ("AES-GCM", "algorithm"), ("ARM", "platform")],
     [("ChaCha20-Poly1305", "AES-GCM", "PREFERS")],
     "why do mobile builds pick ChaCha20-Poly1305 over AES-GCM on ARM cores without AES instructions",
     "chacha20 poly1305 aes gcm arm mobile aes ni battery performance"),
    # --- 3 ---
    ("Migrated long-term signing keys from RSA-2048 to Ed25519; the public keys are 32 bytes instead of 256 and signature verification runs an order of magnitude faster on the gateway box.", "milestone", "technical", False,
     [("RSA-2048", "algorithm"), ("Ed25519", "algorithm")],
     [("Ed25519", "RSA-2048", "REPLACES")],
     "which signing algorithm replaced RSA-2048 for long-term keys and what size and speed win did it bring",
     "ed25519 rsa 2048 signature key size verify speed gateway migrate"),
    # --- 4 ---
    ("ECDSA on secp256r1 stayed in place for the legacy JWT path where downstream verifiers only know P-256; Ed25519 rolled out on every new service that speaks native Ed25519 JWS.", "decision", "technical", False,
     [("ECDSA", "algorithm"), ("secp256r1", "algorithm"), ("Ed25519", "algorithm"), ("JWT", "protocol")],
     [("ECDSA", "JWT", "APPLIES_TO")],
     "why did we keep ECDSA on secp256r1 for legacy JWT while rolling Ed25519 on new services",
     "ecdsa secp256r1 p 256 ed25519 jwt jws legacy verifier compat"),
    # --- 5 ---
    ("Key exchange is X25519 everywhere internal; the earlier custom DH group has been retired, so the handshake layer now trusts a single curve and rejects fallback suites at config time.", "fact", "technical", False,
     [("X25519", "algorithm"), ("DH group", "algorithm")],
     [("X25519", "DH group", "REPLACES")],
     "which key exchange replaced the custom DH group on internal services and what does the handshake layer reject now",
     "x25519 diffie hellman dh group key exchange internal handshake curve"),
    # --- 6 ---
    ("The consensus client aggregates validator signatures with BLS on the BLS12-381 curve; bundling ten thousand attestations into one verify call is what made the per-slot budget work at all.", "fact", "technical", False,
     [("BLS", "algorithm"), ("BLS12-381", "algorithm"), ("consensus client", "service")],
     [("consensus client", "BLS", "USES")],
     "how does the consensus client fit ten thousand validator signatures into a per-slot verify budget",
     "bls bls12 381 aggregate signature validator attestation consensus slot"),
    # --- 7 ---
    ("Password storage is Argon2id with m=64 MiB, t=3, p=4; the old bcrypt column with cost 12 is being re-hashed on next login and a migration flag tracks which rows still hold bcrypt digests.", "decision", "technical", False,
     [("Argon2id", "algorithm"), ("bcrypt", "algorithm"), ("migration flag", "pattern")],
     [("Argon2id", "bcrypt", "REPLACES")],
     "which password hash replaced bcrypt for user storage and which parameters were picked",
     "argon2id bcrypt password hash cost memory migration login rehash"),
    # --- 8 ---
    ("scrypt got rejected for password hashing because tuning its parameters on shared hosts was fragile and the memory-hardness tail gave us less defense than Argon2id with the same wall-clock budget.", "decision", "technical", False,
     [("scrypt", "algorithm"), ("Argon2id", "algorithm")],
     [("Argon2id", "scrypt", "PREFERS")],
     "why was scrypt rejected for password hashing in favour of Argon2id on shared hosts",
     "scrypt argon2id password hash memory hard tuning shared host reject"),
    # --- 9 ---
    ("PBKDF2-HMAC-SHA256 stays only in the FIPS-constrained tenant where Argon2id isn't on the approved list; iteration count was lifted to 600000 after the OWASP guidance refresh.", "fact", "technical", False,
     [("PBKDF2-HMAC-SHA256", "algorithm"), ("Argon2id", "algorithm"), ("OWASP", "organization"), ("FIPS", "organization")],
     [("PBKDF2-HMAC-SHA256", "FIPS", "APPLIES_TO")],
     "why does PBKDF2-HMAC-SHA256 stay in the FIPS tenant and what iteration count does it use now",
     "pbkdf2 hmac sha256 fips argon2id owasp iteration count tenant approved"),
    # --- 10. noise ---
    ("The kitchen's espresso grinder is back on the fritz and the Tuesday latte queue has grown out the second set of doors.", "fact", "noise", True, [], [], None, None),
    # --- 11 ---
    ("Session keys derive from the shared secret via HKDF-SHA256 with a per-connection salt; a single extract yields two expand calls, one for the client and one for the server direction.", "reference", "technical", False,
     [("HKDF-SHA256", "algorithm"), ("shared secret", "concept"), ("salt", "concept")],
     [],
     "how does the session derive directional keys from the shared secret with HKDF-SHA256",
     "hkdf sha256 session key derive extract expand salt client server"),
    # --- 12 ---
    ("HMAC-SHA256 signs the webhook payload header; the signature scheme was chosen deliberately over a custom keyed prefix because length-extension attacks on the Merkle-Damgard construction keep biting people.", "decision", "technical", False,
     [("HMAC-SHA256", "algorithm"), ("Merkle-Damgard", "concept"), ("length-extension", "concept")],
     [("HMAC-SHA256", "length-extension", "FIXES")],
     "why did the webhook signer pick HMAC-SHA256 over a homegrown keyed prefix construction",
     "hmac sha256 webhook signature keyed prefix length extension merkle"),
    # --- 13 ---
    ("Internal content addressing moved from SHA-256 to BLAKE3 for large-file hashing; the streaming hasher saturates the NVMe read throughput instead of stalling at a single SHA core.", "decision", "technical", False,
     [("SHA-256", "algorithm"), ("BLAKE3", "algorithm"), ("NVMe", "technology")],
     [("BLAKE3", "SHA-256", "REPLACES")],
     "which hash replaced SHA-256 for large-file content addressing and what throughput story drove the switch",
     "blake3 sha 256 content address nvme throughput hash stream file"),
    # --- 14 ---
    ("SHA-3 (Keccak-256) remains the on-chain hash because changing it would fork the ledger; off-chain tooling continues to use BLAKE3 freely and only crosses to SHA-3 at the boundary.", "reference", "technical", False,
     [("SHA-3", "algorithm"), ("Keccak-256", "algorithm"), ("BLAKE3", "algorithm")],
     [],
     "why does the chain keep SHA-3 Keccak-256 while off-chain tooling sticks with BLAKE3",
     "sha 3 keccak 256 blake3 on chain off chain hash fork ledger boundary"),
    # --- 15 ---
    ("TLS 1.3 is the only allowed TLS version on the edge; the handshake collapsed from two round trips to one, and cipher-suite negotiation now ships a fixed list of three AEAD suites.", "milestone", "technical", False,
     [("TLS 1.3", "protocol"), ("AEAD", "concept"), ("edge", "service")],
     [("edge", "TLS 1.3", "USES")],
     "which TLS version is the only one allowed on the edge and what handshake simplification did it enable",
     "tls 1 3 edge handshake round trip cipher suite aead allowed version"),
    # --- 16 ---
    ("0-RTT is disabled on authenticated endpoints; early data replay on idempotent POSTs was a footgun and the bandwidth win didn't justify the surface area for anything past the login screen.", "preference", "technical", False,
     [("0-RTT", "protocol"), ("early data", "concept"), ("replay", "concept")],
     [],
     "why is 0-RTT disabled on authenticated endpoints and which attack shape drove the decision",
     "0 rtt early data replay authenticated post login footgun disable"),
    # --- 17 ---
    ("Post-quantum KEM rolled out as a hybrid X25519+Kyber768 suite on the handshake; classical still runs in parallel so a failure in the Kyber path falls back without user-visible breakage.", "architecture", "technical", False,
     [("Kyber768", "algorithm"), ("X25519", "algorithm"), ("handshake", "concept")],
     [("Kyber768", "X25519", "RELATED_TO")],
     "how does the hybrid post-quantum KEM combine X25519 and Kyber768 on the handshake",
     "kyber768 x25519 hybrid post quantum kem handshake fallback classical"),
    # --- 18 ---
    ("Dilithium signatures sit behind a feature flag for document signing; the 2.4 KB signature size tanked the mobile payload budget, so we keep Ed25519 as the default until clients gate on bandwidth.", "problem", "technical", False,
     [("Dilithium", "algorithm"), ("Ed25519", "algorithm"), ("feature flag", "pattern")],
     [("Dilithium", "Ed25519", "RELATED_TO")],
     "why does Dilithium sit behind a feature flag while Ed25519 stays the default for document signing",
     "dilithium ed25519 signature size mobile payload feature flag document"),
    # --- 19 ---
    ("SPHINCS+ signs the firmware release bundle; the stateless hash-based scheme means the offline signing HSM never has to track a state counter and a key compromise doesn't invalidate past releases.", "fact", "technical", False,
     [("SPHINCS+", "algorithm"), ("HSM", "infrastructure"), ("firmware release", "concept")],
     [("SPHINCS+", "firmware release", "APPLIES_TO")],
     "why does the firmware release pipeline sign with SPHINCS+ and what state property matters to the HSM",
     "sphincs plus firmware release signature hash based stateless hsm offline"),
    # --- 20 ---
    ("libsodium is the only crypto dependency in the mobile SDK; the surface is tiny, defaults are safe, and we don't ship raw OpenSSL primitives from the app bundle anymore.", "decision", "technical", False,
     [("libsodium", "library"), ("OpenSSL", "library"), ("mobile SDK", "project")],
     [("libsodium", "OpenSSL", "REPLACES")],
     "which crypto library replaced OpenSSL in the mobile SDK and what surface-area argument drove it",
     "libsodium openssl mobile sdk dependency surface default safe primitive"),
    # --- 21 ---
    ("The legacy daemon still links against NaCl's crypto_box directly; libsodium is API-compatible there, so the port is a one-line swap once we're willing to bump the minimum glibc on the box.", "fact", "technical", False,
     [("NaCl", "library"), ("libsodium", "library"), ("crypto_box", "api"), ("glibc", "library")],
     [("libsodium", "NaCl", "REPLACES")],
     "what is the remaining blocker that keeps the legacy daemon on NaCl instead of libsodium",
     "nacl libsodium crypto_box glibc daemon legacy port api compatible"),
    # --- 22 ---
    ("Server-side TLS uses BoringSSL for the edge binary because Google's curated patch set lands CVE fixes ahead of upstream OpenSSL; the API shim abstracts the tiny divergences at build time.", "decision", "technical", False,
     [("BoringSSL", "library"), ("OpenSSL", "library"), ("edge binary", "service")],
     [("BoringSSL", "OpenSSL", "PREFERS")],
     "why does the edge binary link BoringSSL instead of upstream OpenSSL for server-side TLS",
     "boringssl openssl edge binary cve patch google api shim tls server"),
    # --- 23 ---
    ("rustls replaces native-tls in the control-plane agents; a memory-safe TLS stack with no OpenSSL build-time dependency cut deployment footprint and retired a class of FFI crashes.", "decision", "technical", False,
     [("rustls", "library"), ("native-tls", "library"), ("control-plane", "service")],
     [("rustls", "native-tls", "REPLACES")],
     "which TLS stack replaced native-tls in the control-plane agents and what class of crash did it retire",
     "rustls native tls control plane agent memory safe ffi crash deploy"),
    # --- 24 ---
    ("age encrypts the operator backup bundles; recipients are curve25519 public keys dropped in a YAML file, and the decrypt UX is one command without a PGP web-of-trust rabbit hole.", "preference", "technical", False,
     [("age", "tool"), ("curve25519", "algorithm"), ("PGP", "protocol")],
     [("age", "PGP", "REPLACES")],
     "which tool encrypts operator backups and how does its recipient model differ from the PGP workflow",
     "age curve25519 recipient backup operator yaml pgp web of trust"),
    # --- 25 ---
    ("Release artefacts are signed with minisign; verification is a short Ed25519 check against a committed public key, no keyring import and no expiry dance between the build box and the mirror.", "fact", "technical", False,
     [("minisign", "tool"), ("Ed25519", "algorithm"), ("public key", "concept")],
     [("minisign", "Ed25519", "USES")],
     "which tool signs release artefacts and what verification flow does it replace the PGP keyring dance with",
     "minisign ed25519 release artefact public key verify keyring expiry"),
    # --- 26 ---
    ("Container images go through Sigstore cosign with keyless signing; the OIDC identity in the Rekor transparency log is how we audit who actually cut the image in CI.", "reference", "technical", False,
     [("Sigstore", "tool"), ("cosign", "tool"), ("Rekor", "service"), ("OIDC", "protocol")],
     [("cosign", "Rekor", "COMMUNICATES_WITH")],
     "how does the container pipeline prove who signed an image with Sigstore keyless and Rekor",
     "sigstore cosign rekor oidc keyless signing container image transparency"),
    # --- 27 ---
    ("Every git push is signed via gitsign so commit authorship chains back to the same OIDC identity Sigstore uses; a rejected hook blocks unsigned pushes on the main branch.", "architecture", "technical", False,
     [("gitsign", "tool"), ("Sigstore", "tool"), ("OIDC", "protocol"), ("main branch", "concept")],
     [("gitsign", "Sigstore", "BUILDS_ON")],
     "how does gitsign tie git commit authorship to the Sigstore OIDC identity on the main branch",
     "gitsign sigstore oidc commit push main branch hook reject authorship"),
    # --- 28 ---
    ("Hardware signing keys sit behind a PKCS#11 token interface in the CI runner; the signing service never sees the raw key material and a pin-entry daemon mediates each call.", "architecture", "technical", False,
     [("PKCS#11", "protocol"), ("CI runner", "service"), ("pin-entry daemon", "service")],
     [("CI runner", "PKCS#11", "USES")],
     "how does the CI runner talk to hardware signing keys without ever touching raw key material",
     "pkcs 11 token ci runner signing service pin entry daemon mediate"),
    # --- 29 ---
    ("The offline root key lives on an HSM in a Nitrokey HSM 2 form factor; quorum-of-three operator cards unlock a signing session and every ceremony writes a signed audit record.", "architecture", "technical", False,
     [("HSM", "infrastructure"), ("Nitrokey HSM 2", "infrastructure"), ("quorum-of-three", "pattern")],
     [("Nitrokey HSM 2", "HSM", "IS_A")],
     "how does the offline root key enforce operator quorum and ceremony audit in an HSM",
     "hsm nitrokey offline root key quorum operator card ceremony audit"),
    # --- 30 ---
    ("Mobile device attestation leans on the secure enclave for private-key custody; the enclave-generated key signs a challenge and the server verifies against Apple's attestation root.", "reference", "technical", False,
     [("secure enclave", "infrastructure"), ("attestation", "concept"), ("Apple", "organization")],
     [("secure enclave", "attestation", "PRODUCES")],
     "how does mobile device attestation use the secure enclave to custody the private key end-to-end",
     "secure enclave attestation apple mobile device private key challenge"),
    # --- 31 ---
    ("Boot-time disk encryption keys unseal through the TPM's PCR policy; a firmware update that changes PCR7 blocks the unseal and forces a recovery passphrase, which caught one tampered laptop.", "problem", "technical", False,
     [("TPM", "infrastructure"), ("PCR", "concept"), ("disk encryption", "concept")],
     [("TPM", "disk encryption", "PRODUCES")],
     "how does TPM PCR policy unseal the disk encryption key and what tampering case did it catch",
     "tpm pcr disk encryption unseal firmware update recovery passphrase boot"),
    # --- 32 ---
    ("Rolled AES-GCM-SIV into the at-rest encryption path for the object store; nonce misuse from a replicated write no longer catastrophically leaks the plaintext the way plain AES-GCM would.", "decision", "technical", False,
     [("AES-GCM-SIV", "algorithm"), ("AES-GCM", "algorithm"), ("object store", "service")],
     [("AES-GCM-SIV", "AES-GCM", "IMPROVES_ON")],
     "which AEAD replaced AES-GCM at rest and what nonce-misuse property drove the change",
     "aes gcm siv nonce misuse object store at rest replicated write leak"),
    # --- 33 ---
    ("XChaCha20-Poly1305 handles file-level encryption in the backup daemon; the 192-bit nonce lets us pick randomly per chunk without tracking a counter across machines.", "reference", "technical", False,
     [("XChaCha20-Poly1305", "algorithm"), ("backup daemon", "service"), ("nonce", "concept")],
     [("backup daemon", "XChaCha20-Poly1305", "USES")],
     "why does the backup daemon use XChaCha20-Poly1305 for file-level encryption across machines",
     "xchacha20 poly1305 nonce backup daemon file chunk random 192 bit"),
    # --- 34 ---
    ("Certificate issuance went from ACME with RSA-2048 CSRs to ECDSA P-256 CSRs; Let's Encrypt renewal runs faster and the cert chain bytes dropped noticeably on every TLS connection.", "milestone", "technical", False,
     [("ACME", "protocol"), ("Let's Encrypt", "service"), ("RSA-2048", "algorithm"), ("ECDSA", "algorithm")],
     [("ECDSA", "RSA-2048", "REPLACES")],
     "which CSR algorithm replaced RSA-2048 on ACME certificate issuance and what payload savings followed",
     "acme lets encrypt ecdsa p 256 rsa 2048 csr cert chain renewal"),
    # --- 35 ---
    ("Noise Protocol Framework handshake (Noise_IK) drives the peer-to-peer mesh; static-key mutual auth happens on the first message and we avoid a full PKI in the data path.", "architecture", "technical", False,
     [("Noise Protocol", "protocol"), ("Noise_IK", "protocol"), ("peer-to-peer mesh", "service"), ("PKI", "concept")],
     [("Noise_IK", "PKI", "REPLACES")],
     "which handshake pattern runs the peer-to-peer mesh mutual auth without a full PKI",
     "noise protocol ik handshake peer mesh static key mutual auth pki"),
    # --- 36 ---
    ("WireGuard uses Curve25519 for key exchange and ChaCha20-Poly1305 for data; the kernel-module deployment beat the OpenVPN box on latency and cut the config surface to a single ini file.", "preference", "technical", False,
     [("WireGuard", "protocol"), ("Curve25519", "algorithm"), ("ChaCha20-Poly1305", "algorithm"), ("OpenVPN", "service")],
     [("WireGuard", "OpenVPN", "REPLACES")],
     "which VPN protocol replaced OpenVPN and which primitives back its key exchange and data path",
     "wireguard curve25519 chacha20 poly1305 openvpn vpn kernel config ini"),
    # --- 37 ---
    ("Signed URLs to the media bucket use HMAC-SHA256 with a rotating key pair kept in AWS KMS; rotation runs weekly and both keys verify during the overlap window to avoid broken embeds.", "architecture", "technical", False,
     [("HMAC-SHA256", "algorithm"), ("AWS KMS", "service"), ("media bucket", "service"), ("Signed URLs", "concept")],
     [("media bucket", "HMAC-SHA256", "USES"), ("Signed URLs", "HMAC-SHA256", "USES")],
     "how does the signed URL scheme rotate HMAC keys in AWS KMS without breaking live embeds",
     "hmac sha256 aws kms signed url media bucket rotation overlap window"),
    # --- 38 ---
    ("Post-quantum readiness lines up a fallback to FALCON for signatures should Dilithium need to be pulled; the audit trail can re-sign artefacts in place because the hash commitments stay stable.", "fact", "technical", False,
     [("FALCON", "algorithm"), ("Dilithium", "algorithm"), ("audit trail", "pattern")],
     [("FALCON", "Dilithium", "RELATED_TO")],
     "which post-quantum signature is lined up as a fallback if Dilithium has to be pulled",
     "falcon dilithium post quantum signature fallback audit trail resign"),
    # --- 39 ---
    ("Old MD5 checksum field on the upload API gets ignored server-side but we still echo it back for legacy CLI clients; SHA-256 is the authoritative integrity check now.", "decision", "technical", False,
     [("MD5", "algorithm"), ("SHA-256", "algorithm"), ("upload API", "api")],
     [("SHA-256", "MD5", "REPLACES")],
     "how does the upload API keep legacy MD5 compatibility while running SHA-256 as the real integrity check",
     "md5 sha 256 upload api checksum legacy cli echo authoritative integrity"),
    # --- 40 ---
    ("Master KDF for the envelope-encryption scheme is HKDF-SHA512 keyed off a KMS data key; child keys derive per-tenant and per-table so a blast radius stays bounded to one table on leak.", "reference", "technical", False,
     [("HKDF-SHA512", "algorithm"), ("envelope-encryption", "concept"), ("KMS data key", "concept")],
     [],
     "how does the envelope-encryption scheme bound a key-leak blast radius to a single table",
     "hkdf sha512 envelope encryption kms data key tenant table blast"),
    # --- 41 ---
    ("Dropped CBC-mode support from the public API; a Lucky13 padding-oracle POC from the red team against the old gateway closed the door on anyone arguing for backwards compatibility.", "milestone", "technical", False,
     [("CBC-mode", "algorithm"), ("Lucky13", "concept"), ("padding-oracle", "concept")],
     [],
     "which mode did the public API drop after a Lucky13 padding-oracle POC from the red team",
     "cbc mode lucky13 padding oracle red team public api drop compat"),
    # --- 42 ---
    ("Short-lived access tokens are signed EdDSA JWTs with a five-minute TTL; rotation is driven off an internal JWKS endpoint that refreshes every hour from the signer's HSM-backed key set.", "architecture", "technical", False,
     [("EdDSA", "algorithm"), ("JWT", "protocol"), ("JWKS", "protocol"), ("HSM", "infrastructure")],
     [("JWKS", "HSM", "COMMUNICATES_WITH")],
     "how does the short-lived access-token pipeline rotate EdDSA JWT signing keys via JWKS and an HSM",
     "eddsa jwt jwks hsm access token rotation ttl sign internal endpoint"),
    # --- 43. noise ---
    ("The upstairs plant is definitely unhappy with the new HVAC setpoint and the leaves are starting to curl at the tips.", "fact", "noise", True, [], [], None, None),
    # --- 44 ---
    ("Double-ratchet messaging layer runs X25519 for DH and HKDF-SHA256 for the chain keys; each message rotates the send key so a compromised snapshot doesn't decrypt the next outbound.", "architecture", "technical", False,
     [("Double-ratchet", "protocol"), ("X25519", "algorithm"), ("HKDF-SHA256", "algorithm")],
     [("Double-ratchet", "X25519", "USES"), ("Double-ratchet", "HKDF-SHA256", "USES")],
     "which messaging handshake rotates per-message send keys so a stolen snapshot cannot decrypt the next outbound packet",
     "double ratchet x25519 hkdf sha256 messaging chain key rotate forward"),
    # --- 45 ---
    ("Cryptographic random stream on Linux pulls from getrandom(2) with GRND_RANDOM off; the older /dev/urandom open-on-boot race tripped a seed-failure alarm once in the stress tests.", "decision", "technical", False,
     [("getrandom(2)", "api"), ("/dev/urandom", "file"), ("Linux", "platform")],
     [("getrandom(2)", "/dev/urandom", "REPLACES")],
     "which Linux RNG API replaced /dev/urandom and which boot-time race tripped the alarm",
     "getrandom urandom linux rng boot race seed failure stress test"),
    # --- 46 ---
    ("Constant-time comparisons everywhere in the auth path use subtle.ConstantTimeCompare; a timing-leak Bandit finding on a stray bytes.Equal in the OTP path was the incident that drove the sweep.", "problem", "technical", False,
     [("subtle.ConstantTimeCompare", "api"), ("bytes.Equal", "api"), ("Bandit", "tool"), ("OTP", "protocol")],
     [("subtle.ConstantTimeCompare", "bytes.Equal", "REPLACES")],
     "why did the auth path sweep to subtle.ConstantTimeCompare and which incident triggered it",
     "constant time compare bytes equal bandit otp timing leak auth sweep"),
    # --- 47 ---
    ("Key wrapping in the vault uses AES-KW (RFC 3394) rather than plain AES-GCM because the wrap operation needs to be deterministic for idempotent re-wrap during key rotation.", "decision", "technical", False,
     [("AES-KW", "algorithm"), ("RFC 3394", "publication"), ("AES-GCM", "algorithm"), ("vault", "service")],
     [("AES-KW", "AES-GCM", "PREFERS")],
     "why does the vault wrap keys with AES-KW under RFC 3394 instead of AES-GCM",
     "aes kw rfc 3394 vault key wrap deterministic rotation idempotent gcm"),
    # --- 48 ---
    ("Cryptographic agility lives in a registered suite table; each record pins an AEAD, a KDF, a signature, and a hash so migrating one primitive doesn't rewrite the whole protocol code.", "architecture", "technical", False,
     [("suite table", "pattern"), ("AEAD", "concept"), ("KDF", "concept")],
     [],
     "how does the suite-table pattern let one primitive migrate without rewriting the whole protocol code",
     "suite table aead kdf signature hash crypto agility primitive migrate"),
    # --- 49 ---
    ("Deprecated SHA-1 in every signing path after the Shambles collision POC; a one-off scanner sweeps the artifact store monthly and quarantines anything still chained through a SHA-1 digest.", "milestone", "technical", False,
     [("SHA-1", "algorithm"), ("Shambles", "event"), ("artifact store", "service")],
     [],
     "what triggered the full SHA-1 deprecation in signing paths and how does the artifact sweep enforce it",
     "sha 1 shambles collision signing deprecate artifact store scan quarantine"),
    # --- 50 ---
    ("Verified the OpenSSL 3.2 provider wiring boots with the FIPS module, then set it as the default provider on the regulated tenant; legacy provider stayed enabled only for one digest alias.", "milestone", "technical", False,
     [("OpenSSL 3.2", "library"), ("FIPS module", "library"), ("legacy provider", "config")],
     [("OpenSSL 3.2", "FIPS module", "USES")],
     "which OpenSSL 3.2 provider is now the default on the regulated tenant and why does the legacy provider stay",
     "openssl 3 2 fips module provider regulated tenant legacy digest alias"),
]


def _find_span(text: str, needle: str, used: list[tuple[int, int]]) -> tuple[int, int]:
    start = 0
    while True:
        idx = text.find(needle, start)
        if idx < 0:
            raise ValueError(f"entity name {needle!r} not found in text {text!r}")
        end = idx + len(needle)
        overlap = any(not (end <= s or idx >= e) for s, e in used)
        if not overlap:
            return idx, end
        start = idx + 1


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, entry in enumerate(ENTRIES, start=1):
            text, mt, domain, noise, ents, rels, qq, qk = entry
            used: list[tuple[int, int]] = []
            entities = []
            for name, typ in ents:
                s, e = _find_span(text, name, used)
                used.append((s, e))
                entities.append({"name": name, "type": typ, "start": s, "end": e})
            row: dict = {
                "id": f"shared-{ID_OFFSET + i:05d}",
                "domain": domain,
                "text": text,
                "memory_type": mt,
                "noise": noise,
                "entities": entities,
                "relationships": [{"source": s, "target": t, "type": r} for s, t, r in rels],
            }
            if qq is not None and qk is not None:
                row["queries"] = [
                    {"form": "question", "text": qq},
                    {"form": "keyword", "text": qk},
                ]
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
            written += 1
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
