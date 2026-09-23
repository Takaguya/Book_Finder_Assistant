from fastapi import Header, HTTPException, status

from app.services.firebase_service import verify_id_token


async def get_current_user(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header (expected 'Bearer <Firebase ID token>').",
        )

    token = authorization.split(" ", 1)[1].strip()
    try:
        decoded = await verify_id_token(token)
    except Exception as exc:  # firebase raises various exceptions for invalid/expired tokens
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
        ) from exc

    return {
        "uid": decoded["uid"],
        "email": decoded.get("email"),
        "name": decoded.get("name"),
        "picture": decoded.get("picture"),
    }
