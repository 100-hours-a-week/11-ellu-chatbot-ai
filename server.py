# app/main.py
import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.chat_router import router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="일정 생성 챗봇 API",
    description="챗봇 대화 및 일정 생성 엔드포인트",
    version="1.0"
)

# 전역 예외 핸들러 함수
# 404 기본 에러 예외 처리
@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    logger.error(f"HTTP error: {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": "error", "detail": exc.detail}
    )

# 400에러 예외 처리
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.error(f"Validation error: {exc.errors()}")
    return JSONResponse(
        status_code=400,
        content={"message": "validation_error", "errors": exc.errors()}
    )

# 500에러 예외 처리
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled server error")
    return JSONResponse(
        status_code=500,
        content={"message": "internal_server_error", "detail": "서버 내부 오류가 발생했습니다."}
    )

# 라우터 등록
app.include_router(router, prefix="/ai", tags=["chats"])

# 루트 엔드포인트
@app.get("/")
async def root():
    return {"message": "Welcome to the Looper AI Scheduling Chatbot API!"}
