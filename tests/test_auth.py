import pytest
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class TestAuthEndpoints:
    @pytest.mark.asyncio
    async def test_login_success(self, client, tenant_a, user_hr, db_session):
        response = await client.post(
            "/auth/login",
            json={"email": "hr@company.com", "password": "password123"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "hr@company.com"

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, tenant_a, user_hr, db_session):
        response = await client.post(
            "/auth/login",
            json={"email": "hr@company.com", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        response = await client.post(
            "/auth/login",
            json={"email": "nonexistent@example.com", "password": "password123"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_auth_header(self, client, tenant_a, user_hr, dept_hr, db_session):
        from src.services.auth_service import AuthService

        token = AuthService.create_access_token(user_hr.id, user_hr.tenant_id)

        response = await client.post(
            "/documents/",
            json={"title": "Test", "content": "Test content"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_no_auth_returns_401(self, client):
        response = await client.post(
            "/documents/",
            json={"title": "Test", "content": "Test"},
        )
        assert response.status_code == 401


class TestDepartmentEndpoints:
    @pytest.mark.asyncio
    async def test_create_department(self, client, tenant_a):
        response = await client.post(
            "/departments/",
            json={"name": "Marketing", "description": "Dept marketing"},
            headers={"X-API-Key": tenant_a.api_key},
        )
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Marketing"

    @pytest.mark.asyncio
    async def test_list_departments(self, client, tenant_a, dept_hr, dept_compta):
        response = await client.get(
            "/departments/",
            headers={"X-API-Key": tenant_a.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 2
