from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel
from typing import Dict
from telemetry import setup_datadog
from database import init_db, save_job_state, load_job_state
from graph import AnalystAgentWorkflow

setup_datadog()
init_db()

app = FastAPI(title="SuperDocs Agentic Analyst API")

class StartJobRequest(BaseModel):
    job_id: str
    documents: list[str]

class HumanGateDecisionRequest(BaseModel):
    decisions: Dict[str, str]  # e.g. {"cnf_101": "APPROVED"}

@app.post("/jobs/start")
async def start_job(payload: StartJobRequest):
    wf = AnalystAgentWorkflow(payload.job_id)
    initial_state = {"documents": payload.documents}
    
    # Execute stages 1 and 2
    state = await wf.ingest_documents(initial_state)
    state = await wf.detect_conflicts(state)
    
    return {"status": "PAUSED_AT_HUMAN_GATE", "job_id": payload.job_id, "pending_review": state["conflicts"]}

@app.get("/jobs/{job_id}/state")
async def get_state(job_id: str):
    state = load_job_state(job_id)
    if not state:
        raise HTTPException(status_code=404, detail="Job not found")
    return state

@app.post("/jobs/{job_id}/gate")
async def submit_gate_decisions(job_id: str, payload: HumanGateDecisionRequest):
    current = load_job_state(job_id)
    if not current:
        raise HTTPException(status_code=404, detail="Job not found")
    
    wf = AnalystAgentWorkflow(job_id)
    final_state = await wf.apply_human_decisions(current["state_data"], payload.decisions)
    return {"status": "COMPLETED", "job_id": job_id, "final_deliverable": final_state}
