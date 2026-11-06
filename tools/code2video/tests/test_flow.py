import asyncio
import json
from pathlib import Path

import pytest
from fastapi import HTTPException

from code2video.flow import store
from code2video.flow.conditions import evaluate
from code2video.flow.flow import FlowError, run_flow, validate_flow
from code2video.flow.nodes import NODES, FlowContext
from code2video.flow.runner import validate_for_engine
from code2video.studio import app as studio

TEMPLATES = Path(__file__).resolve().parents[1] / "flows" / "templates"


def test_conditions_operators_nested_and_missing() -> None:
    state = {"a": {"b": {"c": 5}}, "s": "x"}
    assert evaluate({"field": "a.b.c", "op": "eq", "value": 5}, state)
    assert evaluate({"field": "a.b.c", "op": "gt", "value": 4}, state)
    assert evaluate({"field": "a.b.c", "op": "lt", "value": 9}, state)
    assert evaluate({"field": "s", "op": "in", "value": ["x", "y"]}, state)
    assert evaluate({"field": "s", "op": "ne", "value": "y"}, state)
    assert evaluate({"field": "a.b", "op": "exists"}, state)
    assert evaluate({"field": "a.zzz", "op": "missing"}, state)
    assert not evaluate({"field": "a.zzz", "op": "eq", "value": 1}, state)
    assert not evaluate({"field": "a.zzz", "op": "ne", "value": 1}, state)
    assert not evaluate({"field": "s", "op": "gt", "value": 3}, state)
    assert evaluate(None, state)
    with pytest.raises(ValueError):
        evaluate({"field": "s", "op": "bogus"}, state)


def graph(edges, nodes=("a", "b", "c")):
    return {"start": nodes[0], "engine": "whiteboard", "nodes": {n: {"type": "t"} for n in nodes}, "edges": edges}


def test_branching_follows_first_matching_edge() -> None:
    registry = {"t": lambda state, config, ctx: {"v": 1}}
    flow = graph([
        {"from": "a", "to": "b", "condition": {"field": "a.v", "op": "gt", "value": 5}},
        {"from": "a", "to": "c", "condition": {"field": "a.v", "op": "lt", "value": 5}},
    ])
    assert set(run_flow(flow, {}, registry)) - {"_types"} == {"a", "c"}


def test_dead_branch_ends_normally() -> None:
    flow = graph([{"from": "a", "to": "b", "condition": {"field": "nope", "op": "exists"}}], nodes=("a", "b"))
    assert "b" not in run_flow(flow, {}, {"t": lambda *a: {}})


def test_loop_retries_until_success_then_error_cleared() -> None:
    calls = {"n": 0}

    def flaky(state, config, ctx):
        calls["n"] += 1
        return {"error": "tam loi"} if calls["n"] < 3 else {"ok": True}

    flow = graph(
        [
            {"from": "a", "to": "a", "condition": {"field": "a.error", "op": "exists"}, "maxLoop": 3},
            {"from": "a", "to": "b", "condition": {"field": "a.ok", "op": "exists"}},
        ],
        nodes=("a", "b"),
    )
    flow["nodes"]["b"] = {"type": "end"}
    state = run_flow(flow, {}, {"t": flaky, "end": lambda *a: {}})
    assert calls["n"] == 3 and "error" not in state["a"] and "b" in state


def test_loop_exceeding_max_raises() -> None:
    flow = graph(
        [{"from": "a", "to": "a", "condition": {"field": "a.error", "op": "exists"}, "maxLoop": 2}],
        nodes=("a",),
    )
    with pytest.raises(FlowError, match="lặp quá 2 lần"):
        run_flow(flow, {}, {"t": lambda *a: {"error": "x"}})


def test_node_exception_stops_and_records_error() -> None:
    def boom(state, config, ctx):
        raise RuntimeError("hong")

    flow = graph([{"from": "a", "to": "b"}], nodes=("a", "b"))
    state: dict = {}
    steps = []
    with pytest.raises(FlowError, match="Lỗi tại node") as info:
        run_flow(flow, state, {"t": boom}, on_step=lambda *s: steps.append(s))
    assert info.value.node_id == "a"
    assert state["a.error"] == "hong" and "b" not in state
    assert steps[-1][1] == "error"


def test_validate_flow_catches_problems() -> None:
    bad = {"start": "zz", "nodes": {"a": {"type": "nope"}, "b": {"type": "t"}},
           "edges": [{"from": "a", "to": "ghost"}]}
    errors = validate_flow(bad, {"t"})
    assert any("start" in e for e in errors) and any("type" in e for e in errors)
    orphan = graph([{"from": "a", "to": "b"}], nodes=("a", "b", "c"))
    assert any("không thể tới được" in e for e in validate_flow(orphan, {"t"}))
    assert any("maxLoop" in e for e in validate_flow(graph([{"from": "a", "to": "b", "maxLoop": 0}]), {"t"}))


def test_templates_are_valid_for_their_engine() -> None:
    for template in ("wb-story", "hf-scenes"):
        assert validate_for_engine(store.read_template(template)) == []
    wrong = store.read_template("wb-story")
    wrong["engine"] = "hyperframes"
    assert any("không dùng được" in e for e in validate_for_engine(wrong))


def test_whiteboard_template_runs_through_tts_with_demo_provider(tmp_path: Path) -> None:
    flow = store.read_template("wb-story")
    flow["nodes"]["script"]["config"]["provider"] = "demo"
    flow["nodes"]["tts"]["config"]["dryRun"] = True
    nodes = {k: v for k, v in flow["nodes"].items() if k not in ("render", "merge")}
    trimmed = {**flow, "nodes": nodes, "edges": [e for e in flow["edges"] if e["from"] != "tts" and e["to"] in nodes]}
    state = run_flow(trimmed, {}, NODES, FlowContext(run_dir=tmp_path, engine="whiteboard"))
    assert len(state["resources"]) == 2
    for folder in state["resources"]:
        assert (Path(folder) / "voiceover.wav").is_file()
        assert (Path(folder) / "script.srt").is_file()


def test_slugify_strips_vietnamese_diacritics() -> None:
    assert store.slugify("Phim thử Đầu tiên!") == "phim-thu-dau-tien"
    assert store.slugify("???") == "flow"


def test_store_rejects_path_traversal(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(store, "FLOWS_ROOT", tmp_path / "flows")
    for bad in ("../evil", "a/b", "", "A", ".hidden"):
        with pytest.raises(ValueError):
            store.write_flow(bad, {})
    store.write_flow("ok-1", {"name": "n", "engine": "whiteboard"})
    assert store.list_flows() == [{"id": "ok-1", "name": "n", "engine": "whiteboard"}]
    store.delete_flow("ok-1")
    assert store.list_flows() == []


class Body:
    def __init__(self, payload) -> None:
        self._payload = payload

    async def json(self):
        return self._payload


def test_flow_api_template_save_validate_delete(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(store, "FLOWS_ROOT", tmp_path / "flows")
    template_dir = tmp_path / "flows" / "templates"
    template_dir.mkdir(parents=True)
    for src in TEMPLATES.glob("*.flow.json"):
        (template_dir / src.name).write_text(src.read_text(encoding="utf-8"), encoding="utf-8")

    created = asyncio.run(studio.flow_from_template(Body({"template": "wb-story", "name": "Phim thu"})))
    assert created["id"] == "phim-thu"
    assert [f["id"] for f in studio.list_flows()] == ["phim-thu"]
    assert studio.get_flow("phim-thu")["engine"] == "whiteboard"

    with pytest.raises(HTTPException) as info:
        asyncio.run(studio.put_flow("phim-thu", Body(dict(created, start="khong-co"))))
    assert info.value.status_code == 422
    with pytest.raises(HTTPException) as info:
        studio.get_flow("../x")
    assert info.value.status_code == 400
    with pytest.raises(HTTPException) as info:
        studio.get_flow("khong-ton-tai")
    assert info.value.status_code == 404

    studio.delete_flow("phim-thu")
    assert studio.list_flows() == []


def test_flow_run_enqueues_job(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setattr(store, "FLOWS_ROOT", tmp_path / "flows")
    store.write_flow("f1", json.loads((TEMPLATES / "wb-story.flow.json").read_text(encoding="utf-8")))
    captured: dict = {}

    class FakeJob:
        id = "j1"

    monkeypatch.setattr(studio, "RUNS_ROOT", tmp_path / "runs")
    monkeypatch.setattr(studio.queue, "enqueue", lambda params, job_id=None: captured.update(params) or FakeJob())
    result = asyncio.run(studio.run_flow_job(Body({"flowId": "f1", "topic": "chu de moi"})))
    assert json.loads(result.body)["jobId"] == "j1"
    assert captured["mode"] == "flow" and captured["topic"] == "chu de moi"
