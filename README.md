# School Management Microservice Backend

FastAPI Backend with Neon PostgreSQL, Brevo Email OTP, and Cloudinary Media Storage.

## Architecture Structure

```text
├── app/
│   ├── api/
│   │   ├── auth.py
│   │   ├── teacher.py
│   │   ├── student.py
│   │   ├── homework.py
│   │   ├── integrations.py
│   │   ├── billing.py
│   │   └── router.py
│   ├── core/
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   ├── domain/
│   │   ├── email_service.py
│   │   └── cloudinary_service.py
│   ├── schemas/
│   │   ├── auth.py
│   │   ├── teacher.py
│   │   └── homework.py
│   ├── __init__.py
│   └── main.py
├── tests/
├── .dockerignore
├── .env
├── .env.example
├── docker-compose.yml
├── Dockerfile
├── pytest.ini
├── README.md
├── requirements.txt
└── run.py
```

## Setup & Run

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run database migration and seed data:
   ```bash
   python seed_neon.py
   ```
3. Start the API server:
   ```bash
   python run.py
   ```
4. Access API Documentation:
   - Swagger UI: `http://localhost:8000/docs`
   - ReDoc: `http://localhost:8000/redoc`
