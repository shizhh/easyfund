"""Excel import router — AI-driven two-phase import."""

from fastapi import APIRouter, Depends, HTTPException, UploadFile

from backend.auth import get_db
from backend.schemas import ImportConfirmRequest
from backend.services.import_service import analyze_excel, import_excel_with_mapping

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/analyze")
async def analyze_excel_file(file: UploadFile, data_dir: str = Depends(get_db)):
    """Upload Excel and get AI analysis of structure and mapping suggestions."""
    content = await file.read()
    try:
        session_id, mapping = await analyze_excel(content)
    except ValueError as e:
        raise HTTPException(400, str(e))
    return {"session_id": session_id, "mapping": mapping.model_dump()}


@router.post("/confirm")
async def confirm_import(req: ImportConfirmRequest, data_dir: str = Depends(get_db)):
    """Confirm mapping and execute import."""
    try:
        result = await import_excel_with_mapping(req.session_id, req.mapping)
    except FileNotFoundError as e:
        raise HTTPException(404, str(e))
    except ValueError as e:
        raise HTTPException(400, str(e))
    from backend.routers.dashboard import invalidate_dashboard_cache
    invalidate_dashboard_cache()
    return result
