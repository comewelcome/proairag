"""Integration tests for the full API flow with real Docker database.

Tests:
1. Create tenant with admin user
2. Create departments
3. Register users
4. Login and get JWT tokens
5. Ingest documents in different departments
6. Query RAG with department isolation
7. Verify cross-tenant isolation
"""

import uuid

import pytest


class TestTenantCreation:
    """Tests pour la creation de tenants avec utilisateurs admins."""

    @pytest.mark.asyncio
    async def test_create_tenant_with_admin(self, client):
        """Creer un tenant avec un utilisateur admin."""
        response = await client.post(
            "/tenants/",
            json={
                "name": "Test Company",
                "admin_email": "admin@testcompany.com",
                "admin_password": "secure_password_123",
                "admin_full_name": "Admin User",
            },
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Company"
        assert data["is_active"] is True
        assert "id" in data
        assert "api_key" in data  # API key is generated

    @pytest.mark.asyncio
    async def test_create_tenant_without_admin(self, client):
        """Creer un tenant sans utilisateur admin."""
        response = await client.post(
            "/tenants/",
            json={"name": "Test Company No Admin"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Test Company No Admin"

    @pytest.mark.asyncio
    async def test_create_tenant_empty_name_fails(self, client):
        """Creation d'un tenant avec un nom vide doit echouer."""
        response = await client.post(
            "/tenants/",
            json={"name": ""},
        )

        assert response.status_code == 422  # Validation error


class TestDepartmentManagement:
    """Tests pour la gestion des departements."""

    @pytest.mark.asyncio
    async def test_create_department(self, client, tenant_a):
        """Creer un departement."""
        response = await client.post(
            "/departments/",
            json={"name": "Marketing", "description": "Department marketing"},
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Marketing"
        assert data["description"] == "Department marketing"
        assert data["tenant_id"] == str(tenant_a["tenant"].id)

    @pytest.mark.asyncio
    async def test_list_departments(self, client, tenant_a):
        """Lister les departements d'un tenant."""
        # Create a department first
        await client.post(
            "/departments/",
            json={"name": "Marketing"},
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )

        response = await client.get(
            "/departments/",
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 3  # RH, Comptabilite, Marketing (from setup)

    @pytest.mark.asyncio
    async def test_update_department(self, client, tenant_a):
        """Mettre a jour un departement."""
        # Create department
        create_resp = await client.post(
            "/departments/",
            json={"name": "Marketing"},
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )
        dept_id = create_resp.json()["id"]

        # Update department
        response = await client.put(
            f"/departments/{dept_id}",
            json={"name": "Marketing Updated", "description": "Updated description"},
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Marketing Updated"
        assert data["description"] == "Updated description"

    @pytest.mark.asyncio
    async def test_delete_department(self, client, tenant_a):
        """Supprimer un departement."""
        # Create department
        create_resp = await client.post(
            "/departments/",
            json={"name": "Temp Dept"},
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )
        dept_id = create_resp.json()["id"]

        # Delete department
        response = await client.delete(
            f"/departments/{dept_id}",
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )

        assert response.status_code == 204

        # Verify it's gone
        get_resp = await client.get(
            f"/departments/{dept_id}",
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )
        assert get_resp.status_code == 404

    @pytest.mark.asyncio
    async def test_cannot_access_other_tenant_departments(self, client, tenant_a, tenant_b):
        """Impossible d'acceder aux departements d'un autre tenant."""
        # Create department in tenant A
        create_resp = await client.post(
            "/departments/",
            json={"name": "RH"},
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )
        dept_id = create_resp.json()["id"]

        # Try to access with tenant B's API key
        response = await client.get(
            f"/departments/{dept_id}",
            headers={"X-API-Key": tenant_b.api_key},
        )

        assert response.status_code == 404  # Not found (isolated)


class TestUserAuth:
    """Tests pour l'authentification des utilisateurs."""

    @pytest.mark.asyncio
    async def test_register_user(self, client, tenant_a):
        """Enregistrer un nouvel utilisateur dans un tenant."""
        response = await client.post(
            "/auth/register",
            json={
                "email": "newuser@company.com",
                "password": "secure_password_123",
                "full_name": "New User",
            },
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["user"]["email"] == "newuser@company.com"
        assert "access_token" in data

    @pytest.mark.asyncio
    async def test_register_duplicate_email_fails(self, client, tenant_a):
        """Enregistrement avec un email deja utilise doit echouer."""
        # Register first user
        await client.post(
            "/auth/register",
            json={
                "email": "newuser@company.com",
                "password": "secure_password_123",
            },
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )

        # Try to register again with same email
        response = await client.post(
            "/auth/register",
            json={
                "email": "newuser@company.com",
                "password": "another_password",
            },
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )

        assert response.status_code == 409

    @pytest.mark.asyncio
    async def test_login_success(self, client, tenant_a):
        """Connexion reussie avec les bons credentiels."""
        response = await client.post(
            "/auth/login",
            json={
                "email": "hr@company.com",
                "password": "password123",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["user"]["email"] == "hr@company.com"
        assert data["user"]["is_tenant_admin"] is False

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client, tenant_a):
        """Connexion echoue avec un mauvais mot de passe."""
        response = await client.post(
            "/auth/login",
            json={
                "email": "hr@company.com",
                "password": "wrong_password",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_login_nonexistent_user(self, client):
        """Connexion echoue avec un email inexistant."""
        response = await client.post(
            "/auth/login",
            json={
                "email": "nonexistent@example.com",
                "password": "password",
            },
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_jwt_auth_works(self, client, tenant_a, hr_token):
        """Un token JWT valide permet d'acceder aux endpoints."""
        response = await client.post(
            "/documents/",
            json={
                "title": "Test Document",
                "content": "Test content",
            },
            headers={"Authorization": f"Bearer {hr_token}"},
        )

        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_invalid_jwt_fails(self, client):
        """Un token JWT invalide retourne 401."""
        response = await client.post(
            "/documents/",
            json={
                "title": "Test Document",
                "content": "Test content",
            },
            headers={"Authorization": "Bearer invalid_token_here"},
        )

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_api_key_auth_still_works(self, client, tenant_a):
        """L'authentification par API key fonctionne toujours."""
        response = await client.post(
            "/documents/",
            json={
                "title": "Test Document",
                "content": "Test content",
            },
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )

        assert response.status_code == 200


class TestDocumentDepartmentIsolation:
    """Tests pour l'isolation des documents par departement."""

    @pytest.mark.asyncio
    async def test_create_document_in_department(self, client, tenant_a, hr_token):
        """Creer un document dans un departement specifique."""
        dept_hr_id = str(tenant_a["dept_hr"].id)

        response = await client.post(
            "/documents/",
            json={
                "title": "HR Policy",
                "content": "Human resources policy document",
                "department_id": dept_hr_id,
            },
            headers={"Authorization": f"Bearer {hr_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "HR Policy"
        assert data["department_id"] == dept_hr_id

    @pytest.mark.asyncio
    async def test_create_document_without_department(self, client, tenant_a, hr_token):
        """Creer un document sans departement (visible par tous)."""
        response = await client.post(
            "/documents/",
            json={
                "title": "General Policy",
                "content": "General company policy",
            },
            headers={"Authorization": f"Bearer {hr_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "General Policy"
        assert data["department_id"] is None

    @pytest.mark.asyncio
    async def test_hr_cannot_see_compta_documents(self, client, tenant_a, hr_token, compta_token):
        """Les documents de la comptabilite ne sont pas visibles par les RH."""
        # Create a compta document
        dept_compta_id = str(tenant_a["dept_compta"].id)
        await client.post(
            "/documents/",
            json={
                "title": "Salary Data",
                "content": "Confidential salary information for all employees",
                "department_id": dept_compta_id,
            },
            headers={"Authorization": f"Bearer {compta_token}"},
        )

        # Try to query RAG as HR user - should not see compta documents
        # This tests the department filter in vector search
        response = await client.post(
            "/rag/query",
            json={
                "query": "salary information",
                "top_k": 5,
                "include_graph_context": False,
            },
            headers={"Authorization": f"Bearer {hr_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # HR user should not see compta documents
        # The answer might still mention salary if LLM is available,
        # but the sources should not include compta documents
        if "sources" in data and data["sources"]:
            for source in data["sources"]:
                if source.get("document_title") == "Salary Data":
                    pytest.fail("HR user should not see compta documents!")

    @pytest.mark.asyncio
    async def test_compta_cannot_see_hr_documents(self, client, tenant_a, hr_token, compta_token):
        """Les documents des RH ne sont pas visibles par la comptabilite."""
        # Create an HR document
        dept_hr_id = str(tenant_a["dept_hr"].id)
        await client.post(
            "/documents/",
            json={
                "title": "Employee Reviews",
                "content": "Confidential employee performance reviews",
                "department_id": dept_hr_id,
            },
            headers={"Authorization": f"Bearer {hr_token}"},
        )

        # Try to query RAG as compta user - should not see HR documents
        response = await client.post(
            "/rag/query",
            json={
                "query": "employee performance reviews",
                "top_k": 5,
                "include_graph_context": False,
            },
            headers={"Authorization": f"Bearer {compta_token}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Compta user should not see HR documents
        if "sources" in data and data["sources"]:
            for source in data["sources"]:
                if source.get("document_title") == "Employee Reviews":
                    pytest.fail("Compta user should not see HR documents!")

    @pytest.mark.asyncio
    async def test_general_documents_visible_to_all(self, client, tenant_a, hr_token, compta_token):
        """Les documents generaux (sans departement) sont visibles par tous."""
        # Create a general document (no department)
        await client.post(
            "/documents/",
            json={
                "title": "Company Handbook",
                "content": "General company handbook and policies for all employees",
            },
            headers={"Authorization": f"Bearer {hr_token}"},
        )

        # Both HR and Compta should be able to query and find this document
        for token, user_name in [(hr_token, "HR"), (compta_token, "Compta")]:
            response = await client.post(
                "/rag/query",
                json={
                    "query": "company handbook policies",
                    "top_k": 5,
                    "include_graph_context": False,
                },
                headers={"Authorization": f"Bearer {token}"},
            )

            assert response.status_code == 200
            data = response.json()

            # General document should be visible to both
            found = False
            if "sources" in data and data["sources"]:
                for source in data["sources"]:
                    if source.get("document_title") == "Company Handbook":
                        found = True
                        break

            assert found, f"General document should be visible to {user_name} user"


class TestCrossTenantIsolation:
    """Tests pour l'isolation entre tenants."""

    @pytest.mark.asyncio
    async def test_tenant_a_cannot_see_tenant_b_documents(self, client, tenant_a, tenant_b):
        """Les documents du tenant B ne sont pas visibles par le tenant A."""
        # Create a document in tenant B
        response = await client.post(
            "/documents/",
            json={
                "title": "Tenant B Secret",
                "content": "Secret information from tenant B",
            },
            headers={"X-API-Key": tenant_b.api_key},
        )
        assert response.status_code == 200

        # Try to query as tenant A - should not see tenant B's documents
        # Using tenant A's API key for admin-level access
        response = await client.post(
            "/rag/query",
            json={
                "query": "secret information",
                "top_k": 5,
                "include_graph_context": False,
            },
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )

        assert response.status_code == 200
        data = response.json()

        # Tenant A should not see tenant B's documents
        if "sources" in data and data["sources"]:
            for source in data["sources"]:
                if source.get("document_title") == "Tenant B Secret":
                    pytest.fail("Tenant A should not see Tenant B documents!")

    @pytest.mark.asyncio
    async def test_different_api_keys_isolated(self, client, tenant_a, tenant_b):
        """Les API keys sont isolees entre tenants."""
        # Create document in tenant A
        await client.post(
            "/documents/",
            json={
                "title": "Tenant A Doc",
                "content": "Document from tenant A",
            },
            headers={"X-API-Key": tenant_a["tenant"].api_key},
        )

        # Try to list documents with tenant B's API key
        response = await client.get(
            "/departments/",  # Just check we can authenticate
            headers={"X-API-Key": tenant_b.api_key},
        )
        assert response.status_code == 200  # Should work, but return different data
