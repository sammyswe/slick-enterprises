-- Isolated database for backend integration tests (pytest tests/integration/).
SELECT format('CREATE DATABASE %I OWNER %I', 'pricepulse_test', current_user)
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'pricepulse_test')\gexec
