from datetime import datetime, timedelta, timezone

import jwt
from django.conf import settings


def issue_token(user):
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "preferred_username": user.username,
        "profiles": [
            {"appScope": p.app_scope, "role": p.role, "context": p.context}
            for p in user.profiles.all()
        ],
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=settings.TOKEN_TTL_SECONDS)).timestamp()),
        "iss": settings.JWT_ISSUER,
        "aud": settings.JWT_AUDIENCE,
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm="HS256")


def validate_token(token):
    return jwt.decode(
        token,
        settings.JWT_SECRET,
        algorithms=["HS256"],
        audience=settings.JWT_AUDIENCE,
        issuer=settings.JWT_ISSUER,
    )


def authorize(claims, app_scope, required_role=None, context=None):
    profiles = claims.get("profiles", []) or []
    for profile in profiles:
        if profile.get("appScope") != app_scope:
            continue
        if required_role and profile.get("role") != required_role:
            continue
        if context and profile.get("context") != context:
            continue
        return True
    return False
