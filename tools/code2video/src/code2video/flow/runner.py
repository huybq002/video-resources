"""Chạy flow như một job của JobQueue (mode 'flow')."""
from __future__ import annotations

from pathlib import Path

from .flow import FlowError, run_flow, validate_flow
from . import rules, store
from .nodes import ENGINE_NODES, NODES, FlowContext


def validate_for_engine(flow: dict) -> list[str]:
    """Lỗi schema + node không hợp lệ với engine của flow."""
    errors = validate_flow(flow, set(NODES))
    allowed = ENGINE_NODES.get(flow.get("engine", ""))
    if allowed is None:
        errors.append(f"engine không hợp lệ: {flow.get('engine')}")
        return errors
    for node_id, node in (flow.get("nodes") or {}).items():
        if isinstance(node, dict) and node.get("type") in NODES and node["type"] not in allowed:
            errors.append(f"Node '{node_id}' ({node['type']}) không dùng được với engine {flow['engine']}.")
    nodes = flow.get("nodes") or {}
    for edge in flow.get("edges") or []:
        a, b = nodes.get(edge.get("from")), nodes.get(edge.get("to"))
        if isinstance(a, dict) and isinstance(b, dict) and a.get("type") in NODES and b.get("type") in NODES:
            problem = rules.edge_problem(a["type"], b["type"], flow.get("engine") or "whiteboard")
            if problem:
                errors.append(f"Dây {edge['from']} → {edge['to']}: {problem}")
    return errors


def _with_topic(flow: dict, topic: str) -> dict:
    nodes = {}
    for node_id, node in flow["nodes"].items():
        if node.get("type") == "idea":
            node = {**node, "config": {**(node.get("config") or {}), "text": topic}}
        nodes[node_id] = node
    return {**flow, "nodes": nodes}


def execute_flow_job(job, queue) -> None:
    """Chạy flow trong worker thread; cập nhật label/progress job theo node, ghi kết quả vào job."""
    params = job.params
    flow = params["flow"]
    run_dir = Path(params["outputDir"])
    run_dir.mkdir(parents=True, exist_ok=True)
    state: dict = {}
    flow_id = params.get("flowId") or ""
    outputs: dict = {}

    def persist(status: str, **extra) -> None:
        if not flow_id:
            return
        try:
            store.write_run(flow_id, {
                "flowId": flow_id, "jobId": job.id, "outputDir": str(run_dir), "status": status,
                "doneNodes": list(done_nodes), "outputs": outputs, **extra,
            })
        except (OSError, ValueError):
            pass  # lưu lịch sử là phụ, không làm hỏng lần chạy

    if params.get("topic"):
        flow = _with_topic(flow, params["topic"])
    ctx = FlowContext(run_dir=run_dir, engine=flow["engine"], tts_lock=queue._tts_lock)
    total = max(1, len(flow["nodes"]))
    done_nodes: list[str] = []

    def on_step(node_id: str, kind: str, message: str) -> None:
        with queue._lock:
            if kind == "start":
                job.stage = "flow"
                job.label = f"Flow: {message}"
                job.result = {"activeNode": node_id, "doneNodes": list(done_nodes), "outputs": outputs}
            elif kind == "done":
                done_nodes.append(node_id)
                outputs[node_id] = state.get(node_id)
                job.progress = min(0.95, len(done_nodes) / total)
                job.result = {"activeNode": None, "doneNodes": list(done_nodes), "outputs": outputs}
            job.version += 1
        if kind == "start":
            persist("running", activeNode=node_id)
        elif kind == "done":
            persist("running")

    job.output_dir = run_dir
    persist("running")
    try:
        run_flow(flow, state, NODES, ctx, on_step)
    except FlowError as error:
        if error.node_id and error.node_id not in outputs and isinstance(state.get(error.node_id), dict):
            outputs[error.node_id] = state[error.node_id]
        with queue._lock:
            job.result = {"state": state, "failedNode": error.node_id, "doneNodes": list(done_nodes), "outputs": outputs}
        persist("error", failedNode=error.node_id, message=str(error))
        raise
    with queue._lock:
        job.result = {"outputDir": str(run_dir), "video": state.get("video"), "renderer": flow["engine"], "state": state,
                      "doneNodes": list(done_nodes), "outputs": outputs}
        job.status = "done"
        job.progress = 1.0
        job.stage = "done"
        job.label = "Hoàn tất"
        job.version += 1
    persist("done", video=state.get("video"))
