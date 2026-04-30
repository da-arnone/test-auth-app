import json
import uuid
from urllib.request import Request, urlopen

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from .auth_utils import authorize, issue_token, validate_token
from .models import AppUser, UserProfile
from .serializers import UserSerializer


def _json_body(request):
    if not request.body:
        return {}
    try:
        return json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return {}


def _user_payload(user):
    return UserSerializer(user).data


def _get_user(user_ref):
    try:
        user_uuid = uuid.UUID(str(user_ref))
        by_id = AppUser.objects.filter(id=user_uuid).first()
        if by_id:
            return by_id
    except (TypeError, ValueError, AttributeError):
        pass
    return AppUser.objects.filter(username=user_ref).first()


def _require_auth_admin(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "missing bearer token"}, status=401)
    token = auth_header[len("Bearer ") :]
    try:
        claims = validate_token(token)
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=401)
    if not authorize(claims, "auth-app", "auth-admin", None):
        return JsonResponse({"error": "forbidden: auth-admin role required"}, status=403)
    return None


@require_GET
def health(request):
    return JsonResponse({"status": "ok", "service": "auth-app"})


@csrf_exempt
@require_http_methods(["GET", "POST"])
def admin_users(request):
    unauthorized = _require_auth_admin(request)
    if unauthorized:
        return unauthorized
    if request.method == "GET":
        users = AppUser.objects.all().order_by("created_at")
        return JsonResponse({"data": [_user_payload(u) for u in users]})

    data = _json_body(request)
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return JsonResponse({"error": "username and password are required"}, status=400)
    if AppUser.objects.filter(username=username).exists():
        return JsonResponse({"error": "username already exists"}, status=400)

    user = AppUser(username=username, suspended=bool(data.get("suspended", False)))
    user.set_password(password)
    user.save()
    return JsonResponse({"data": _user_payload(user)}, status=201)


@csrf_exempt
@require_http_methods(["GET"])
def admin_user_detail(request, user_id):
    unauthorized = _require_auth_admin(request)
    if unauthorized:
        return unauthorized
    user = _get_user(user_id)
    if not user:
        return JsonResponse({"error": "user not found"}, status=404)
    return JsonResponse({"data": _user_payload(user)})


@csrf_exempt
@require_http_methods(["PATCH"])
def admin_user_suspended(request, user_id):
    unauthorized = _require_auth_admin(request)
    if unauthorized:
        return unauthorized
    user = _get_user(user_id)
    if not user:
        return JsonResponse({"error": "user not found"}, status=404)
    data = _json_body(request)
    user.suspended = bool(data.get("suspended"))
    user.save(update_fields=["suspended", "updated_at"])
    return JsonResponse({"data": _user_payload(user)})


@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def admin_user_profiles(request, user_id):
    unauthorized = _require_auth_admin(request)
    if unauthorized:
        return unauthorized
    user = _get_user(user_id)
    if not user:
        return JsonResponse({"error": "user not found"}, status=404)

    data = _json_body(request)
    app_scope = data.get("appScope")
    role = data.get("role")
    context = data.get("context") or None
    if not app_scope or not role:
        return JsonResponse({"error": "profile must include appScope and role"}, status=400)

    if request.method == "POST":
        profile, created = UserProfile.objects.get_or_create(
            user=user, app_scope=app_scope, role=role, context=context
        )
        message = "Profile assigned" if created else "Profile already exists"
        status_code = 201 if created else 200
        return JsonResponse(
            {
                "data": _user_payload(profile.user),
                "created": created,
                "message": message,
            },
            status=status_code,
        )

    UserProfile.objects.filter(user=user, app_scope=app_scope, role=role, context=context).delete()
    return JsonResponse({"data": _user_payload(user)})


@csrf_exempt
@require_http_methods(["PATCH"])
def admin_user_password(request, user_id):
    unauthorized = _require_auth_admin(request)
    if unauthorized:
        return unauthorized
    user = _get_user(user_id)
    if not user:
        return JsonResponse({"error": "user not found"}, status=404)
    data = _json_body(request)
    password = data.get("password")
    if not password:
        return JsonResponse({"error": "password is required"}, status=400)
    user.set_password(password)
    user.save(update_fields=["password_hash", "updated_at"])
    return JsonResponse({"data": _user_payload(user)})


@csrf_exempt
@require_http_methods(["POST"])
def third_token(request):
    data = _json_body(request)
    username = data.get("username")
    password = data.get("password")
    if not username or not password:
        return JsonResponse({"error": "username and password are required"}, status=400)

    user = AppUser.objects.filter(username=username).first()
    if not user or user.suspended or not user.verify_password(password):
        return JsonResponse({"error": "invalid credentials or account suspended"}, status=401)

    access_token = issue_token(user)
    return JsonResponse(
        {
            "data": {
                "accessToken": access_token,
                "tokenType": "Bearer",
                "expiresInSeconds": settings.TOKEN_TTL_SECONDS,
            }
        }
    )


@csrf_exempt
@require_http_methods(["POST"])
def third_validate(request):
    token = _json_body(request).get("token")
    if not token:
        return JsonResponse({"error": "token is required"}, status=400)
    try:
        claims = validate_token(token)
        return JsonResponse({"data": {"valid": True, "claims": claims}})
    except Exception as exc:
        return JsonResponse({"data": {"valid": False}, "error": str(exc)}, status=401)


@csrf_exempt
@require_http_methods(["POST"])
def third_whois(request):
    token = _json_body(request).get("token")
    if not token:
        return JsonResponse({"error": "token is required"}, status=400)
    try:
        claims = validate_token(token)
        return JsonResponse(
            {
                "data": {
                    "userId": claims.get("sub"),
                    "username": claims.get("preferred_username"),
                    "profiles": claims.get("profiles", []),
                }
            }
        )
    except Exception as exc:
        return JsonResponse({"error": str(exc)}, status=401)


@csrf_exempt
@require_http_methods(["POST"])
def third_authorize(request):
    data = _json_body(request)
    token = data.get("token")
    app_scope = data.get("appScope")
    required_role = data.get("requiredRole")
    context = data.get("context")
    if not token or not app_scope:
        return JsonResponse({"error": "token and appScope are required"}, status=400)
    try:
        claims = validate_token(token)
        allowed = authorize(claims, app_scope, required_role, context)
        return JsonResponse(
            {
                "data": {
                    "allowed": allowed,
                    "reason": "authorized" if allowed else "missing required role/profile",
                }
            }
        )
    except Exception as exc:
        return JsonResponse({"data": {"allowed": False}, "error": str(exc)}, status=401)


@require_GET
def org_health(request):
    return JsonResponse({"status": "ok", "service": "org-app"})


@require_GET
def org_contracts(request):
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return JsonResponse({"error": "missing bearer token"}, status=401)
    token = auth_header[len("Bearer ") :]
    context = request.headers.get("x-org-context")

    payload = json.dumps(
        {
            "token": token,
            "appScope": "org-app",
            "requiredRole": "org-app",
            "context": context,
        }
    ).encode("utf-8")

    try:
        request_obj = Request(
            f"{settings.AUTH_BASE_URL.rstrip('/')}/third/auth/authorize",
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urlopen(request_obj, timeout=5) as response:
            body = json.loads(response.read().decode("utf-8"))
        if not body.get("data", {}).get("allowed"):
            return JsonResponse(
                {
                    "error": "forbidden by auth-app third/auth authorization check",
                    "details": body,
                },
                status=403,
            )
    except Exception as exc:
        return JsonResponse({"error": "auth-app unavailable", "details": str(exc)}, status=502)

    org_context = context or "org-001"
    return JsonResponse(
        {
            "data": [
                {
                    "ref": "contract-001",
                    "description": "Contract payload returned by org-app after auth-app authorization",
                    "organizationId": org_context,
                }
            ]
        }
    )
