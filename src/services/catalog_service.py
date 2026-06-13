from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import QueryParams

from src.core.config import B2B_URL, B2C_TO_B2B_KEY
from src.core.exceptions import NotFoundException, ValidationException
from src.repositories.catalog_repository import CatalogRepository
from src.schemas.catalog import (
    CatalogFacetsResponse,
    CatalogProductListItemResponse,
    FacetValueResponse,
    PaginatedCatalogProductsResponse,
    ProductCardResponse,
    ProductSkuResponse,
)


ALLOWED_CATALOG_SORTS = ("price_asc", "price_desc", "popularity", "new")
DEFAULT_CATALOG_SORT = "popularity"


class CatalogService:
    def __init__(self, session: AsyncSession):
        self.repo = CatalogRepository(session)
        self.session = session

    async def get_products(
        self,
        query_params: QueryParams,
        limit: int,
        offset: int,
        q: str | None,
        sort: str,
    ) -> PaginatedCatalogProductsResponse:
        self._validate_sort(sort)
        upstream_query = self._build_catalog_query(
            query_params=query_params,
            limit=limit,
            offset=offset,
            q=q,
            sort=sort,
        )
        payload = await self._get_b2b_json("/api/v1/products", upstream_query)
        return self._build_products_response(payload, limit=limit, offset=offset)

    async def get_facets(
        self,
        query_params: QueryParams,
        sort: str | None = None,
    ) -> CatalogFacetsResponse:
        if sort is not None:
            self._validate_sort(sort)
        upstream_query = self._build_facets_query(query_params)
        payload = await self._get_b2b_json("/api/v1/catalog/facets", upstream_query)
        category_id = payload.get("category_id") if isinstance(payload, dict) else None
        if category_id is None:
            category_id = self._extract_category_id(query_params)
        return self._build_facets_response(payload, category_id=category_id)

    async def get_similar_products(
        self,
        product_id: UUID,
        limit: int,
    ) -> list[CatalogProductListItemResponse]:
        product = await self._get_visible_product_payload(product_id)
        category_id = self._product_category_id(product)
        if category_id is None:
            return []

        payload = await self._get_b2b_json(
            f"/api/v1/products/{product_id}/similar",
            [
                ("category", str(category_id)),
                ("limit", str(limit)),
                ("offset", "0"),
            ],
            not_found_message="Product not found",
        )
        items = self._build_products_response(payload, limit=limit, offset=0).items
        return self._exclude_current_product(items, product_id, limit)

    async def get_product_card(self, product_id: UUID) -> ProductCardResponse:
        product = await self._get_visible_product_payload(product_id)

        skus = [self._build_public_sku(sku) for sku in product.get("skus", [])]
        prices = [sku.price for sku in skus]
        old_prices = [sku.old_price for sku in skus if sku.old_price]

        return ProductCardResponse(
            id=product["id"],
            name=product.get("name") or product.get("title") or "",
            slug=product.get("slug"),
            category=product.get("category"),
            min_price=min(prices) if prices else 0,
            old_price=min(old_prices) if old_prices else None,
            has_stock=any(sku.available_quantity > 0 for sku in skus),
            rating=product.get("rating", 0) or 0,
            reviews_count=product.get("reviews_count", 0) or 0,
            images=product.get("images", []),
            seller=product.get("seller"),
            description=product.get("description"),
            attributes=product.get("attributes") or self._characteristics_to_attributes(product.get("characteristics", [])),
            skus=skus,
        )

    async def _get_b2b_json(
        self,
        path: str,
        query: list[tuple[str, str]],
        not_found_message: str = "Category not found",
    ) -> dict[str, Any] | list[Any]:
        url = self._build_url(path, query)
        try:
            async with httpx.AsyncClient(base_url=B2B_URL, timeout=5.0) as client:
                response = await client.get(url, headers=self._headers())
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"},
            ) from exc

        if response.status_code >= 500:
            raise HTTPException(
                status_code=502,
                detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"},
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=self._safe_error_payload(response, not_found_message=not_found_message),
            )

        return response.json()

    async def _get_visible_product_payload(self, product_id: UUID) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(base_url=B2B_URL, timeout=5.0) as client:
                response = await client.get(f"/api/v1/products/{product_id}", headers=self._headers())
        except httpx.HTTPError as exc:
            raise HTTPException(
                status_code=502,
                detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"},
            ) from exc

        if response.status_code == 404:
            raise NotFoundException("Product not found")

        if response.status_code >= 500:
            raise HTTPException(
                status_code=502,
                detail={"code": "BAD_GATEWAY", "message": "B2B service unavailable"},
            )

        if response.status_code >= 400:
            raise HTTPException(
                status_code=response.status_code,
                detail=self._safe_error_payload(response, not_found_message="Product not found"),
            )

        product = response.json()
        if product.get("status") != "MODERATED" or product.get("deleted") is True:
            raise NotFoundException("Product not found")

        return product

    def _build_catalog_query(
            self,
            query_params: QueryParams,
            limit: int,
            offset: int,
            q: str | None,
            sort: str,
    ) -> list[tuple[str, str]]:
        query: list[tuple[str, str]] = [
            ("limit", str(limit)),
            ("offset", str(offset)),
            ("sort", sort),
        ]
        if q:
            query.append(("search", q))  # B2B ждёт search, не q

        category_id = self._extract_category_id(query_params)
        if category_id:
            query.append(("category_id", category_id))

        for name, value in self._extract_filters(query_params):
            if name == "category_id":
                continue
            query.append((f"filters[{name}]", value))

        return query

    def _build_facets_query(self, query_params: QueryParams) -> list[tuple[str, str]]:
        query: list[tuple[str, str]] = []
        category_id = self._extract_category_id(query_params)
        if category_id:
            query.append(("category_id", category_id))

        for name, value in self._extract_filters(query_params):
            if name == "category_id":
                continue
            query.append((f"filters[{name}]", value))

        return query

    @staticmethod
    def _extract_category_id(query_params: QueryParams) -> str | None:
        return (
            query_params.get("category_id")
            or query_params.get("filter[category_id]")
            or query_params.get("filters[category_id]")
        )

    @staticmethod
    def _extract_filters(query_params: QueryParams) -> list[tuple[str, str]]:
        result: list[tuple[str, str]] = []
        for key, value in query_params.multi_items():
            if key.startswith("filter[") and key.endswith("]"):
                result.append((key[len("filter[") : -1], value))
            elif key.startswith("filters[") and key.endswith("]"):
                result.append((key[len("filters[") : -1], value))
        return result

    def _build_products_response(
        self,
        payload: dict[str, Any] | list[Any],
        limit: int,
        offset: int,
    ) -> PaginatedCatalogProductsResponse:
        if isinstance(payload, list):
            raw_items = payload
            total_count = len(raw_items)
            response_limit = limit
            response_offset = offset
        else:
            raw_items = payload.get("items", []) or []
            total_count = self._to_int(payload.get("total_count", payload.get("total", len(raw_items))))
            response_limit = self._to_int(payload.get("limit", limit))
            response_offset = self._to_int(payload.get("offset", offset))

        items = [self._build_catalog_product_item(item) for item in raw_items if isinstance(item, dict)]
        return PaginatedCatalogProductsResponse(
            items=items,
            total_count=total_count,
            limit=response_limit,
            offset=response_offset,
        )

    def _build_catalog_product_item(self, product: dict[str, Any]) -> CatalogProductListItemResponse:
        return CatalogProductListItemResponse(
            id=product["id"],
            title=product.get("title") or product.get("name") or "",
            image=self._image_url(product.get("image")) or self._main_product_image(product),
            price=self._catalog_product_price(product),
            in_stock=self._catalog_product_in_stock(product),
            is_in_cart=bool(product.get("is_in_cart", False)),
        )

    def _build_facets_response(
        self,
        payload: dict[str, Any] | list[Any],
        category_id: str | None,
    ) -> CatalogFacetsResponse:
        if isinstance(payload, list):
            raw_facets = payload
        elif isinstance(payload.get("facets"), dict):
            raw_facets = [
                {"name": name, "values": values}
                for name, values in payload.get("facets", {}).items()
            ]
        else:
            raw_facets = payload.get("facets", []) if isinstance(payload, dict) else []

        facets = []
        for raw_facet in raw_facets:
            if not isinstance(raw_facet, dict):
                continue
            name = raw_facet.get("name") or raw_facet.get("slug")
            if not name:
                continue
            facets.append(
                {
                    "name": name,
                    "values": [
                        FacetValueResponse(
                            value=str(raw_value.get("value", raw_value.get("name", ""))),
                            count=self._to_int(raw_value.get("count", 0)),
                        )
                        for raw_value in raw_facet.get("values", []) or []
                        if isinstance(raw_value, dict)
                    ],
                }
            )

        return CatalogFacetsResponse(category_id=category_id, facets=facets)

    def _build_public_sku(self, sku: dict[str, Any]) -> ProductSkuResponse:
        base_price = sku.get("price", 0) or 0
        discount = sku.get("discount", 0) or 0
        public_price = max(base_price - discount, 0) if discount > 0 else base_price
        old_price = sku.get("old_price")
        if old_price is None and discount > 0:
            old_price = base_price

        return ProductSkuResponse(
            id=sku["id"],
            name=sku.get("name") or sku.get("sku_name") or "",
            sku_code=sku.get("sku_code"),
            price=public_price,
            old_price=old_price,
            available_quantity=sku.get("available_quantity", sku.get("active_quantity", 0)) or 0,
            attributes=sku.get("attributes") or self._characteristics_to_attributes(sku.get("characteristics", [])),
            images=self._build_sku_images(sku),
        )

    @staticmethod
    def _product_category_id(product: dict[str, Any]) -> str | None:
        category = product.get("category")
        if isinstance(category, dict) and category.get("id"):
            return str(category["id"])
        if product.get("category_id"):
            return str(product["category_id"])
        return None

    @staticmethod
    def _exclude_current_product(
        items: list[CatalogProductListItemResponse],
        product_id: UUID,
        limit: int,
    ) -> list[CatalogProductListItemResponse]:
        result: list[CatalogProductListItemResponse] = []
        seen_ids: set[UUID] = set()
        for item in items:
            if item.id == product_id or item.id in seen_ids:
                continue
            result.append(item)
            seen_ids.add(item.id)
            if len(result) >= limit:
                break
        return result

    @staticmethod
    def _validate_sort(sort: str) -> None:
        if sort in ALLOWED_CATALOG_SORTS:
            return
        allowed = ", ".join(ALLOWED_CATALOG_SORTS)
        raise ValidationException(f"Invalid sort parameter. Allowed: {allowed}")

    @staticmethod
    def _headers() -> dict[str, str]:
        headers = {}
        if B2C_TO_B2B_KEY:
            headers["X-Service-Key"] = B2C_TO_B2B_KEY
        return headers

    @staticmethod
    def _build_url(path: str, query: list[tuple[str, str]]) -> str:
        if not query:
            return path
        return f"{path}?{urlencode(query, safe='[]')}"

    @staticmethod
    def _safe_error_payload(response: httpx.Response, not_found_message: str = "Category not found") -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if isinstance(payload, dict) and "code" in payload and "message" in payload:
            return payload

        if response.status_code == 404:
            return {"code": "NOT_FOUND", "message": not_found_message}

        return {"code": "UPSTREAM_ERROR", "message": "B2B returned an error"}

    @staticmethod
    def _catalog_product_price(product: dict[str, Any]) -> int:
        for field in ("price", "min_price"):
            if product.get(field) is not None:
                return CatalogService._to_int(product.get(field))

        prices = []
        for sku in product.get("skus", []) or []:
            if not isinstance(sku, dict):
                continue
            base_price = CatalogService._to_int(sku.get("price", 0))
            discount = CatalogService._to_int(sku.get("discount", 0))
            prices.append(max(base_price - discount, 0) if discount > 0 else base_price)
        return min(prices) if prices else 0

    @staticmethod
    def _catalog_product_in_stock(product: dict[str, Any]) -> bool:
        if product.get("in_stock") is not None:
            return bool(product.get("in_stock"))
        if product.get("has_stock") is not None:
            return bool(product.get("has_stock"))

        for sku in product.get("skus", []) or []:
            if not isinstance(sku, dict):
                continue
            quantity = sku.get("available_quantity", sku.get("active_quantity", 0))
            if CatalogService._to_int(quantity) > 0:
                return True
        return False

    @staticmethod
    def _main_product_image(product: dict[str, Any]) -> str | None:
        images = product.get("images") or []
        if isinstance(images, list):
            for image in images:
                if isinstance(image, dict) and image.get("is_main"):
                    return CatalogService._image_url(image)
            if images:
                return CatalogService._image_url(images[0])

        for sku in product.get("skus", []) or []:
            if not isinstance(sku, dict):
                continue
            image = CatalogService._image_url(sku.get("image"))
            if image:
                return image
            sku_images = sku.get("images") or []
            if isinstance(sku_images, list) and sku_images:
                image = CatalogService._image_url(sku_images[0])
                if image:
                    return image
        return None

    @staticmethod
    def _image_url(image: Any) -> str | None:
        if not image:
            return None
        if isinstance(image, str):
            return image
        if isinstance(image, dict):
            value = image.get("url") or image.get("src")
            return str(value) if value else None
        return str(image)

    @staticmethod
    def _to_int(value: Any) -> int:
        try:
            return int(value or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _characteristics_to_attributes(characteristics: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            item["name"]: item.get("value")
            for item in characteristics
            if isinstance(item, dict) and item.get("name")
        }

    @staticmethod
    def _build_sku_images(sku: dict[str, Any]) -> list[dict[str, Any]]:
        images = sku.get("images")
        if images:
            return images

        image = sku.get("image")
        if not image:
            return []

        return [
            {
                "url": image,
                "ordering": 0,
                "is_main": True,
            }
        ]
