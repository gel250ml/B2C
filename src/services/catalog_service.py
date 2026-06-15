from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.datastructures import QueryParams

from src.core.config import B2B_CATEGORIES_PATH, B2B_URL, B2C_TO_B2B_KEY
from src.core.exceptions import NotFoundException, ValidationException
from src.repositories.catalog_repository import CatalogRepository
from src.schemas.catalog import (
    BreadcrumbItemResponse,
    BreadcrumbsMetaResponse,
    BreadcrumbsResponse,
    CatalogCategoryResponse,
    CatalogFacetsResponse,
    CatalogProductListItemResponse,
    CategoryDetailResponse,
    CategoryParentResponse,
    CategoryTreeNodeResponse,
    CategoryTreeResponse,
    FacetValueResponse,
    PaginatedCatalogProductsResponse,
    ProductCardResponse,
    ProductSkuResponse,
)


ALLOWED_CATALOG_SORTS = ("price_asc", "price_desc", "popularity", "new")
DEFAULT_CATALOG_SORT = "popularity"
B2B_PUBLIC_PRODUCTS_PATH = "/api/v1/public/products"


class CatalogService:
    def __init__(self, session: AsyncSession):
        self.repo = CatalogRepository(session)
        self.session = session


    async def get_categories_flat(self) -> list[CatalogCategoryResponse]:
        categories = await self._get_category_map()
        roots, children = self._index_categories(categories)
        result: list[CatalogCategoryResponse] = []

        def walk(category: dict[str, Any], names_path: list[str]) -> None:
            category_path = [*names_path, category["name"]]
            result.append(
                CatalogCategoryResponse(
                    id=category["id"],
                    name=category["name"],
                    parent_id=category.get("parent_id"),
                    level=len(category_path) - 1,
                    path=category_path,
                )
            )
            for child in children.get(category["id"], []):
                walk(child, category_path)

        for root in roots:
            walk(root, [])
        return result

    async def get_categories_tree(self) -> list[CategoryTreeNodeResponse]:
        categories = await self._get_category_map()
        return self._build_category_tree(categories)

    async def get_categories_tree_response(self) -> CategoryTreeResponse:
        return CategoryTreeResponse(items=await self.get_categories_tree())

    async def get_category_detail(
        self,
        category_id: UUID,
        include_product_count: bool = False,
    ) -> CategoryDetailResponse:
        categories = await self._get_category_map()
        category = categories.get(category_id)
        if category is None:
            raise NotFoundException("Category not found")

        parent = None
        parent_id = category.get("parent_id")
        if parent_id is not None:
            parent_category = categories.get(parent_id)
            if parent_category is None:
                self._raise_orphan_node()
            parent = CategoryParentResponse(
                id=parent_category["id"],
                name=parent_category["name"],
                slug=parent_category.get("slug"),
            )

        return CategoryDetailResponse(
            id=category["id"],
            name=category["name"],
            slug=category.get("slug"),
            description=category.get("description"),
            parent=parent,
            product_count=self._category_product_count(category) if include_product_count else None,
            seo=category.get("seo"),
            meta_tags=category.get("meta_tags") or {},
            image_url=category.get("image_url"),
            is_active=bool(category.get("is_active", True)),
            created_at=self._dt_to_str(category.get("created_at")),
            updated_at=self._dt_to_str(category.get("updated_at")),
        )

    async def get_breadcrumbs(
        self,
        category_id: UUID | None,
        product_id: UUID | None,
    ) -> BreadcrumbsResponse:
        if category_id is not None and product_id is not None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "ambiguous_param",
                    "message": "only one of category_id or product_id must be provided",
                },
            )
        if category_id is None and product_id is None:
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "missing_param",
                    "message": "category_id or product_id must be provided",
                },
            )

        resolved_via = "category_id"
        resolved_product_id = None
        resolved_category_id = category_id
        if product_id is not None:
            product = await self.get_visible_product_payload(product_id)
            raw_category_id = self._product_category_id(product)
            if raw_category_id is None:
                self._raise_orphan_node()
            try:
                resolved_category_id = UUID(str(raw_category_id))
            except ValueError:
                self._raise_orphan_node()
            resolved_product_id = product_id
            resolved_via = "product_id"

        assert resolved_category_id is not None
        categories = await self._get_category_map()
        if resolved_category_id not in categories:
            if category_id is not None:
                raise NotFoundException("Category not found")
            self._raise_orphan_node()

        path = self._category_path(categories, resolved_category_id)
        slugs: list[str] = []
        items: list[BreadcrumbItemResponse] = []
        for index, category in enumerate(path):
            slug = category.get("slug") or self._slug_from_name(category["name"])
            slugs.append(slug)
            items.append(
                BreadcrumbItemResponse(
                    id=category["id"],
                    slug=category.get("slug"),
                    name=category["name"],
                    url=f"/catalog/{'/'.join(slugs)}",
                    level=index,
                    is_current=index == len(path) - 1,
                )
            )

        return BreadcrumbsResponse(
            data=items,
            meta=BreadcrumbsMetaResponse(
                resolved_via=resolved_via,
                category_id=resolved_category_id,
                product_id=resolved_product_id,
            ),
        )

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
        payload = await self._get_b2b_json(B2B_PUBLIC_PRODUCTS_PATH, upstream_query)
        return self._build_products_response(payload, limit=limit, offset=offset)

    async def get_facets(
        self,
        query_params: QueryParams,
        sort: str | None = None,
    ) -> CatalogFacetsResponse:
        if sort is not None:
            self._validate_sort(sort)

        upstream_query = self._build_facets_source_query(query_params)
        payload = await self._get_b2b_json(B2B_PUBLIC_PRODUCTS_PATH, upstream_query)
        category_id = self._extract_category_id(query_params)
        return self._build_local_facets_response(payload, query_params, category_id=category_id)

    async def get_similar_products(
        self,
        product_id: UUID,
        limit: int,
    ) -> list[CatalogProductListItemResponse]:
        product = await self.get_visible_product_payload(product_id)
        category_id = self._product_category_id(product)
        if category_id is None:
            return []

        payload = await self._get_b2b_json(
            f"{B2B_PUBLIC_PRODUCTS_PATH}/{product_id}/similar",
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
        product = await self.get_visible_product_payload(product_id)

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
            description=product.get("description") or "",
            attributes=product.get("attributes") or self._characteristics_to_attributes(product.get("characteristics", [])),
            skus=skus,
        )


    async def _get_category_map(self) -> dict[UUID, dict[str, Any]]:
        payload = await self._get_b2b_json(
            B2B_CATEGORIES_PATH,
            [],
            not_found_message="Category not found",
        )
        categories = self._normalize_categories_payload(payload)
        self._validate_category_hierarchy(categories)
        return {category["id"]: category for category in categories}

    def _build_category_tree(
        self,
        categories: dict[UUID, dict[str, Any]],
    ) -> list[CategoryTreeNodeResponse]:
        roots, children = self._index_categories(categories)

        def build_node(category: dict[str, Any], names_path: list[str]) -> CategoryTreeNodeResponse:
            category_path = [*names_path, category["name"]]
            return CategoryTreeNodeResponse(
                id=category["id"],
                name=category["name"],
                parent_id=category.get("parent_id"),
                level=len(category_path) - 1,
                path=category_path,
                children=[build_node(child, category_path) for child in children.get(category["id"], [])],
            )

        return [build_node(root, []) for root in roots]

    def _index_categories(
        self,
        categories: dict[UUID, dict[str, Any]],
    ) -> tuple[list[dict[str, Any]], dict[UUID, list[dict[str, Any]]]]:
        roots: list[dict[str, Any]] = []
        children: dict[UUID, list[dict[str, Any]]] = {}
        for category in categories.values():
            parent_id = category.get("parent_id")
            if parent_id is None:
                roots.append(category)
            else:
                children.setdefault(parent_id, []).append(category)
        return roots, children

    def _normalize_categories_payload(self, payload: dict[str, Any] | list[Any]) -> list[dict[str, Any]]:
        if isinstance(payload, list):
            raw_items = payload
        elif isinstance(payload, dict):
            raw_items = payload.get("items") or payload.get("categories") or payload.get("data") or []
        else:
            raw_items = []

        categories: list[dict[str, Any]] = []
        for raw in raw_items:
            if not isinstance(raw, dict):
                continue
            category_id = self._to_uuid(raw.get("id"))
            if category_id is None:
                continue
            parent_id = self._to_uuid(raw.get("parent_id")) if raw.get("parent_id") else None
            categories.append(
                {
                    **raw,
                    "id": category_id,
                    "name": raw.get("name") or raw.get("title") or "",
                    "slug": raw.get("slug"),
                    "parent_id": parent_id,
                }
            )
        return categories

    def _validate_category_hierarchy(self, categories: list[dict[str, Any]]) -> None:
        ids = {category["id"] for category in categories}
        for category in categories:
            parent_id = category.get("parent_id")
            if parent_id is not None and parent_id not in ids:
                self._raise_orphan_node()

        category_map = {category["id"]: category for category in categories}
        for category in categories:
            seen: set[UUID] = set()
            current = category
            while current.get("parent_id") is not None:
                parent_id = current["parent_id"]
                if parent_id in seen:
                    self._raise_orphan_node()
                seen.add(parent_id)
                parent = category_map.get(parent_id)
                if parent is None:
                    self._raise_orphan_node()
                current = parent

    def _category_path(
        self,
        categories: dict[UUID, dict[str, Any]],
        category_id: UUID,
    ) -> list[dict[str, Any]]:
        category = categories.get(category_id)
        if category is None:
            raise NotFoundException("Category not found")

        result = [category]
        seen = {category_id}
        current = category
        while current.get("parent_id") is not None:
            parent_id = current["parent_id"]
            if parent_id in seen:
                self._raise_orphan_node()
            parent = categories.get(parent_id)
            if parent is None:
                self._raise_orphan_node()
            result.append(parent)
            seen.add(parent_id)
            current = parent
        result.reverse()
        return result

    @staticmethod
    def _category_product_count(category: dict[str, Any]) -> int | None:
        for field in ("product_count", "products_count", "total_products"):
            if category.get(field) is not None:
                return CatalogService._to_int(category.get(field))
        return None

    @staticmethod
    def _raise_orphan_node() -> None:
        raise HTTPException(
            status_code=422,
            detail={"error": "orphan_node", "message": "category hierarchy is broken"},
        )

    @staticmethod
    def _dt_to_str(value: Any) -> str | None:
        if value is None:
            return None
        return value.isoformat() if hasattr(value, "isoformat") else str(value)

    @staticmethod
    def _slug_from_name(value: str) -> str:
        return value.strip().lower().replace(" ", "-") or "category"

    @staticmethod
    def _to_uuid(value: Any) -> UUID | None:
        try:
            return UUID(str(value)) if value else None
        except (TypeError, ValueError):
            return None

    async def _get_b2b_json(
        self,
        path: str,
        query: list[tuple[str, str]],
        not_found_message: str = "Category not found",
    ) -> dict[str, Any] | list[Any]:
        url = self._build_url(path, query)
        try:
            async with httpx.AsyncClient(base_url=B2B_URL, timeout=5.0, follow_redirects=True) as client:
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

    async def get_visible_product_payload(self, product_id: UUID) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(base_url=B2B_URL, timeout=5.0, follow_redirects=True) as client:
                response = await client.get(f"{B2B_PUBLIC_PRODUCTS_PATH}/{product_id}", headers=self._headers())
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

        query.extend(self._build_public_product_filter_query(query_params))
        return query

    def _build_facets_source_query(self, query_params: QueryParams) -> list[tuple[str, str]]:
        query: list[tuple[str, str]] = [("limit", "100"), ("offset", "0")]

        search = query_params.get("search") or query_params.get("q")
        if search:
            query.append(("search", search))

        query.extend(self._build_public_product_filter_query(query_params))
        return query

    def _build_public_product_filter_query(self, query_params: QueryParams) -> list[tuple[str, str]]:
        query: list[tuple[str, str]] = []
        category_id = self._extract_category_id(query_params)
        if category_id:
            query.append(("category_id", category_id))

        for name, value in self._extract_filters(query_params):
            if name == "category_id":
                continue
            if name == "price_min":
                query.append(("min_price", value))
                continue
            if name == "price_max":
                query.append(("max_price", value))
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

        items = [self.build_catalog_product_item(item) for item in raw_items if isinstance(item, dict)]
        return PaginatedCatalogProductsResponse(
            items=items,
            total_count=total_count,
            limit=response_limit,
            offset=response_offset,
        )

    def build_catalog_product_item(self, product: dict[str, Any]) -> CatalogProductListItemResponse:
        return CatalogProductListItemResponse(
            id=product["id"],
            title=product.get("title") or product.get("name") or "",
            image=self._image_url(product.get("image")) or self._image_url(product.get("cover_image")) or self._main_product_image(product),
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

    def _build_local_facets_response(
        self,
        payload: dict[str, Any] | list[Any],
        query_params: QueryParams,
        category_id: str | None,
    ) -> CatalogFacetsResponse:
        if isinstance(payload, dict) and ("facets" in payload):
            return self._build_facets_response(payload, category_id=category_id)

        raw_items = payload if isinstance(payload, list) else payload.get("items", []) if isinstance(payload, dict) else []
        selected_filters = [
            (name, value)
            for name, value in self._extract_filters(query_params)
            if name not in {"category_id", "price_min", "price_max"}
        ]

        counters: dict[str, dict[str, int]] = {}
        for product in raw_items:
            if not isinstance(product, dict):
                continue
            if not self._product_matches_selected_filters(product, selected_filters):
                continue
            for name, values in self._extract_facet_values_from_product(product).items():
                bucket = counters.setdefault(name, {})
                for value in values:
                    bucket[value] = bucket.get(value, 0) + 1

        facets = [
            {
                "name": name,
                "values": [
                    FacetValueResponse(value=value, count=count)
                    for value, count in sorted(values.items(), key=lambda item: item[0])
                ],
            }
            for name, values in sorted(counters.items(), key=lambda item: item[0])
        ]
        return CatalogFacetsResponse(category_id=category_id, facets=facets)

    def _product_matches_selected_filters(
        self,
        product: dict[str, Any],
        selected_filters: list[tuple[str, str]],
    ) -> bool:
        values_by_name = self._extract_facet_values_from_product(product)
        normalized_values = {
            self._normalize_facet_name(name): {str(value).lower() for value in values}
            for name, values in values_by_name.items()
        }

        for filter_name, expected_value in selected_filters:
            values = normalized_values.get(self._normalize_facet_name(filter_name), set())
            if str(expected_value).lower() not in values:
                return False
        return True

    def _extract_facet_values_from_product(self, product: dict[str, Any]) -> dict[str, set[str]]:
        facets: dict[str, set[str]] = {}

        def add(name: Any, value: Any) -> None:
            if name is None or value is None:
                return
            label = str(name).strip()
            if not label:
                return
            values = value if isinstance(value, list) else [value]
            for raw_value in values:
                if raw_value is None:
                    continue
                text = str(raw_value).strip()
                if text:
                    facets.setdefault(label, set()).add(text)

        attributes = product.get("attributes")
        if isinstance(attributes, dict):
            for name, value in attributes.items():
                add(name, value)

        for characteristic in product.get("characteristics", []) or []:
            if isinstance(characteristic, dict):
                add(characteristic.get("name") or characteristic.get("slug"), characteristic.get("value"))

        for field in ("brand", "color", "memory", "seller_id"):
            if product.get(field) is not None:
                add(field, product.get(field))

        seller = product.get("seller")
        if isinstance(seller, dict):
            add("seller_id", seller.get("id"))
            add("seller", seller.get("display_name"))

        for sku in product.get("skus", []) or []:
            if not isinstance(sku, dict):
                continue
            sku_attributes = sku.get("attributes")
            if isinstance(sku_attributes, dict):
                for name, value in sku_attributes.items():
                    add(name, value)
            for characteristic in sku.get("characteristics", []) or []:
                if isinstance(characteristic, dict):
                    add(characteristic.get("name") or characteristic.get("slug"), characteristic.get("value"))

        return facets

    @staticmethod
    def _normalize_facet_name(name: str) -> str:
        normalized = str(name).strip().lower().replace(" ", "_").replace("-", "_")
        aliases = {
            "бренд": "brand",
            "цвет": "color",
            "объём_памяти": "memory",
            "объем_памяти": "memory",
            "память": "memory",
            "продавец": "seller",
        }
        return aliases.get(normalized, normalized)

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
