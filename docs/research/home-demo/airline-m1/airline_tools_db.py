#!/usr/bin/env python3
"""
AgentFit airline tool — reads τ³-bench airline db.json directly.
按三维能力体系构建: 执行层工具 + 确定性约束(代码层)

Usage: python3 airline_tools_db.py <tool_name> '<json_args>'
"""

import json
import sys
import tempfile
from pathlib import Path

DB_PATH = Path("/Users/kaiiangs/Desktop/open-source-project/agentfit-labs/tau2-bench/data/tau2/domains/airline/db.json")
DB = json.loads(DB_PATH.read_text())

# airline db.json 结构探索
if isinstance(DB, dict):
    USERS = DB.get("users", {})
    RESERVATIONS = DB.get("reservations", {})
else:
    USERS = {}
    RESERVATIONS = {}

# 确定性约束状态(跨进程持久化)
STATE_FILE = Path(tempfile.gettempdir()) / "agentfit_airline_session.json"

def _load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"authenticated": False, "authenticated_user": None}

def _save_state(state):
    STATE_FILE.write_text(json.dumps(state))


def find_user(args):
    """通用用户查找"""
    state = _load_state()
    if "user_id" in args:
        uid = str(args["user_id"])
        if uid in USERS:
            state["authenticated"] = True
            state["authenticated_user"] = uid
            _save_state(state)
            return {"user_id": uid, "name": USERS[uid].get("name", "")}
    if "first_name" in args:
        for uid, u in USERS.items():
            n = u.get("name", "")
            if args["first_name"] in n and args.get("last_name", "") in n:
                state["authenticated"] = True
                state["authenticated_user"] = uid
                _save_state(state)
                return {"user_id": uid, "name": n}
    return {"error": "User not found"}


def get_user_details(args):
    uid = str(args.get("user_id", _load_state().get("authenticated_user", "")))
    if uid in USERS:
        return USERS[uid]
    return {"error": "User not found"}


def get_reservation_details(args):
    rid = args["reservation_id"]
    if rid in RESERVATIONS:
        return RESERVATIONS[rid]
    return {"error": "Reservation not found"}


def search_direct_flight(args):
    """搜索直飞航班"""
    origin = args.get("origin", "")
    destination = args.get("destination", "")
    # 从 db 里找航班 (airline db 可能有 flights 结构)
    return {"query": f"{origin} -> {destination}", "note": "搜索航班"}


def book_reservation(args):
    """预订"""
    state = _load_state()
    if not state["authenticated"]:
        return {"error": "必须先验证身份才能预订"}
    return {"status": "booked", "reservation_id": "NEW", "details": args}


def cancel_reservation(args):
    """取消预订——确定性约束: 必须验证身份"""
    state = _load_state()
    if not state["authenticated"]:
        return {"error": "必须先验证身份才能取消"}
    rid = args.get("reservation_id", "")
    if rid in RESERVATIONS:
        RESERVATIONS[rid]["status"] = "cancelled"
        return {"status": "cancelled", "reservation_id": rid}
    return {"error": "Reservation not found"}


def update_reservation_flights(args):
    state = _load_state()
    if not state["authenticated"]:
        return {"error": "必须先验证身份才能修改"}
    return {"status": "updated", "field": "flights", "reservation_id": args.get("reservation_id", "")}


def update_reservation_baggages(args):
    state = _load_state()
    if not state["authenticated"]:
        return {"error": "必须先验证身份才能修改"}
    return {"status": "updated", "field": "baggages", "reservation_id": args.get("reservation_id", "")}


def update_reservation_passengers(args):
    state = _load_state()
    if not state["authenticated"]:
        return {"error": "必须先验证身份才能修改"}
    return {"status": "updated", "field": "passengers", "reservation_id": args.get("reservation_id", "")}


def calculate(args):
    """计算器工具"""
    expr = args.get("expression", "")
    return {"expression": expr, "note": "计算器"}


def transfer_to_human_agents(args):
    return {"status": "transferred"}


TOOLS = {
    "find_user": find_user,
    "get_user_details": get_user_details,
    "get_reservation_details": get_reservation_details,
    "search_direct_flight": search_direct_flight,
    "book_reservation": book_reservation,
    "cancel_reservation": cancel_reservation,
    "update_reservation_flights": update_reservation_flights,
    "update_reservation_baggages": update_reservation_baggages,
    "update_reservation_passengers": update_reservation_passengers,
    "calculate": calculate,
    "transfer_to_human_agents": transfer_to_human_agents,
}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: airline_tools_db.py <tool_name> <json_args>", "available": list(TOOLS.keys())}))
        sys.exit(1)
    tool_name = sys.argv[1]
    tool_args = json.loads(sys.argv[2])
    if tool_name in TOOLS:
        print(json.dumps(TOOLS[tool_name](tool_args), indent=2, default=str))
    else:
        print(json.dumps({"error": f"Unknown tool: {tool_name}", "available": list(TOOLS.keys())}))
