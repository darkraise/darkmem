"""One-off emitter for classification top-up batch-002 — contrastive_reference_fact mode, tech documentation slice.

Writes 100 rows (50 pairs) to data/v2/classification/batch_002.tmp.jsonl with ids class-00101..00200.
"""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "v2" / "classification" / "batch_002.tmp.jsonl"
ID_OFFSET = 100
PAIR_OFFSET = 50

# (ref_text, ref_domain, fact_text, fact_domain)
PAIRS: list[tuple[str, str, str, str]] = [
    # 1. RFC 9110 - HTTP semantics
    (
        "RFC 9110 section 9.3.1 defines GET as a method whose semantics are safe and idempotent, meaning the request is not intended to cause state change on the origin server.",
        "technical",
        "HTTP GET requests are supposed to be safe and idempotent; they shouldn't mutate server state.",
        "technical",
    ),
    # 2. RFC 7519 - JWT
    (
        "RFC 7519 specifies that a JWT is a compact, URL-safe token consisting of three base64url-encoded segments separated by dots: header, payload, and signature.",
        "technical",
        "A JSON Web Token is made up of three base64url parts joined by dots: a header, a payload, and a signature.",
        "technical",
    ),
    # 3. RFC 6749 - OAuth 2.0
    (
        "Per RFC 6749, the authorization code grant flow requires the client to exchange an authorization code for an access token at the token endpoint using client credentials.",
        "technical",
        "In the OAuth 2.0 authorization code flow, the client swaps the code for an access token at the token endpoint using its credentials.",
        "technical",
    ),
    # 4. RFC 5321 - SMTP
    (
        "RFC 5321 states that an SMTP server MUST accept messages with line lengths of up to 998 octets plus the trailing CRLF.",
        "technical",
        "SMTP servers must handle message lines up to 998 bytes long, not counting the terminating CRLF.",
        "technical",
    ),
    # 5. RFC 8259 - JSON
    (
        "RFC 8259 mandates that JSON text exchanged between systems that are not part of a closed ecosystem MUST be encoded using UTF-8.",
        "technical",
        "Interoperable JSON on the wire has to be UTF-8 encoded.",
        "technical",
    ),
    # 6. PostgreSQL docs - WAL
    (
        "Per the PostgreSQL 16 documentation on Write-Ahead Logging, WAL records are flushed to disk before the corresponding data pages, ensuring crash recovery can replay committed changes.",
        "technical",
        "Postgres flushes WAL records to disk ahead of the actual data pages so crash recovery can redo committed transactions.",
        "technical",
    ),
    # 7. PostgreSQL docs - MVCC
    (
        "The PostgreSQL documentation on concurrency control explains that MVCC gives each transaction a snapshot of the database so readers never block writers and vice versa.",
        "technical",
        "Postgres uses MVCC so readers and writers don't block each other — each transaction sees its own snapshot.",
        "technical",
    ),
    # 8. PostgreSQL docs - VACUUM
    (
        "Per the PostgreSQL docs on routine maintenance, autovacuum must run regularly to reclaim space from dead tuples and prevent transaction ID wraparound.",
        "technical",
        "Autovacuum in Postgres has to run often enough to clean up dead tuples and avoid transaction ID wraparound.",
        "technical",
    ),
    # 9. Kubernetes API reference
    (
        "The Kubernetes API reference v1.29 states that a Pod's restartPolicy field only applies to containers in the same Pod and defaults to Always.",
        "technical",
        "A Pod's restartPolicy governs only the containers inside that Pod and defaults to Always.",
        "technical",
    ),
    # 10. Kubernetes docs - services
    (
        "Per the Kubernetes documentation on Services, a ClusterIP service exposes the service on an internal IP reachable only from within the cluster.",
        "technical",
        "Kubernetes ClusterIP services are only reachable from inside the cluster via an internal IP.",
        "technical",
    ),
    # 11. Docker docs - build cache
    (
        "The Docker documentation on BuildKit explains that each instruction in a Dockerfile creates a cacheable layer keyed by its inputs, and cache is invalidated when an instruction's inputs change.",
        "technical",
        "Docker build layers are cached per instruction, and changing an instruction's inputs busts the cache for that layer onward.",
        "technical",
    ),
    # 12. Docker Compose docs
    (
        "Per the Docker Compose specification v2, the 'depends_on' key only controls start order and does not wait for the referenced service to be ready unless a healthcheck condition is specified.",
        "technical",
        "In Compose, depends_on only orders startup; it doesn't wait for readiness unless you add a healthcheck condition.",
        "technical",
    ),
    # 13. Python language reference - GIL
    (
        "The CPython documentation on threading notes that the Global Interpreter Lock allows only one thread to execute Python bytecode at a time, even on multi-core systems.",
        "technical",
        "CPython's GIL means only one thread runs Python bytecode at a time, regardless of how many cores you have.",
        "technical",
    ),
    # 14. Python PEP 8
    (
        "PEP 8 recommends limiting all lines to a maximum of 79 characters and docstrings or comments to 72 characters.",
        "technical",
        "Python code should keep lines at or below 79 characters and comments below 72.",
        "technical",
    ),
    # 15. Python PEP 484 - type hints
    (
        "PEP 484 introduces a standard syntax for type hints using annotations, which the runtime ignores but static checkers like mypy consume.",
        "technical",
        "Python type hints are evaluated by static checkers like mypy and ignored at runtime.",
        "technical",
    ),
    # 16. Go language spec - goroutines
    (
        "The Go language specification defines a goroutine as a lightweight thread managed by the Go runtime, started with the 'go' keyword preceding a function call.",
        "technical",
        "Goroutines are Go-runtime-managed lightweight threads launched by prefixing a call with 'go'.",
        "technical",
    ),
    # 17. Rust reference - ownership
    (
        "Per the Rust reference on ownership, each value has exactly one owner and is dropped when the owner goes out of scope.",
        "technical",
        "In Rust, every value has one owner, and when that owner goes out of scope the value is dropped.",
        "technical",
    ),
    # 18. TCP RFC 9293
    (
        "RFC 9293 describes the TCP three-way handshake: SYN from client, SYN-ACK from server, ACK from client, establishing a full-duplex connection.",
        "technical",
        "TCP opens a connection with a three-way handshake: SYN, SYN-ACK, then ACK.",
        "technical",
    ),
    # 19. TLS RFC 8446
    (
        "RFC 8446 specifies TLS 1.3, which reduces the handshake to one round trip and removes support for legacy ciphers like RC4 and 3DES.",
        "technical",
        "TLS 1.3 has a single round-trip handshake and drops legacy ciphers such as RC4 and 3DES.",
        "technical",
    ),
    # 20. DNS RFC 1035
    (
        "RFC 1035 specifies that DNS messages over UDP are limited to 512 octets unless EDNS0 signals a larger buffer.",
        "technical",
        "DNS over UDP caps at 512 bytes per message unless EDNS0 negotiates a bigger size.",
        "technical",
    ),
    # 21. POSIX - fork
    (
        "The POSIX.1-2017 standard specifies that fork() returns zero in the child process and the child's PID in the parent process.",
        "technical",
        "After fork(), the child receives a return value of 0 and the parent receives the child's PID.",
        "technical",
    ),
    # 22. POSIX - signals
    (
        "Per POSIX, SIGKILL and SIGSTOP cannot be caught, blocked, or ignored by the receiving process.",
        "technical",
        "Processes cannot handle or mask SIGKILL or SIGSTOP.",
        "technical",
    ),
    # 23. W3C - CSS flexbox
    (
        "The W3C CSS Flexbox Level 1 specification defines justify-content as controlling the alignment of flex items along the main axis of the flex container.",
        "technical",
        "In CSS flexbox, justify-content aligns items along the main axis.",
        "technical",
    ),
    # 24. WHATWG HTML - async/defer
    (
        "The WHATWG HTML Living Standard specifies that a script tag with 'defer' is executed after the document has been parsed but before DOMContentLoaded.",
        "technical",
        "Defer scripts run after HTML parsing finishes but before DOMContentLoaded fires.",
        "technical",
    ),
    # 25. ECMAScript spec - strict equality
    (
        "The ECMAScript 2024 specification defines strict equality (===) as returning true only when the operands share the same type and value, without type coercion.",
        "technical",
        "JavaScript's === returns true only when both sides match in type and value with no coercion.",
        "technical",
    ),
    # 26. React docs - effects
    (
        "Per the React 18 documentation on useEffect, the effect is re-run whenever a value in the dependency array changes by Object.is comparison.",
        "ai_coding",
        "React's useEffect re-runs when any value in its dependency array changes via Object.is.",
        "ai_coding",
    ),
    # 27. PyTorch docs - autograd
    (
        "The PyTorch documentation on autograd states that gradients accumulate in .grad attributes until explicitly zeroed with optimizer.zero_grad() or tensor.grad.zero_().",
        "ai_coding",
        "PyTorch accumulates gradients in .grad until you zero them out; otherwise successive backward calls compound.",
        "ai_coding",
    ),
    # 28. Hugging Face transformers docs
    (
        "The Hugging Face Transformers documentation on tokenizers notes that AutoTokenizer.from_pretrained downloads the tokenizer config, vocab, and merges from the model repo on the Hub.",
        "ai_coding",
        "AutoTokenizer.from_pretrained pulls the tokenizer config, vocabulary, and merges from the Hub.",
        "ai_coding",
    ),
    # 29. TensorFlow docs - eager vs graph
    (
        "Per the TensorFlow 2 documentation, tf.function traces Python code into a callable graph, giving graph-mode performance while preserving an eager-mode authoring experience.",
        "ai_coding",
        "TF 2's tf.function turns Python into a traced graph so you get graph-mode speed but write code eagerly.",
        "ai_coding",
    ),
    # 30. OpenAI API reference
    (
        "The OpenAI API reference for chat completions specifies that the 'temperature' parameter ranges from 0 to 2, with higher values producing more random outputs.",
        "ai_coding",
        "OpenAI's chat completion temperature goes from 0 to 2; higher means more random sampling.",
        "ai_coding",
    ),
    # 31. Anthropic API docs
    (
        "Per the Anthropic API documentation, the 'stop_sequences' parameter accepts up to four strings that will cause the model to halt generation when produced.",
        "ai_coding",
        "Anthropic's Messages API accepts up to four stop sequences; generation halts when the model emits one.",
        "ai_coding",
    ),
    # 32. Redis docs - persistence
    (
        "The Redis documentation on persistence explains that RDB snapshots are point-in-time dumps while AOF logs every write command, and both can be enabled together.",
        "technical",
        "Redis can persist with RDB point-in-time snapshots, AOF command logs, or both at once.",
        "technical",
    ),
    # 33. MongoDB docs - indexes
    (
        "Per the MongoDB 7 documentation on indexes, a compound index supports queries that filter on a prefix of the indexed fields in the order they were declared.",
        "technical",
        "MongoDB compound indexes help any query that uses a left-to-right prefix of the declared fields.",
        "technical",
    ),
    # 34. Git docs - rebase
    (
        "The Git documentation on git-rebase warns that rebasing commits already pushed to a shared branch rewrites history and forces collaborators to reset their local copies.",
        "technical",
        "Rebasing already-pushed commits on a shared branch rewrites history and breaks other people's local branches.",
        "technical",
    ),
    # 35. Linux kernel docs - cgroups
    (
        "The Linux kernel documentation on cgroups v2 states that a process can only belong to one cgroup in each hierarchy at a time.",
        "technical",
        "Under cgroups v2, a process is in exactly one cgroup per hierarchy.",
        "technical",
    ),
    # 36. Nginx docs - worker processes
    (
        "The Nginx documentation recommends setting worker_processes to 'auto' so the server spawns one worker per available CPU core.",
        "technical",
        "Nginx's worker_processes 'auto' setting creates one worker per CPU core.",
        "technical",
    ),
    # 37. GraphQL spec
    (
        "The GraphQL June 2018 specification defines three operation types: query, mutation, and subscription, with query as the default when the operation keyword is omitted.",
        "technical",
        "GraphQL has queries, mutations, and subscriptions, and unmarked operations are treated as queries.",
        "technical",
    ),
    # 38. gRPC docs
    (
        "Per the gRPC documentation, the four supported RPC styles are unary, server streaming, client streaming, and bidirectional streaming.",
        "technical",
        "gRPC offers unary, server-streaming, client-streaming, and bidirectional-streaming RPCs.",
        "technical",
    ),
    # 39. Protobuf docs
    (
        "The Protocol Buffers language guide for proto3 states that scalar fields have default values and are not serialized when set to their default.",
        "technical",
        "In proto3, scalar fields at their default values are skipped on the wire.",
        "technical",
    ),
    # 40. AWS S3 docs
    (
        "Per the AWS S3 documentation, objects uploaded via multipart upload must have each part at least 5 MB except for the final part.",
        "technical",
        "S3 multipart upload parts must be 5 MB or larger, except the last one.",
        "technical",
    ),
    # 41. AWS IAM docs
    (
        "The AWS IAM documentation on policy evaluation states that an explicit Deny in any applicable policy overrides any Allow.",
        "technical",
        "If any IAM policy explicitly denies an action, the request is denied regardless of other allows.",
        "technical",
    ),
    # 42. Terraform docs - state
    (
        "Per the Terraform documentation, the state file maps real-world resources to the configuration and must be shared via a remote backend when working in a team.",
        "technical",
        "Terraform's state maps resources to config and should live in a remote backend for team workflows.",
        "technical",
    ),
    # 43. Ansible docs - idempotency
    (
        "The Ansible documentation on module design emphasizes that modules should be idempotent, producing the same end state whether run once or many times.",
        "technical",
        "Ansible modules are expected to be idempotent — running them repeatedly yields the same end state.",
        "technical",
    ),
    # 44. NumPy docs - broadcasting
    (
        "Per the NumPy documentation on broadcasting, two array shapes are compatible when, aligned from the trailing axis, each dimension is either equal or one of them is 1.",
        "ai_coding",
        "NumPy broadcasts two arrays when, aligned from the right, each dimension matches or one equals 1.",
        "ai_coding",
    ),
    # 45. Pandas docs - inplace
    (
        "The Pandas 2.2 documentation warns that the 'inplace' parameter is being deprecated because it does not reliably avoid copies and complicates method chaining.",
        "ai_coding",
        "Pandas is phasing out the inplace parameter since it doesn't really avoid copies and hurts chaining.",
        "ai_coding",
    ),
    # 46. Scikit-learn docs
    (
        "Per the scikit-learn documentation, StandardScaler removes the mean and scales to unit variance using statistics fit on the training data only.",
        "ai_coding",
        "StandardScaler centers and scales features using stats fit from the training set.",
        "ai_coding",
    ),
    # 47. CUDA programming guide
    (
        "The NVIDIA CUDA C++ Programming Guide specifies that threads within a warp execute the same instruction at the same time, and divergent branches are serialized.",
        "technical",
        "CUDA warp threads run in lockstep; branches that diverge within a warp run serially.",
        "technical",
    ),
    # 48. Unicode standard
    (
        "The Unicode Standard version 15 specifies that code points in the range U+D800 to U+DFFF are surrogate code points reserved for UTF-16 and are not valid in UTF-8.",
        "technical",
        "Surrogate code points U+D800 through U+DFFF belong to UTF-16 and must not appear in UTF-8.",
        "technical",
    ),
    # 49. Semantic Versioning spec
    (
        "The Semantic Versioning 2.0.0 specification states that a MAJOR version increment signals incompatible API changes, while MINOR adds functionality in a backward-compatible way.",
        "technical",
        "SemVer bumps MAJOR for breaking API changes and MINOR for backward-compatible features.",
        "technical",
    ),
    # 50. WebAssembly spec
    (
        "The WebAssembly Core Specification 2.0 defines a linear memory as a contiguous, byte-addressable array that can be grown in pages of 64 KiB.",
        "technical",
        "WebAssembly linear memory is a contiguous byte array that grows in 64 KiB pages.",
        "technical",
    ),
]


def emit() -> int:
    OUT.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with OUT.open("w", encoding="utf-8") as f:
        for i, (ref_text, ref_domain, fact_text, fact_domain) in enumerate(PAIRS, start=1):
            pair_id = f"cls-pair-{PAIR_OFFSET + i:05d}"
            ref_id = f"class-{ID_OFFSET + (2 * i - 1):05d}"
            fact_id = f"class-{ID_OFFSET + (2 * i):05d}"
            f.write(json.dumps({"id": ref_id, "domain": ref_domain, "text": ref_text, "memory_type": "reference", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            f.write(json.dumps({"id": fact_id, "domain": fact_domain, "text": fact_text, "memory_type": "fact", "pair_id": pair_id}, ensure_ascii=False) + "\n")
            written += 2
    return written


if __name__ == "__main__":
    n = emit()
    print(f"wrote {n} rows to {OUT}")
