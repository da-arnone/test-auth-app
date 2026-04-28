# test-auth-app

This project is now migrated to:
- Django backend (`backend/`)
- React frontend (`frontend/`)

The backend exposes the same auth/org APIs:
- `admin/auth` for user/profile management
- `third/auth` for token issue/validation/whois/authorization
- `api/org/contracts` protected by `third/auth/authorize`

## Run

1) Install backend requirements:

```bash
pip install -r backend/requirements.txt
```

2) Run database migration + seed:

```bash
npm run backend:migrate
npm run backend:seed
```

3) Start backend:

```bash
npm run backend:run
```

4) In another terminal, start frontend:

```bash
npm run frontend:dev
```

URLs:
- backend: `http://localhost:8000`
- frontend: `http://localhost:5173`

## Seed users

- `admin` / `admin123` (profile: `auth-app/auth-admin`)
- `alice` / `alice123` (profiles: `org-app/org-app` and `org-app/org-third`, context `org-001`)

## API quick checks

Issue token:

```bash
curl -X POST http://localhost:8000/third/auth/token ^
  -H "Content-Type: application/json" ^
  -d "{\"username\":\"alice\",\"password\":\"alice123\"}"
```

Access org contracts:

```bash
curl http://localhost:8000/api/org/contracts ^
  -H "Authorization: Bearer <TOKEN>" ^
  -H "x-org-context: org-001"
```