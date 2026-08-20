"""Auditor 审计官（确定性官员）：证据落链 + RunStore 落盘。只记录不决策。"""
from __future__ import annotations

from ..core.transaction import ChangeTransaction
from ..log.training_log import EpochEntry
from ..store.run_store import RunStore


class Auditor:
    def __init__(self, run_store: RunStore):
        self.store = run_store
        self.committed_transactions: list[dict] = []
        self.rollbacks: list[dict] = []

    def record_transaction(self, tx: ChangeTransaction, rolled_back: bool, reason: str = "") -> None:
        record = {
            "status": tx.status,
            "changes": [{"layer": c.layer, "action": c.action,
                         "element": getattr(c.element, "id", str(c.element)), "reason": c.reason,
                         "origin": getattr(c, "origin", "task"),
                         "semantic": getattr(c, "semantic", ""),
                         "reg_evidence": getattr(c, "reg_evidence", None),
                         "reg_conflict": getattr(c, "reg_conflict", None)}
                        for c in tx.changes],
            "version": tx.solution.version,
            "rolled_back": rolled_back,
            "reason": reason,
        }
        (self.rollbacks if rolled_back else self.committed_transactions).append(record)

    def persist_epoch(self, epoch: int, log_record: dict,
                      loss_traces: list, messages: list) -> None:
        """步骤⑨：训练日志落链 + 全量证据落盘。"""
        self.store.save_epoch(epoch, log_record, loss_traces)
        self.store.save_messages(epoch, messages)

    def persist_summary(self, summary: dict) -> None:
        summary["transactions_committed"] = self.committed_transactions
        summary["transactions_rolled_back"] = self.rollbacks
        self.store.save_summary(summary)
