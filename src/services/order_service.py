import hashlib
import json
import logging
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import (
    Address,
    Buyer,
    Order,
    OrderItem,
    OrderStatus,
    OrderStatusHistory,
    PaymentMethod,
    PaymentMethodType,
)
from src.repositories.idempotency_repository import IdempotencyRepository
from src.repositories.order_repository import OrderRepository
from src.schemas.order import CreateOrderRequest, OrderResponse
from src.services.b2b_catalog_client import B2BCatalogClient, B2BSkuData
from src.services.b2b_inventory_client import (
    B2BInventoryClient,
    B2BUnavailableError,
    ReserveFailedError,
)

logger = logging.getLogger(__name__)


class OrderService:
    ALLOWED_CANCEL_STATUSES = {OrderStatus.CREATED, OrderStatus.PAID}
    CHECKOUT_IDEMPOTENCY_SCOPE = "orders.checkout"
    IDEMPOTENCY_TTL = timedelta(hours=1)

    def __init__(self, session: AsyncSession):
        self.repo = OrderRepository(session)
        self.idempotency_repo = IdempotencyRepository(session)
        self.session = session
        self.b2b_catalog_client = B2BCatalogClient()
        self.b2b_inventory_client = B2BInventoryClient()

    async def create_order(
        self,
        buyer_id: UUID,
        payload: CreateOrderRequest,
        idempotency_key_header: UUID | None,
    ) -> tuple[dict, int]:
        idempotency_key = self._resolve_idempotency_key(payload, idempotency_key_header)
        items = payload.checkout_items()
        self._validate_checkout_items(items)

        request_hash = self._request_hash(payload)
        idempotency_record, existing_response = await self._claim_idempotency_key(idempotency_key, request_hash)
        if existing_response is not None:
            return existing_response, 200

        try:
            address, payment_method = await self._resolve_checkout_relations(buyer_id, payload)
            sku_map = await self._get_skus([item.sku_id for item in items])
            failed_items = self._collect_failed_items(items, sku_map)
            if failed_items:
                raise self._reserve_failed_exception(failed_items)

            await self.b2b_inventory_client.reserve(
                idempotency_key=idempotency_key,
                items=[
                    {"sku_id": str(item.sku_id), "quantity": item.quantity}
                    for item in items
                ],
            )

            order = self._build_order(
                buyer_id=buyer_id,
                idempotency_key=idempotency_key,
                payload=payload,
                items=items,
                sku_map=sku_map,
                address=address,
                payment_method=payment_method,
            )
            self.session.add(order)
            await self.session.flush()

            response_payload = OrderResponse.model_validate(order).model_dump(mode="json")
            idempotency_record.response = response_payload
            await self.session.commit()
            return response_payload, 201
        except ReserveFailedError as exc:
            await self._cleanup_idempotency_key(idempotency_key)
            raise self._reserve_failed_exception(exc.failed_items)
        except B2BUnavailableError:
            await self._cleanup_idempotency_key(idempotency_key)
            raise self._b2b_unavailable_exception()
        except HTTPException as exc:
            await self._cleanup_idempotency_key(idempotency_key)
            if exc.status_code == 503:
                raise self._b2b_unavailable_exception()
            raise
        except Exception:
            await self._cleanup_idempotency_key(idempotency_key)
            raise

    async def cancel_order(
        self,
        order_id: UUID,
        buyer_id: UUID,
        reason: str | None = None,
    ) -> OrderResponse:
        order = await self.repo.get_by_id_and_buyer(order_id, buyer_id)
        if order is None:
            raise HTTPException(
                status_code=404,
                detail={"code": "ORDER_NOT_FOUND", "message": "Заказ не найден"},
            )

        if order.status not in self.ALLOWED_CANCEL_STATUSES:
            current_status = self._status_value(order.status)
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "CANCEL_NOT_ALLOWED",
                    "message": f"Отмена невозможна: заказ в статусе {current_status}",
                    "current_status": current_status,
                },
            )

        order.cancel_reason = reason
        await self._set_status(order, OrderStatus.CANCEL_PENDING, reason)

        try:
            await self._unreserve_order(order)
        except B2BUnavailableError:
            logger.exception("Unreserve failed for order %s. Order left in CANCEL_PENDING", order.id)
            return self._to_response(order)

        await self._set_status(order, OrderStatus.CANCELLED, reason)
        return self._to_response(order)

    async def retry_pending_cancellations(self, limit: int = 100) -> int:
        orders = await self.repo.get_cancel_pending_orders(limit)
        cancelled_count = 0

        for order in orders:
            try:
                await self._unreserve_order(order)
            except B2BUnavailableError:
                logger.exception("Retry unreserve failed for order %s", order.id)
                continue

            await self._set_status(order, OrderStatus.CANCELLED, order.cancel_reason)
            cancelled_count += 1

        return cancelled_count

    def _resolve_idempotency_key(
        self,
        payload: CreateOrderRequest,
        idempotency_key_header: UUID | None,
    ) -> UUID:
        if idempotency_key_header and payload.idempotency_key and idempotency_key_header != payload.idempotency_key:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_REQUEST",
                    "message": "Idempotency-Key в заголовке и idempotency_key в body не совпадают",
                },
            )

        idempotency_key = idempotency_key_header or payload.idempotency_key
        if idempotency_key is None:
            raise HTTPException(
                status_code=400,
                detail={"code": "INVALID_REQUEST", "message": "Idempotency-Key обязателен"},
            )
        return idempotency_key

    @staticmethod
    def _validate_checkout_items(items) -> None:
        if not items:
            raise HTTPException(
                status_code=400,
                detail={
                    "code": "INVALID_REQUEST",
                    "message": "Список items не может быть пустым",
                },
            )

        if any(item.quantity < 1 for item in items):
            raise HTTPException(
                status_code=422,
                detail={
                    "code": "INVALID_QUANTITY",
                    "message": "Количество должно быть не менее 1 для каждой позиции",
                },
            )

    async def _claim_idempotency_key(self, key: UUID, request_hash: str) -> tuple[object, dict | None]:
        now = self._now()
        expires_at = now + self.IDEMPOTENCY_TTL
        existing = await self.idempotency_repo.get(self.CHECKOUT_IDEMPOTENCY_SCOPE, key)

        if existing and existing.expires_at > now:
            if existing.request_hash != request_hash:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "IDEMPOTENCY_CONFLICT",
                        "message": "Idempotency-Key уже использован с другим телом запроса",
                    },
                )
            if existing.response is None:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "IDEMPOTENCY_IN_PROGRESS",
                        "message": "Запрос с таким Idempotency-Key уже выполняется",
                    },
                )
            return existing, existing.response

        if existing:
            existing.request_hash = request_hash
            existing.response = None
            existing.expires_at = expires_at
            record = existing
        else:
            record = self.idempotency_repo.add(
                self.CHECKOUT_IDEMPOTENCY_SCOPE,
                key,
                request_hash,
                expires_at,
            )

        try:
            await self.session.commit()
        except IntegrityError:
            await self.session.rollback()
            existing = await self.idempotency_repo.get(self.CHECKOUT_IDEMPOTENCY_SCOPE, key)
            if existing and existing.request_hash == request_hash and existing.response is None:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "IDEMPOTENCY_IN_PROGRESS",
                        "message": "Запрос с таким Idempotency-Key уже выполняется",
                    },
                )
            if existing and existing.request_hash != request_hash:
                raise HTTPException(
                    status_code=409,
                    detail={
                        "code": "IDEMPOTENCY_CONFLICT",
                        "message": "Idempotency-Key уже использован с другим телом запроса",
                    },
                )
            raise
        return record, None

    async def _get_skus(self, sku_ids: list[UUID]) -> dict[UUID, B2BSkuData]:
        try:
            return await self.b2b_catalog_client.get_skus(list(dict.fromkeys(sku_ids)))
        except HTTPException as exc:
            if exc.status_code == 503:
                raise B2BUnavailableError("B2B catalog service unavailable") from exc
            raise

    async def _resolve_checkout_relations(
        self,
        buyer_id: UUID,
        payload: CreateOrderRequest,
    ) -> tuple[Address, PaymentMethod]:
        buyer = await self.repo.get_buyer(buyer_id)
        now = self._now()
        if buyer is None:
            buyer = Buyer(
                id=buyer_id,
                email=f"checkout-{buyer_id}@example.com",
                password_hash="checkout-mock",
                first_name="Checkout",
                last_name="Buyer",
                created_at=now,
                updated_at=now,
            )
            self.session.add(buyer)

        if payload.address_id:
            address = await self.repo.get_address_for_buyer(payload.address_id, buyer_id)
            if address is None:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "INVALID_REQUEST", "message": "Адрес доставки не найден"},
                )
        else:
            address = Address(
                id=uuid4(),
                buyer_id=buyer_id,
                country="RU",
                city="Mock city",
                street="Mock street",
                building="1",
                recipient_name="Checkout Buyer",
                recipient_phone="79999999999",
                comment=payload.delivery_address,
                is_default=False,
                created_at=now,
                updated_at=now,
            )
            self.session.add(address)

        if payload.payment_method_id:
            payment_method = await self.repo.get_payment_method_for_buyer(payload.payment_method_id, buyer_id)
            if payment_method is None:
                raise HTTPException(
                    status_code=400,
                    detail={"code": "INVALID_REQUEST", "message": "Способ оплаты не найден"},
                )
        else:
            payment_method = PaymentMethod(
                id=uuid4(),
                buyer_id=buyer_id,
                type=PaymentMethodType.CARD,
                card_last4="0000",
                card_brand="MOCK",
                is_default=False,
                created_at=now,
            )
            self.session.add(payment_method)

        return address, payment_method

    def _collect_failed_items(self, items, sku_map: dict[UUID, B2BSkuData]) -> list[dict]:
        failed_items: list[dict] = []
        for item in items:
            sku = sku_map.get(item.sku_id)
            if sku is None or sku.product_id is None:
                failed_items.append(
                    self._failed_item(item.sku_id, item.quantity, 0, "SKU_NOT_FOUND")
                )
                continue

            if sku.product_deleted:
                failed_items.append(
                    self._failed_item(item.sku_id, item.quantity, sku.available_quantity, "PRODUCT_DELETED")
                )
                continue

            if sku.product_blocked or sku.product_status != "MODERATED":
                failed_items.append(
                    self._failed_item(item.sku_id, item.quantity, sku.available_quantity, "PRODUCT_BLOCKED")
                )
                continue

            if sku.available_quantity < item.quantity:
                reason = "OUT_OF_STOCK" if sku.available_quantity <= 0 else "INSUFFICIENT_STOCK"
                failed_items.append(
                    self._failed_item(item.sku_id, item.quantity, sku.available_quantity, reason)
                )
        return failed_items

    @staticmethod
    def _failed_item(sku_id: UUID, requested: int, available: int, reason: str) -> dict:
        return {
            "sku_id": str(sku_id),
            "requested": requested,
            "available": available,
            "reason": reason,
        }

    def _build_order(
        self,
        buyer_id: UUID,
        idempotency_key: UUID,
        payload: CreateOrderRequest,
        items,
        sku_map: dict[UUID, B2BSkuData],
        address: Address,
        payment_method: PaymentMethod,
    ) -> Order:
        now = self._now()
        order_id = uuid4()
        subtotal = sum(sku_map[item.sku_id].unit_price * item.quantity for item in items)
        order = Order(
            id=order_id,
            buyer_id=buyer_id,
            address_id=address.id,
            payment_method_id=payment_method.id,
            number=self._generate_order_number(now),
            status=OrderStatus.PAID,
            subtotal=subtotal,
            delivery_cost=0,
            total=subtotal,
            comment=payload.comment,
            idempotency_key=idempotency_key,
            created_at=now,
            paid_at=now,
        )
        order.address = address
        order.payment_method = payment_method

        for item in items:
            sku = sku_map[item.sku_id]
            line_total = sku.unit_price * item.quantity
            product_title = sku.product_title or sku.name
            order.items.append(
                OrderItem(
                    order_id=order_id,
                    product_id=sku.product_id,
                    sku_id=item.sku_id,
                    name=product_title,
                    product_title=product_title,
                    sku_name=sku.name,
                    sku_code=sku.sku_code,
                    quantity=item.quantity,
                    unit_price=sku.unit_price,
                    line_total=line_total,
                    image_url=self._image_url(sku.image),
                )
            )

        order.status_history.append(
            OrderStatusHistory(
                order_id=order_id,
                status=OrderStatus.PAID.value,
                reason="checkout",
                changed_at=now,
            )
        )
        return order

    async def _cleanup_idempotency_key(self, key: UUID) -> None:
        await self.session.rollback()
        record = await self.idempotency_repo.get(self.CHECKOUT_IDEMPOTENCY_SCOPE, key)
        if record and record.response is None:
            await self.session.delete(record)
            await self.session.commit()

    async def _unreserve_order(self, order: Order) -> None:
        await self.b2b_inventory_client.unreserve(
            order_id=order.id,
            items=[
                {
                    "sku_id": str(item.sku_id),
                    "quantity": item.quantity,
                }
                for item in order.items
            ],
        )

    async def _set_status(
        self,
        order: Order,
        status: OrderStatus,
        reason: str | None = None,
    ) -> None:
        order.status = status
        self.repo.add_status_history(order, status, reason)
        await self.session.commit()

    @staticmethod
    def _request_hash(payload: CreateOrderRequest) -> str:
        items = [item.model_dump(mode="json") for item in payload.checkout_items()]
        normalized = {
            "address_id": str(payload.address_id) if payload.address_id else None,
            "payment_method_id": str(payload.payment_method_id) if payload.payment_method_id else None,
            "comment": payload.comment,
            "delivery_address": payload.delivery_address,
            "items": items,
        }
        raw = json.dumps(normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    @staticmethod
    def _reserve_failed_exception(failed_items: list[dict]) -> HTTPException:
        return HTTPException(
            status_code=409,
            detail={
                "code": "RESERVE_FAILED",
                "message": "Не удалось зарезервировать товары",
                "failed_items": failed_items,
            },
        )

    @staticmethod
    def _b2b_unavailable_exception() -> HTTPException:
        return HTTPException(
            status_code=503,
            detail={
                "code": "B2B_UNAVAILABLE",
                "message": "Сервис товаров временно недоступен, попробуйте позже",
            },
        )

    @staticmethod
    def _generate_order_number(now: datetime) -> str:
        return f"ORD-{now.strftime('%Y%m%d%H%M%S')}-{uuid4().hex[:8].upper()}"

    @staticmethod
    def _image_url(image) -> str | None:
        if image is None:
            return None
        if isinstance(image, dict):
            value = image.get("url") or image.get("src")
            return str(value) if value else None
        return str(image)

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC).replace(tzinfo=None)

    @staticmethod
    def _status_value(status: OrderStatus | str) -> str:
        return status.value if isinstance(status, OrderStatus) else str(status)

    @staticmethod
    def _to_response(order: Order) -> OrderResponse:
        return OrderResponse.model_validate(order)
