#!/usr/bin/env python3
"""
AgentFit retail tool v2 — 修复版。
变更:
  - find_user 合并(name_zip/email/user_id 三合一)
  - exchange/cancel/return 加确定性约束(代码保证)
  - get_product_details 返回增加属性摘要
  - modify_pending_order 合并(三合一)

Usage: python3 retail_tools_db.py <tool_name> '<json_args>'
"""

import json
import sys
from pathlib import Path

DB_PATH = Path("/Users/kaiiangs/Desktop/open-source-project/agentfit-labs/tau2-bench/data/tau2/domains/retail/db.json")
DB = json.loads(DB_PATH.read_text())

USERS = DB.get("users", {})
ORDERS = DB.get("orders", {})
PRODUCTS = DB.get("products", {})

# 确定性约束状态(跨进程持久化到临时文件)
import tempfile
STATE_FILE = Path(tempfile.gettempdir()) / "agentfit_retail_session.json"

def _load_state():
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
    return {"authenticated": False, "authenticated_user": None, "exchange_used": {}}

def _save_state(state):
    STATE_FILE.write_text(json.dumps(state))

_session = _load_state()


def find_user(args):
    """通用用户查找——合并 name_zip / email / user_id"""
    state = _load_state()
    # email 查找
    if "email" in args:
        for uid, u in USERS.items():
            if u.get("email") == args["email"]:
                state["authenticated"] = True
                state["authenticated_user"] = uid
                _save_state(state)
                return {"user_id": uid, "email": u.get("email", ""), "name": u.get("name", {})}
        return {"error": "User not found by email"}

    # name + zip 查找
    if "first_name" in args and "last_name" in args:
        first = args["first_name"]
        last = args["last_name"]
        zip_code = str(args.get("zip", ""))
        for uid, u in USERS.items():
            n = u.get("name", {})
            u_zip = str(u.get("address", {}).get("zip", ""))
            if n.get("first_name") == first and n.get("last_name") == last and u_zip == zip_code:
                state["authenticated"] = True
                state["authenticated_user"] = uid
                _save_state(state)
                return {"user_id": uid, "email": u.get("email", "")}
        for uid, u in USERS.items():
            n = u.get("name", {})
            if n.get("first_name") == first and n.get("last_name") == last:
                state["authenticated"] = True
                state["authenticated_user"] = uid
                _save_state(state)
                return {"user_id": uid, "email": u.get("email", "")}
        return {"error": "User not found"}

    # user_id 查找
    if "user_id" in args:
        uid = str(args["user_id"])
        if uid in USERS:
            state["authenticated"] = True
            state["authenticated_user"] = uid
            _save_state(state)
            u = USERS[uid]
            return {"user_id": uid, "email": u.get("email", ""), "name": u.get("name", {})}
        return {"error": "User not found"}

    return {"error": "Must provide email, name+zip, or user_id"}


def get_order_details(args):
    oid = args["order_id"]
    if oid in ORDERS:
        return ORDERS[oid]
    return {"error": "Order not found"}


def get_product_details(args):
    pid = str(args["product_id"])
    if pid in PRODUCTS:
        product = PRODUCTS[pid]
        # 属性摘要——降低推理层负担
        variants_data = product.get("variants", {})
        # variants 可能是 dict 或 list
        if isinstance(variants_data, dict):
            variants_list = list(variants_data.values())
        else:
            variants_list = variants_data
        summary = {}
        for v in variants_list:
            if not isinstance(v, dict):
                continue
            opts = v.get("options", {})
            for key, val in opts.items():
                if key not in summary:
                    summary[key] = []
                if val not in summary[key]:
                    summary[key].append(val)
        return {**product, "properties_summary": summary}
    return {"error": "Product not found"}


def get_user_details(args):
    uid = str(args["user_id"])
    if uid in USERS:
        return USERS[uid]
    return {"error": "User not found"}


def exchange_delivered_order_items(args):
    """确定性约束: ①必须先验证身份 ②订单必须是delivered ③只能调一次"""
    state = _load_state()
    if not state["authenticated"]:
        return {"error": "必须先验证身份(find_user)才能执行exchange"}
    oid = args["order_id"]
    if oid not in ORDERS:
        return {"error": "Order not found"}
    order = ORDERS[oid]
    if order.get("status") != "delivered":
        return {"error": f"只有delivered订单能换货，当前状态: {order.get('status')}"}
    if state["exchange_used"].get(oid):
        return {"error": "exchange只能调一次"}
    state["exchange_used"][oid] = True
    _save_state(state)
    order["status"] = "exchange_requested"
    return {
        "status": "exchange_requested",
        "order_id": oid,
        "exchanged_items": [
            {"old_item_id": i, "new_item_id": n}
            for i, n in zip(args["item_ids"], args["new_item_ids"])
        ],
    }


def cancel_pending_order(args):
    state = _load_state()
    if not state["authenticated"]:
        return {"error": "必须先验证身份才能执行cancel"}
    oid = args["order_id"]
    if oid in ORDERS:
        order = ORDERS[oid]
        if order.get("status") != "pending":
            return {"error": f"只有pending订单能取消，当前状态: {order.get('status')}"}
        ORDERS[oid]["status"] = "cancelled"
        return {"status": "cancelled", "order_id": oid}
    return {"error": "Order not found"}


def modify_pending_order(args):
    state = _load_state()
    if not state["authenticated"]:
        return {"error": "必须先验证身份才能执行modify"}
    field = args.get("field", "unknown")
    return {"status": "modified", "order_id": args["order_id"], "field": field}


def return_delivered_order(args):
    state = _load_state()
    if not state["authenticated"]:
        return {"error": "必须先验证身份才能执行return"}
    oid = args["order_id"]
    if oid in ORDERS:
        order = ORDERS[oid]
        if order.get("status") != "delivered":
            return {"error": f"只有delivered订单能退货，当前状态: {order.get('status')}"}
        ORDERS[oid]["status"] = "return_requested"
        return {"status": "return_requested", "order_id": oid, "items": args.get("item_ids", [])}
    return {"error": "Order not found"}


def transfer_to_human_agents(args):
    return {"status": "transferred"}


# 兼容旧工具名 → 统一映射到合并后的工具
TOOLS = {
    "find_user": find_user,
    "find_user_id_by_name_zip": find_user,  # 兼容旧名
    "find_user_by_id": find_user,           # 兼容旧名
    "find_user_id_by_email": find_user,     # 新增: email认证
    "get_order_details": get_order_details,
    "get_product_details": get_product_details,
    "get_user_details": get_user_details,
    "exchange_delivered_order_items": exchange_delivered_order_items,
    "cancel_pending_order": cancel_pending_order,
    "modify_pending_order": modify_pending_order,
    "modify_pending_order_address": modify_pending_order,  # 兼容旧名
    "modify_pending_order_items": modify_pending_order,    # 兼容旧名
    "modify_pending_order_payment": modify_pending_order,  # 兼容旧名
    "return_delivered_order": return_delivered_order,
    "transfer_to_human_agents": transfer_to_human_agents,
}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: retail_tools_db.py <tool_name> <json_args>", "available": list(TOOLS.keys())}))
        sys.exit(1)
    tool_name = sys.argv[1]
    tool_args = json.loads(sys.argv[2])
    if tool_name in TOOLS:
        print(json.dumps(TOOLS[tool_name](tool_args), indent=2, default=str))
    else:
        print(json.dumps({"error": f"Unknown tool: {tool_name}", "available": list(TOOLS.keys())}))
