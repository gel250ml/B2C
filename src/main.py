from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.database.init_db import init_db
from src.routes.address_router import router as address_router
from src.routes.auth_router import router as auth_router
from src.routes.b2b_event_router import router as b2b_event_router
from src.routes.buyer_router import router as buyer_router
from src.routes.cart_router import router as cart_router
from src.routes.catalog_router import router as catalog_router
from src.routes.category_navigation_router import router as category_navigation_router
from src.routes.favorite_router import router as favorite_router
from src.routes.home_router import router as home_router
from src.routes.notification_router import router as notification_router
from src.routes.order_router import router as order_router
from src.routes.payment_method_router import router as payment_method_router
from src.routes.product_subscription_router import router as product_subscription_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


tags_metadata = [
    {
        "name": "Auth",
        "description": "Регистрация и аутентификация покупателей",
    },
    {
        "name": "Buyer",
        "description": "Профиль покупателя",
    },
    {
        "name": "Addresses",
        "description": "Адреса доставки",
    },
    {
        "name": "PaymentMethods",
        "description": "Платёжные методы (моки)",
    },
    {
        "name": "Catalog",
        "description": "Каталог товаров (проксируется из B2B)",
    },
    {
        "name": "Cart",
        "description": "Корзина (гость + авторизованный)",
    },
    {
        "name": "Home",
        "description": "Главная страница: баннеры и CTR-события",
    },
    {
        "name": "Favorites",
        "description": "Избранное и подписки на товары",
    },
    {
        "name": "Orders",
        "description": "Заказы покупателя",
    },
    {
        "name": "Notifications",
        "description": "Уведомления и подписки",
    },
    {
        "name": "B2B Events",
        "description": "Приём событий от B2B-сервиса (служебный канал)",
    },
]

app = FastAPI(
    lifespan=lifespan,
    openapi_tags=tags_metadata,
)


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    if isinstance(exc.detail, dict) and "message" in exc.detail and ("code" in exc.detail or "error" in exc.detail):
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.detail,
        )
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=400,
        content={
            "code": "INVALID_REQUEST",
            "message": exc.errors()[0].get("msg", "Validation error"),
        },
    )


app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(buyer_router, prefix="/api/v1")
app.include_router(address_router, prefix="/api/v1")
app.include_router(payment_method_router, prefix="/api/v1")
app.include_router(catalog_router, prefix="/api/v1")
app.include_router(category_navigation_router, prefix="/api/v1")
app.include_router(cart_router, prefix="/api/v1")
app.include_router(home_router, prefix="/api/v1")
app.include_router(favorite_router, prefix="/api/v1")
app.include_router(product_subscription_router, prefix="/api/v1")
app.include_router(order_router, prefix="/api/v1")
app.include_router(notification_router, prefix="/api/v1")
app.include_router(b2b_event_router, prefix="/api/v1")
