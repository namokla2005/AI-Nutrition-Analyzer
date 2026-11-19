"""AI Nutrition Analyzer - FastAPI application factory.

Giai đoạn hiện tại: khung ứng dụng + health check (các router được bổ sung ở Giai đoạn 3).
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import BASE_DIR, settings
from app.api.v1 import api_router
from app.pages import router as pages_router

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings.ensure_dirs()
    logger.info("Khởi động %s v%s", settings.app_name, settings.app_version)
    logger.info("Static: %s", BASE_DIR / "app" / "static")
    yield
    logger.info("Đã dừng ứng dụng.")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version=settings.app_version,
        description="Hệ thống nhận diện thực phẩm, dự đoán calo và phân tích dinh dưỡng bằng Machine Learning.",
        lifespan=lifespan,
    )

    static_dir = BASE_DIR / "app" / "static"
    static_dir.mkdir(parents=True, exist_ok=True)
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(api_router)
    app.include_router(pages_router)

    @app.exception_handler(Exception)
    async def unhandled_error(request: Request, exc: Exception) -> JSONResponse:  # pragma: no cover
        logger.exception("Lỗi không xử lý được tại %s", request.url.path)
        return JSONResponse(
            status_code=500,
            content={"detail": "Lỗi hệ thống. Vui lòng thử lại sau."},
        )

    @app.get("/favicon.ico", include_in_schema=False)
    async def favicon() -> Response:
        """Biểu tượng trang: cùng hình với thẻ <link rel="icon"> trong base.html.

        Trả về tệp thật để trình duyệt không nhận 404 (trước đây chỉ có data-URI trong HTML).
        """
        svg = (
            "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
            "<rect width='32' height='32' rx='8' fill='#16a34a'/>"
            "<text x='16' y='23' font-family='sans-serif' font-size='18' font-weight='bold' "
            "text-anchor='middle' fill='#fff'>A</text></svg>"
        )
        return Response(content=svg, media_type="image/svg+xml")

    @app.get("/status", include_in_schema=False, response_class=HTMLResponse, summary="Trang trạng thái")
    async def root() -> HTMLResponse:
        """Trang chủ tạm: cho biết hệ thống đang chạy và phần nào đã sẵn sàng.

        Giao diện chính thức (9 trang tiếng Việt) thuộc Giai đoạn 4.
        """
        from sqlalchemy import func, select

        from app.core.database import engine
        from app.models import Food, FoodSource, Meal, User

        db_ok = False
        counts = {"foods": 0, "food_sources": 0, "users": 0, "meals": 0}
        db_error = None
        try:
            with engine.connect() as conn:
                db_ok = True
            from app.core.database import SessionLocal

            with SessionLocal() as db:
                counts["foods"] = db.scalar(select(func.count()).select_from(Food)) or 0
                counts["food_sources"] = db.scalar(select(func.count()).select_from(FoodSource)) or 0
                counts["users"] = db.scalar(select(func.count()).select_from(User)) or 0
                counts["meals"] = db.scalar(select(func.count()).select_from(Meal)) or 0
        except Exception as exc:
            db_error = type(exc).__name__

        ollama_ok = False
        try:
            import httpx

            r = httpx.get(f"{settings.ollama_base_url}/api/tags", timeout=2.0)
            ollama_ok = r.status_code == 200
        except Exception:
            ollama_ok = False

        def badge(ok: bool, yes: str = "hoạt động", no: str = "chưa sẵn sàng") -> str:
            cls = "ok" if ok else "off"
            return f'<span class="badge {cls}">{yes if ok else no}</span>'

        html = f"""<!doctype html>
<html lang="vi"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'><rect width='32' height='32' rx='8' fill='%2316a34a'/><text x='16' y='23' font-family='sans-serif' font-size='18' font-weight='bold' text-anchor='middle' fill='%23fff'>A</text></svg>">
<title>{settings.app_name}</title>
<style>
  :root {{ color-scheme: light dark; }}
  body {{ font-family: system-ui, "Segoe UI", sans-serif; max-width: 780px; margin: 40px auto;
         padding: 0 20px; line-height: 1.6; }}
  h1 {{ font-size: 1.5rem; margin-bottom: .2rem; }}
  .sub {{ color: #666; margin-top: 0; }}
  table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
  th, td {{ text-align: left; padding: .5rem .6rem; border-bottom: 1px solid #8883; }}
  .badge {{ padding: .15rem .55rem; border-radius: 999px; font-size: .82rem; }}
  .ok {{ background: #1a7f3733; color: #15803d; }}
  .off {{ background: #b91c1c33; color: #b91c1c; }}
  code {{ background: #8882; padding: .1rem .35rem; border-radius: 4px; }}
  ul.links {{ padding-left: 1.1rem; }}
</style></head><body>
<h1>{settings.app_name}</h1>
<p class="sub">Phiên bản {settings.app_version} — máy chủ đang chạy tại <code>http://{settings.host}:{settings.port}</code></p>

<table>
  <tr><th>Thành phần</th><th>Trạng thái</th><th>Ghi chú</th></tr>
  <tr><td>Máy chủ FastAPI</td><td>{badge(True)}</td><td>Đang phục vụ yêu cầu</td></tr>
  <tr><td>Database SQLite</td><td>{badge(db_ok)}</td><td>{counts['foods']} thực phẩm · {counts['food_sources']} nguồn dữ liệu · {counts['users']} tài khoản · {counts['meals']} bữa ăn{' · lỗi: ' + db_error if db_error else ''}</td></tr>
  <tr><td>Trợ lý AI (Ollama)</td><td>{badge(ollama_ok, 'kết nối được', 'không kết nối được')}</td><td>{settings.ollama_model} tại {settings.ollama_base_url}</td></tr>
</table>

<p><b>Các chức năng đã có API:</b></p>
<ul class="links">
  <li><a href="/docs">Tài liệu API (Swagger)</a> — 14 endpoint</li>
  <li><a href="/api/v1/health">/api/v1/health</a> — kiểm tra trạng thái</li>
  <li><a href="/api/v1/foods">/api/v1/foods</a> — tra cứu thực phẩm</li>
</ul>
<p><b>Đang xây dựng:</b> nhận diện ảnh, nhật ký ăn uống, thống kê, trợ lý AI và 9 trang giao diện tiếng Việt.</p>
</body></html>"""
        return HTMLResponse(content=html)

    @app.get("/api/v1/health", tags=["system"], summary="Trạng thái hệ thống")
    async def health() -> dict:
        from sqlalchemy import text

        from app.core.database import db_path_from_url, engine

        db_ok = False
        db_info: dict = {"url_ok": bool(engine.url), "file": str(db_path_from_url())}
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_ok = True
        except Exception as exc:
            db_info["error"] = type(exc).__name__

        return {
            "app": settings.app_name,
            "version": settings.app_version,
            "database": {"ok": db_ok, **db_info},
            "ollama": {
                "base_url": settings.ollama_base_url,
                "model": settings.ollama_model,
                "checked": False,
            },
        }

    return app


app = create_app()
