import hashlib
import json
from pathlib import Path
import re
import pytest

CONTRACT=str(Path(__file__).parents[1]/"corroboration_signal.py")
CLAIM="The 1.2 release includes a public JSON API."
URLS=["https://raw.githubusercontent.com/"+owner+"/notes/"+letter*40+"/release.txt" for owner,letter in [("alpha","a"),("beta","b"),("gamma","c")]]
DOCS=["Release 1.2 provides a documented public JSON API.","Our release notes confirm the public JSON API in version 1.2.","The version 1.2 public JSON API is now documented."]
HASHES=[hashlib.sha256(body.encode()).hexdigest() for body in DOCS]
COUNTER_URL="https://raw.githubusercontent.com/delta/notes/"+"d"*40+"/correction.txt"
COUNTER="Correction: release 1.2 has no public JSON API; that feature is in 1.3."
COUNTER_SHA=hashlib.sha256(COUNTER.encode()).hexdigest()

def deploy(direct_vm,direct_deploy):
    direct_vm.warp("2026-10-21T00:00:00Z")
    return direct_deploy(CONTRACT)

def request(c,urls=URLS,hashes=HASHES):
    return c.request(CLAIM,urls,hashes,300,600)

def serve(direct_vm,urls=URLS,docs=DOCS):
    for url,body in zip(urls,docs):
        direct_vm.mock_web(re.escape(url),{"status":200,"body":body})

def model(direct_vm,stances=None,docs=DOCS):
    stances=stances or ["SUPPORTS","SUPPORTS","SUPPORTS"]
    cites=[{"source":i,"quote":docs[i]} for i,stance in enumerate(stances) if stance in ("SUPPORTS","REFUTES")]
    direct_vm.mock_llm("CORROBORATION_SIGNAL_V1",json.dumps({"stances":stances,"citations":cites}))

def observed(direct_vm,c):
    rid=request(c)
    serve(direct_vm)
    model(direct_vm)
    c.observe(rid)
    return rid

def test_observation_binds_sources_claim_time_and_contract(direct_vm,direct_deploy):
    """Catches missing substantive source consensus or context/time binding."""
    c=deploy(direct_vm,direct_deploy)
    rid=observed(direct_vm,c)
    out=c.get_signal(rid)
    assert out["status"]=="SUPPORTED"
    assert out["quorum"]==2
    assert out["support_count"]==3
    assert out["claim_sha256"]==hashlib.sha256(CLAIM.encode()).hexdigest()
    assert out["observed_at"]==1792540800
    assert out["valid_until"]==1792541400
    assert out["observations"][0]["digests"]==HASHES
    assert direct_vm.run_validator() is True
    assert c.is_current_supported(rid,out["claim_sha256"]) is True
    assert c.is_current_supported(rid,"00"*32) is False
    with direct_vm.expect_revert("not pending"):
        c.observe(rid)

@pytest.mark.parametrize("stances,want",[( ["SUPPORTS","SUPPORTS","UNRELATED"],"SUPPORTED"),(["REFUTES","REFUTES","UNRELATED"],"REFUTED"),(["SUPPORTS","SUPPORTS","REFUTES"],"CONTESTED"),(["SUPPORTS","UNCERTAIN","UNRELATED"],"INSUFFICIENT"),(["UNCERTAIN","UNCERTAIN","UNCERTAIN"],"INSUFFICIENT")])
def test_status_is_derived_from_substantive_stances(direct_vm,direct_deploy,stances,want):
    c=deploy(direct_vm,direct_deploy)
    rid=request(c)
    serve(direct_vm)
    model(direct_vm,stances)
    c.observe(rid)
    assert c.get_signal(rid)["status"]==want

def test_validator_refetches_changed_source_and_reclassifies(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    rid=observed(direct_vm,c)
    direct_vm.clear_mocks()
    serve(direct_vm,docs=[DOCS[0],"Changed second source bytes.",DOCS[2]])
    model(direct_vm)
    assert direct_vm.run_validator() is False
    direct_vm.clear_mocks()
    serve(direct_vm)
    model(direct_vm,["REFUTES","REFUTES","REFUTES"])
    assert direct_vm.run_validator() is False

def test_validator_rejects_forged_status_counts_and_quotes(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    rid=observed(direct_vm,c)
    packet={"stances":["SUPPORTS"]*3,"citations":[{"source":i,"quote":DOCS[i]} for i in range(3)],"digests":HASHES}
    assert direct_vm.run_validator(leader_result=dict(packet,status="SUPPORTED",support_count=999)) is False
    forged=dict(packet,citations=[{"source":0,"quote":"A fabricated quoted claim is never present in the evidence."}])
    assert direct_vm.run_validator(leader_result=forged) is False

@pytest.mark.parametrize("change",["same_owner","duplicate_url","branch","private_host","missing_hash","bad_hash","too_few"])
def test_source_policy_is_bound_at_request(direct_vm,direct_deploy,change):
    c=deploy(direct_vm,direct_deploy)
    urls=list(URLS); hashes=list(HASHES)
    if change=="same_owner": urls[1]=urls[1].replace("/beta/","/alpha/")
    if change=="duplicate_url": urls[1]=urls[0]
    if change=="branch": urls[0]=urls[0].replace("a"*40,"main")
    if change=="private_host": urls[0]="https://localhost/secret"
    if change=="missing_hash": hashes=hashes[:2]
    if change=="bad_hash": hashes[0]="z"*64
    if change=="too_few": urls=urls[:2]; hashes=hashes[:2]
    with direct_vm.expect_revert():
        request(c,urls,hashes)

def test_bad_transport_does_not_create_false_signal(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    rid=request(c)
    direct_vm.mock_web(re.escape(URLS[0]),{"status":503,"body":"Service unavailable"})
    with direct_vm.expect_revert("SOURCE"):
        c.observe(rid)
    assert c.get_signal(rid)["status"]=="PENDING"

@pytest.mark.parametrize("output",[{"stances":["SUPPORTS"]*3,"citations":[]},{"stances":["YES"]*3,"citations":[]},{"stances":["SUPPORTS"],"citations":[]},{"stances":["UNCERTAIN"]*3,"citations":[],"final_status":"SUPPORTED"}])
def test_model_invalid_or_injected_output_cannot_finalize(direct_vm,direct_deploy,output):
    c=deploy(direct_vm,direct_deploy)
    rid=request(c)
    serve(direct_vm)
    direct_vm.mock_llm("CORROBORATION_SIGNAL_V1",json.dumps(output))
    with direct_vm.expect_revert("invalid assessment"):
        c.observe(rid)
    assert c.get_signal(rid)["status"]=="PENDING"

def test_observation_and_validity_deadlines(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    pending=request(c)
    rid=observed(direct_vm,c)
    direct_vm.warp("2026-10-21T00:05:00Z")
    with direct_vm.expect_revert("observation window"):
        c.observe(pending)
    c.expire(pending)
    assert c.get_signal(pending)["status"]=="EXPIRED"
    direct_vm.warp("2026-10-21T00:10:00Z")
    assert c.is_current_supported(rid,hashlib.sha256(CLAIM.encode()).hexdigest()) is False
    c.expire(rid)
    assert c.get_signal(rid)["status"]=="EXPIRED"

def test_verified_counter_source_changes_signal_without_extending_ttl(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    rid=observed(direct_vm,c)
    direct_vm.clear_mocks()
    serve(direct_vm,URLS+[COUNTER_URL],DOCS+[COUNTER])
    model(direct_vm,["SUPPORTS"]*3+["REFUTES"],DOCS+[COUNTER])
    direct_vm.warp("2026-10-21T00:01:00Z")
    c.challenge(rid,COUNTER_URL,COUNTER_SHA)
    out=c.get_signal(rid)
    assert out["status"]=="CONTESTED"
    assert out["quorum"]==3
    assert out["refute_count"]==1
    assert out["valid_until"]==1792541400
    assert out["observations"][1]["observed_at"]==1792540860
    assert direct_vm.run_validator() is True
    assert c.is_current_supported(rid,hashlib.sha256(CLAIM.encode()).hexdigest()) is False
    with direct_vm.expect_revert("challenge unavailable"):
        c.challenge(rid,COUNTER_URL,COUNTER_SHA)

def test_frivolous_or_same_publisher_challenge_cannot_suspend(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    rid=observed(direct_vm,c)
    with direct_vm.expect_revert("new publisher"):
        c.challenge(rid,URLS[0].replace("release.txt","other.txt"),HASHES[0])
    direct_vm.clear_mocks()
    serve(direct_vm,URLS+[COUNTER_URL],DOCS+[COUNTER])
    model(direct_vm,["SUPPORTS"]*3+["UNRELATED"],DOCS+[COUNTER])
    with direct_vm.expect_revert("opposite stance"):
        c.challenge(rid,COUNTER_URL,COUNTER_SHA)
    assert c.get_signal(rid)["status"]=="SUPPORTED"

def test_pending_cancellation_requester_only(direct_vm,direct_deploy):
    c=deploy(direct_vm,direct_deploy)
    rid=request(c)
    from gltest.direct import create_address
    with direct_vm.prank(create_address("outsider")):
        with direct_vm.expect_revert("requester only"):
            c.cancel(rid)
    c.cancel(rid)
    assert c.get_signal(rid)["status"]=="CANCELED"
    with direct_vm.expect_revert("not pending"):
        c.observe(rid)
