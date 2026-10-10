import json
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    SimStepRequest,
    SimContinueRequest,
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


@router.post("/continue", response_model=StepTickResponse)
async def sim_continue(req: SimContinueRequest, db: Session = Depends(get_db)):
    """智能续写：由 AI 自主判断时间切速与情节推进"""
    try:
        res = await SimulationService.run_continue(
            db, req.character_id, config=req.config
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
    """触发突发事件：支持用户指定事件或由 AI 结合题材自主衍生"""
    try:
        res = await SimulationService.trigger_inciting_incident(
            db, req.character_id, incident_description=req.incident_description, config=req.config
        )
        return res
    except Exception as e:
        raise map_sim_exception_to_http(e)


@router.post("/step-stream")
async def sim_step_stream(req: SimStepRequest, db: Session = Depends(get_db)):
    """纯按钮微步进实时流式输出 (SSE)"""
    async def event_generator():
        try:
            async for evt in SimulationService.run_step_stream(
                db, req.character_id, hours=req.hours, config=req.config
            ):
                yield f"event: {evt['event']}\ndata: {json.dumps(evt['data'], default=str, ensure_ascii=False)}\n\n"
        except Exception as e:
            err_dict = {
                "error_code": getattr(e, "error_code", "SIM_STREAM_ERROR"),
                "message": getattr(e, "message", str(e)),
            }
            yield f"event: error\ndata: {json.dumps(err_dict, default=str, ensure_ascii=False)}\n\n"

    sse_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=sse_headers)


@router.post("/continue-stream")
async def sim_continue_stream(req: SimContinueRequest, db: Session = Depends(get_db)):
    """智能续写实时流式输出 (SSE)"""
    async def event_generator():
        try:
            async for evt in SimulationService.continue_stream(
                db, req.character_id, config=req.config
            ):
                yield f"event: {evt['event']}\ndata: {json.dumps(evt['data'], default=str, ensure_ascii=False)}\n\n"
        except Exception as e:
            err_dict = {
                "error_code": getattr(e, "error_code", "SIM_STREAM_ERROR"),
                "message": getattr(e, "message", str(e)),
            }
            yield f"event: error\ndata: {json.dumps(err_dict, default=str, ensure_ascii=False)}\n\n"

    sse_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=sse_headers)


@router.post("/fast-forward-stream")
async def sim_fast_forward_stream(req: SimFastForwardRequest, db: Session = Depends(get_db)):
    """阶段快进实时流式输出 (SSE)"""
    async def event_generator():
        try:
            async for evt in SimulationService.fast_forward_stream(
                db, req.character_id, step_type=req.step_type, config=req.config
            ):
                yield f"event: {evt['event']}\ndata: {json.dumps(evt['data'], default=str, ensure_ascii=False)}\n\n"
        except Exception as e:
            err_dict = {
                "error_code": getattr(e, "error_code", "SIM_STREAM_ERROR"),
                "message": getattr(e, "message", str(e)),
            }
            yield f"event: error\ndata: {json.dumps(err_dict, default=str, ensure_ascii=False)}\n\n"

    sse_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=sse_headers)


@router.post("/trigger-incident-stream")
async def sim_trigger_incident_stream(req: SimTriggerIncidentRequest, db: Session = Depends(get_db)):
    """突发事件实时流式输出 (SSE)"""
    async def event_generator():
        try:
            async for evt in SimulationService.trigger_incident_stream(
                db, req.character_id, incident_description=req.incident_description, config=req.config
            ):
                yield f"event: {evt['event']}\ndata: {json.dumps(evt['data'], default=str, ensure_ascii=False)}\n\n"
        except Exception as e:
            err_dict = {
                "error_code": getattr(e, "error_code", "SIM_STREAM_ERROR"),
                "message": getattr(e, "message", str(e)),
            }
            yield f"event: error\ndata: {json.dumps(err_dict, default=str, ensure_ascii=False)}\n\n"

    sse_headers = {
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "X-Accel-Buffering": "no",
    }
    return StreamingResponse(event_generator(), media_type="text/event-stream", headers=sse_headers)
