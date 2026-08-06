from dataclasses import dataclass

import jwt
from fastapi import Depends, HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import settings
from app.db import get_pool

_bearer_scheme = HTTPBearer(auto_error=True)
_jwk_client = PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")


@dataclass
class AuthClaims:
    user_id: str
    email: str


async def get_current_auth_user(
    credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme),
) -> AuthClaims:
    """Verifies the Supabase-issued JWT and returns its claims.

    Does not require a `students` row to exist yet — use this directly
    for endpoints (like account creation) that run before one does.
    """
    token = credentials.credentials
    try:
        signing_key = _jwk_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience="authenticated",
            issuer=f"{settings.supabase_url}/auth/v1",
        )
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")

    if payload.get("role") != "authenticated":
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired session")

    return AuthClaims(user_id=payload["sub"], email=payload["email"])


async def get_current_student(
    auth: AuthClaims = Depends(get_current_auth_user),
) -> dict:
    row = await get_pool().fetchrow("select * from students where id = $1", auth.user_id)
    if row is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No student profile exists for this account yet",
        )
    return dict(row)
