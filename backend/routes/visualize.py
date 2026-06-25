from fastapi import APIRouter, HTTPException
from backend.models.schemas import VisualizeRequest
from backend.services.viz_service import generate_chart

router = APIRouter(prefix="/api", tags=["visualize"])


@router.post("/visualize")
async def visualize(request: VisualizeRequest):
    try:
        result = await generate_chart(request.query)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"可视化生成失败: {e}")
