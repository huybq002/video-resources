"""Executor: chạy flow từ node start, rẽ nhánh/loop theo điều kiện, có giới hạn lặp."""
from __future__ import annotations

from typing import Callable

from .conditions import OPS, evaluate

DEFAULT_MAX_LOOP = 3
OnStep = Callable[[str, str, str], None]


class FlowError(RuntimeError):
    def __init__(self, message: str, node_id: str | None = None) -> None:
        super().__init__(message)
        self.node_id = node_id


def validate_flow(flow: dict, node_types: set[str]) -> list[str]:
    """Trả về danh sách lỗi schema (rỗng = hợp lệ)."""
    errors: list[str] = []
    nodes = flow.get("nodes")
    if not isinstance(nodes, dict) or not nodes:
        return ["Flow cần object nodes không rỗng."]
    start = flow.get("start")
    if start not in nodes:
        errors.append(f"start '{start}' không trỏ tới node nào.")
    for node_id, node in nodes.items():
        if not isinstance(node, dict) or node.get("type") not in node_types:
            kind = node.get("type") if isinstance(node, dict) else node
            errors.append(f"Node '{node_id}' có type không hợp lệ: {kind}")
    edges = flow.get("edges", [])
    if not isinstance(edges, list):
        return errors + ["edges phải là danh sách."]
    for edge in edges:
        if not isinstance(edge, dict) or edge.get("from") not in nodes or edge.get("to") not in nodes:
            errors.append(f"Dây nối trỏ tới node không tồn tại: {edge}")
            continue
        condition = edge.get("condition")
        if condition and condition.get("op") not in OPS:
            errors.append(f"Dây {edge['from']} → {edge['to']} có toán tử không hợp lệ: {condition.get('op')}")
        if "maxLoop" in edge and (not isinstance(edge["maxLoop"], int) or edge["maxLoop"] < 1):
            errors.append(f"maxLoop của dây {edge['from']} → {edge['to']} phải là số nguyên ≥ 1.")
    if not errors:
        reachable, stack = set(), [start]
        while stack:
            current = stack.pop()
            if current in reachable:
                continue
            reachable.add(current)
            stack += [e["to"] for e in edges if e["from"] == current]
        for node_id in nodes:
            if node_id not in reachable:
                errors.append(f"Node '{node_id}' không thể tới được từ start.")
    return errors


def run_flow(
    flow: dict,
    state: dict,
    nodes: dict[str, Callable],
    ctx: object | None = None,
    on_step: OnStep | None = None,
) -> dict:
    """Chạy flow; node trả dict ghi đè state[id] (khóa '_global' được gộp vào state gốc)."""
    notify = on_step or (lambda *_: None)
    errors = validate_flow(flow, set(nodes))
    if errors:
        raise FlowError("Flow không hợp lệ: " + "; ".join(errors))
    edges = flow.get("edges", [])
    counts: dict[int, int] = {}
    current: str | None = flow["start"]
    while current is not None:
        node = flow["nodes"][current]
        notify(current, "start", node.get("label") or current)
        try:
            output = nodes[node["type"]](state, node.get("config") or {}, ctx) or {}
        except Exception as error:
            state[f"{current}.error"] = str(error)
            notify(current, "error", str(error))
            raise FlowError(f"Lỗi tại node '{current}': {error}", current) from error
        output = dict(output)
        state.update(output.pop("_global", {}))
        state[current] = output
        state.setdefault("_types", {})[node["type"]] = output  # node sau tìm đầu vào theo loại card, không theo id
        notify(current, "done", "")
        chosen = None
        for index, edge in enumerate(edges):
            if edge["from"] == current and evaluate(edge.get("condition"), state):
                chosen = (index, edge)
                break
        if chosen is None:
            return state
        index, edge = chosen
        counts[index] = counts.get(index, 0) + 1
        limit = edge.get("maxLoop", DEFAULT_MAX_LOOP)
        if counts[index] > limit:
            message = f"Flow lặp quá {limit} lần tại dây {edge['from']} → {edge['to']}"
            if output.get("error"):
                message = f"Đã thử lại {limit} lần vẫn lỗi (lặp quá {limit} lần): {output['error']}"
            notify(current, "error", message)
            raise FlowError(message, current)
        current = edge["to"]
    return state
