from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    SimStepRequest,
    SimFastForwardRequest,
    SimTriggerIncidentRequest,
    StepTickResponse,
)
from app.services.simulation import SimulationService
from app.services.prompt_library import (
    STYLE_PRESETS,
    WRITING_PATCHES,
    WORD_COUNT_TIERS,
)

router = APIRouter(prefix="/api/v1/sim", tags=["Simulation Control"])


@router.get("/prompt-meta")
def get_prompt_metadata():
    """获取文风框架、技法补丁与字数档位元数据"""
    return {
        "style_presets": STYLE_PRESETS,
        "writing_patches": WRITING_PATCHES,
        "word_count_tiers": WORD_COUNT_TIERS,
    }


from app.services.llm_client import LLMClientError
from app.services.arbitrator import ArbitrationError
from app.services.storyteller import StorytellerError


def map_sim_exception_to_http(e: Exception) -> HTTPException:
    if isinstance(e, LLMClientError):
        status = e.status_code if e.status_code in (400, 401, 403, 404, 429, 502, 504) else 502
        return HTTPException(status_code=status, detail={"error_code": e.error_code, "message": e.message})
    elif isinstance(e, ArbitrationError):
        return HTTPException(status_code=502, detail={"error_code": e.error_code, "message": e.message})
    elif isinstance(e, StorytellerError):
        return HTTPException(status_code=502, detail={"error_code": e.error_code, "message": e.message})
    return HTTPException(status_code=500, detail={"error_code": "SIM_INTERNAL_ERROR", "message": str(e)})


@router.post("/step", response_model=StepTickResponse)
async def sim_step(req: SimStepRequest, db: Session = Depends(get_db)):
    """纯按钮微步进 (+1h)"""
    try:
        res = await SimulationService.run_step(
            db, req.character_id, hours=req.hours, config=req.config
        )
        return res
    except Exception as e:
        raise map_sim_exception_to_http(e)


@router.post("/fast-forward", response_model=StepTickResponse)
async def sim_fast_forward(req: SimFastForwardRequest, db: Session = Depends(get_db)):
    """纯按钮阶段快进 (+6h 或 +24h 跨日跃迁)"""
    try:
        res = await SimulationService.fast_forward(
            db, req.character_id, step_type=req.step_type, config=req.config
        )
        return res
    except Exception as e:
        raise map_sim_exception_to_http(e)


@router.post("/trigger-incident", response_model=StepTickResponse)
async def sim_trigger_incident(req: SimTriggerIncidentRequest, db: Session = Depends(get_db)):
    """纯按钮触发突发事件：用户无需也不可输入文本，AI 自主构思危机并注入推演"""
    try:
        res = await SimulationService.trigger_inciting_incident(
            db, req.character_id, config=req.config
        )
        return res
    except Exception as e:
        raise map_sim_exception_to_http(e)
