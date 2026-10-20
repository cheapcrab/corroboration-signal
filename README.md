# CorroborationSignal

AI-assisted, unaudited prototype: a standalone GenLayer Intelligent Contract that records a time-bounded, auditable cross-source signal for a fixed public factual claim. It measures what selected public documents say. It does not prove world truth, real authorship, source independence, or identity.

This is an independent IC contribution. Its source-level stance aggregation, contradiction rule, publisher namespace policy, fixed TTL and substantive counter-source challenge are distinct from the profile02 proof/governance ICs and MilestoneRemedy's bilateral dispute protocol. Only generic SDK/time/transport/testing primitives are reused.

## Consensus boundary

The requester fixes a claim, 3..5 commit-pinned public document URLs, each exact SHA-256 digest, an observation deadline and TTL. Each source must come from a different case-normalized GitHub account namespace, including gist accounts. Distinct namespaces are an explicit diversity filter; one person can control several, and copied documents can repeat the same underlying source.

Leader and validators independently fetch every source, verify its fixed digest and independently classify each document as SUPPORTS, REFUTES, UNRELATED or UNCERTAIN relative to the claim's exact version/time scope. Every directional stance requires an exact quoted substring from that same source. The validator checks leader quotations against its own fresh bytes and compares independently derived stances and digests. Shape checking alone cannot approve the leader's position.

Deterministic code computes strict-majority quorum `floor(source_count/2)+1`, counts and status:

| Evidence pattern | Status |
|---|---|
| At least one SUPPORTS and at least one REFUTES | CONTESTED, regardless of numerical majority |
| No REFUTES and SUPPORTS >= quorum | SUPPORTED |
| No SUPPORTS and REFUTES >= quorum | REFUTED |
| Otherwise | INSUFFICIENT |

The model cannot return a final status, counts, quorum or expiry. Extra fields are rejected. Source order, claim hash, contract/chain context and transaction observation time are bound to each stored observation.

## Source and interface

`corroboration_signal.py` is the only deployable file. It pins the official concrete runner `py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6`. Constructor has **no arguments** (`[]`); no secret/API key is supplied.

| Method | Effect |
|---|---|
| `request(claim,urls,sha256s,observation_seconds,ttl_seconds) -> id` | Fixes bounded claim/source policy. Claim <=2000 characters; 3..5 sources and matching hashes; distinct publisher namespaces; both durations 60..86400 seconds. |
| `observe(id)` | Anyone may execute once while PENDING, strictly before observation deadline. Independent fetch/classification produces the signal; validity ends at observation transaction time + fixed TTL. |
| `challenge(id,url,sha256)` | One active SUPPORTED/REFUTED signal may receive one new namespace/source. All original and new sources are independently re-fetched/reclassified. The new source must substantiate the opposite directional stance; otherwise no state change. TTL is never extended. |
| `expire(id)` | Anyone materializes EXPIRED at pending observation deadline or observed validity cutoff. |
| `cancel(id)` | Requester only while PENDING. CANCELED is terminal. |
| `get_signal(id)` | Full claim, fixed sources, historical observations, digests/citations, counters and current stored status. |
| `is_current_supported(id,claim_sha256)` | True only for SUPPORTED, exact intended claim hash and transaction time strictly before validity cutoff. |

A failed source fetch or invalid model output leaves PENDING unchanged; it cannot create a negative factual signal. A failed/frivolous challenge leaves the existing observation unchanged. Requests/observations are separate records: renewing a stale signal requires a fresh request and observation rather than overwriting its history.

## Source and time policy

Only these requested HTTPS locators are supported:

```text
https://raw.githubusercontent.com/<account>/<repo>/<40-lowercase-hex-commit>/<path>
https://gist.githubusercontent.com/<account>/<32-lowercase-hex-gist>/raw/<40-lowercase-hex-version>/<path>
```

URL length <=512, safe ASCII path, no credentials/port/query/fragment/dot segments or mutable branches. Each body must be HTTP 200, nonempty UTF-8, <=16000 bytes and match the supplied 64-lowercase-hex SHA-256. A challenge may increase the set to at most six sources. Every historical observation records the exact source set, hashes and time, so consumers can inspect which revision produced a signal.

`observed_at` is retrieval/evaluation transaction time, not verified publication time or proof that documents describe the current world. Pinned old snapshots cannot establish a fresh real-world condition without evidence for that claim's temporal scope. The prompt explicitly requires uncertainty rather than inferring present facts from old documents. TTL controls signal usability; it does not make source assertions true or fresh automatically.

The pinned SDK does not expose final URL, redirect policy or a pre-download size setting. Host restrictions apply to the requested URL and body limits apply after receipt. Runtime TLS/DNS, any internal redirects, bandwidth and GitHub/gist availability remain transport assumptions. Missing/changed sources prevent an observation/revision instead of silently changing its evidence.

## Threat model and integration

Attackers may create multiple publisher namespaces, coordinate copies, publish false claims, select biased sources, embed prompt injection, forge a leader's status/counts/citations, or submit frivolous challenges. Namespace filtering, immutable hashes, bounded work, independent reclassification and exact citation checks address specific protocol attacks; they do not establish editorial independence, reputation or truthful reporting. Citation presence alone is not entailment; semantic assessment is independently repeated by validators. Correlated models may still make the same mistake.

All documents and request context are untrusted data. Instructions inside sources cannot legitimately change the schema or aggregation rules. Tests check rejection of injected/extra outcome fields; they do not demonstrate live prompt-injection immunity. A confirmed single contrary source makes the result CONTESTED under the stated conservative rule. Only one successful challenge is available; later contradictory evidence needs a new request, which integrations should be prepared to consume. There is no autonomous crawl, renewal or background monitoring.

Integrators should bind the request ID, exact claim hash, source policy and intended temporal scope, require suitably finalized network state, and check `is_current_supported` at use time. `get_signal` can retain a stored SUPPORTED label after wall time passes until someone materializes expiry; the boolean view enforces expiry immediately using transaction time. Treat the result as a provenance-backed document signal, never a sole basis for irreversible high-stakes action.

## Verification

Python 3.12+, dedicated environment:

```text
python -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
.venv/Scripts/python.exe tools/verify.py
```

Use `.venv/bin/python` on Linux/macOS. Verification loads the exact pinned SDK from the official GenVM v0.2.12 artifact, runs the actual deployable file's direct tests, semantic lint and ABI extraction, and binds the source digest in `evidence/verification.json`.

`evidence/tdd-red.log` records the real NOT_IMPLEMENTED failure before implementation. The final **24 passing tests** cover context/source/time binding, all aggregation outcomes, independent source/model divergence, forged counts/status/quotes, source namespace/pinning/hash policy, bad transport, malformed model output, pending deadline and TTL boundaries, genuine opposite-source challenge, frivolous/same-publisher rejection and requester cancellation. `verification-tests.log`, `verification-lint.log` and `verification-schema.log` are the final evidence.

External network/model responses are explicitly mocked; captured official validator functions execute against replaced fixtures. Fixture URLs and documents are fictional, not asserted live sources. Test-only upstream gltest 0.29.2 compatibility in `tests/conftest.py` fixes open-stdin file cleanup on Windows and `warp()` message-time refresh; it does not replace production/validator logic. The constructor is deployed on GenLayer Studio (chain 61999) with FINALIZED / leader SUCCESS and normal majority consensus. On-chain source bytes match the locally tested SHA-256; see `evidence/deployment.json`. One idle validation execution was cancelled nonfatally after quorum (CONSENSUS_VALIDATOR_QUORUM_REACHED), which is retained in the evidence. Deployment used zero native value and displayed zero GEN network fee. Live source classification/challenge flows, model quality, production performance and non-Studio gas costs remain unverified. No users, audit or production results are claimed.

Official references checked on 2026-10-21: [boilerplate](https://github.com/genlayerlabs/genlayer-project-boilerplate), [equivalence principle](https://docs.genlayer.com/developers/intelligent-contracts/equivalence-principle), [storage](https://docs.genlayer.com/developers/intelligent-contracts/features/storage), [transaction context](https://docs.genlayer.com/developers/intelligent-contracts/features/transaction-context), [direct API](https://github.com/genlayerlabs/genlayer-testing-suite/blob/main/docs/direct-runner.md), [exact SDK release](https://github.com/genlayerlabs/genvm/releases/tag/v0.2.12). Pinned SDK signatures were inspected.

MIT licensed; see `LICENSE`.
