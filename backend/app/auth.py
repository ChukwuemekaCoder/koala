import jwt
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt import PyJWKClient

from app.config import settings
from app.db import get_pool

_bearer_scheme = HTTPBearer(auto_error=True)
_jwk_client = PyJWKClient(f"{settings.supabase_url}/auth/v1/.well-known/jwks.json")


async def get_current_student(
    credentials: HTTPAuthorizationCredentials = Security(_bearer_scheme),
) -> dict:
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

    student_id = payload["sub"]
    row = await get_pool().fetchrow("select * from students where id = $1", student_id)
    if row is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "No student profile exists for this account yet",
        )
    return dict(row)
