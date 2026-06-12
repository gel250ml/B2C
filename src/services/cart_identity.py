import base64
import json
from dataclasses import dataclass
from uuid import UUID

from fastapi import Header

from src.core.exceptions import ValidationException


@dataclass(frozen=True)
class CartIdentity:
    user_id: UUID | None = None
    session_id: UUID | None = None

    @property
    def is_authenticated(self) -> bool:
        return self.user_id is not None


def _decode_jwt_sub(authorization: str | None) -> UUID | None:
    if not authorization:
        return None

    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ValidationException("Invalid Authorization header")

    parts = token.split(".")
    if len(parts) < 2:
        raise ValidationException("Invalid JWT token")

    payload = parts[1]
    payload += "=" * (-len(payload) % 4)
    try:
        decoded = base64.urlsafe_b64decode(payload.encode())
        data = json.loads(decoded)
        sub = data.get("sub")
        if not sub:
            raise ValueError
        return UUID(str(sub))
    except Exception as exc:
        raise ValidationException("Invalid JWT token") from exc


async def get_cart_identity(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_session_id: UUID | None = Header(default=None, alias="X-Session-Id"),
) -> CartIdentity:
    user_id = _decode_jwt_sub(authorization)
    if user_id:
        return CartIdentity(user_id=user_id)

    if not x_session_id:
        raise ValidationException("X-Session-Id is required for guest cart")

    return CartIdentity(session_id=x_session_id)


async def get_merge_identity(
    authorization: str | None = Header(default=None, alias="Authorization"),
    x_session_id: UUID | None = Header(default=None, alias="X-Session-Id"),
) -> CartIdentity:
    user_id = _decode_jwt_sub(authorization)
    if not user_id:
        raise ValidationException("Authorization is required for cart merge")
    if not x_session_id:
        raise ValidationException("X-Session-Id is required for cart merge")
    return CartIdentity(user_id=user_id, session_id=x_session_id)
