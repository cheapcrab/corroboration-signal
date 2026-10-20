# CorroborationSignal design / test plan

AI-assisted independent IC prototype, 2026-10-21. No identity, real-world truth or editorial independence claims.

A requester fixes a bounded factual claim, observation deadline, TTL and 3..5 public source locators plus exact content hashes. Each source must pin a GitHub/gist commit. Extracted GitHub account namespaces must be distinct. This is a reproducible publisher namespace policy; one person can control several namespaces, and copying sources does not become independent evidence.

Leader and validators independently fetch all sources, verify each locked byte digest, and independently classify each source as SUPPORTS/REFUTES/UNRELATED/UNCERTAIN against the exact claim. Any directional stance needs a source-specific exact quote. Validator checks proposed citations against its own fetched documents and compares the independently derived stances and digests. Deterministic code computes majority quorum and SUPPORTED/REFUTED/CONTESTED/INSUFFICIENT; mixed directional evidence is CONTESTED even when one side has a majority. The model cannot submit final status or support counts.

Observations bind contract, chain, claim hash, source order, source hashes and transaction observation time. They expire after TTL. One active directional signal may be challenged with a new publisher namespace and hash-pinned source; only an independently confirmed opposite stance can change state. All original sources are re-fetched and reclassified too. Challenge does not extend validity. Expiry and pending cancellation are deterministic. No governance electorate/charter or two-resource control proof is reused.

TDD: real deployable SDK artifact; source quorum/grouping; digest and time binding; changed validator data; quote/stance/model forgery; majority/contradiction/insufficiency; deadline and TTL boundaries; opposing-source challenge; same-publisher and unsupported challenges; one challenge; unknown IDs and access. Direct mode mocks only external transport/model responses; no live consensus or deployment is asserted.
