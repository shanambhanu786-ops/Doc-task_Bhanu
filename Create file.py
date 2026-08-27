import asyncio
from typing import Dict, Any
from telemetry import trace_stage
from database import save_job_state

class AnalystAgentWorkflow:
    def __init__(self, job_id: str):
        self.job_id = job_id

    @trace_stage("stage_1_ingest_and_parse")
    async def ingest_documents(self, state: Dict[str, Any]) -> Dict[str, Any]:
        state["stage"] = "INGESTED"
        state["extracted_facts"] = [
            {"id": "claim_1", "text": "Vendor delivery deadline is 30 Days.", "source": "contract_v1.pdf:p2"},
            {"id": "claim_2", "text": "Vendor delivery deadline is 45 Days.", "source": "amendment_1.pdf:p1"}
        ]
        save_job_state(self.job_id, "INGESTED", state)
        return state

    @trace_stage("stage_2_conflict_detection")
    async def detect_conflicts(self, state: Dict[str, Any]) -> Dict[str, Any]:
        state["stage"] = "CONFLICTS_DETECTED"
        state["conflicts"] = [
            {
                "conflict_id": "cnf_101",
                "description": "Delivery timeline discrepancy between contract (30 days) and amendment (45 days).",
                "sources": ["contract_v1.pdf:p2", "amendment_1.pdf:p1"]
            }
        ]
        save_job_state(self.job_id, "WAITING_FOR_HUMAN_GATE", state)
        return state

    @trace_stage("stage_3_human_gate_apply")
    async def apply_human_decisions(self, state: Dict[str, Any], decisions: Dict[str, str]) -> Dict[str, Any]:
        # Item-by-item human review application
        approved_findings = []
        for conflict in state.get("conflicts", []):
            decision = decisions.get(conflict["conflict_id"], "REJECTED")
            if decision == "APPROVED":
                approved_findings.append(conflict)
        
        state["approved_findings"] = approved_findings
        state["stage"] = "FINALIZED"
        save_job_state(self.job_id, "FINALIZED", state)
        return state
