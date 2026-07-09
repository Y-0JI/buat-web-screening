from fastapi import APIRouter, UploadFile, File
from app.schemas.stock import VisionAnalysisResponse, VisionReport, RenderType
from app.ai.vision import analyze_chart_image

router = APIRouter(prefix="/api", tags=["vision"])

ALLOWED_TYPES = {"image/png", "image/jpeg", "image/jpg"}
MAX_SIZE = 10 * 1024 * 1024


@router.post("/vision-analysis", response_model=VisionAnalysisResponse)
async def vision_analysis(file: UploadFile = File(...)):
    if file.content_type not in ALLOWED_TYPES:
        return VisionAnalysisResponse(
            success=False,
            error=f"Format tidak didukung: {file.content_type}. Gunakan PNG atau JPG.",
        )

    contents = await file.read()
    if len(contents) > MAX_SIZE:
        return VisionAnalysisResponse(
            success=False, error="Ukuran file maksimal 10 MB."
        )

    result = await analyze_chart_image(contents, file.filename or "chart.png")

    report = VisionReport(
        file_name=result.get("file_name", file.filename or "chart.png"),
        analysis_text=result.get("analysis_text", ""),
        patterns_detected=result.get("patterns_detected", []),
        trend=result.get("trend"),
        support_level=result.get("support_level"),
        resistance_level=result.get("resistance_level"),
    )

    return VisionAnalysisResponse(success=True, data=report)
