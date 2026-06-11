from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ProductImageResponse(BaseModel):
    url: str
    ordering: int

    model_config = ConfigDict(extra="ignore")


class ProductCharacteristicResponse(BaseModel):
    name: str
    value: str

    model_config = ConfigDict(extra="ignore")


class ProductSkuResponse(BaseModel):
    id: UUID
    name: str
    price: int
    discount: int = 0
    image: str | None = None
    active_quantity: int
    in_stock: bool
    characteristics: list[ProductCharacteristicResponse] = []

    model_config = ConfigDict(extra="ignore")


class ProductCardResponse(BaseModel):
    id: UUID
    slug: str | None = None
    title: str
    description: str | None = None
    images: list[ProductImageResponse] = []
    status: str
    characteristics: list[ProductCharacteristicResponse] = []
    skus: list[ProductSkuResponse] = []

    model_config = ConfigDict(extra="ignore")
