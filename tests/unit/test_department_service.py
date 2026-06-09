"""Unit tests for DepartmentService with mocked DB session."""

import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.department import Department
from src.models.user import User
from src.models.user_department import UserDepartment
from src.services.department_service import DepartmentService
from src.schemas.department import DepartmentCreate, DepartmentUpdate


class TestCreateDepartment:
    """Tests pour la creation de departements."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return DepartmentService(mock_db)

    @pytest.mark.asyncio
    async def test_create_department_success(self, service, mock_db):
        """create cree un nouveau departement."""
        tenant_id = uuid.uuid4()
        data = DepartmentCreate(name="RH", description="Ressources Humaines")

        async def mock_refresh(obj):
            obj.id = uuid.uuid4()
            obj.tenant_id = tenant_id

        mock_db.refresh.side_effect = mock_refresh

        result = await service.create(tenant_id, data)

        assert isinstance(result, Department)
        assert result.name == "RH"
        assert result.description == "Ressources Humaines"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_department_minimal(self, service, mock_db):
        """create fonctionne avec juste le nom (description optionnelle)."""
        tenant_id = uuid.uuid4()
        data = DepartmentCreate(name="IT")

        async def mock_refresh(obj):
            obj.id = uuid.uuid4()
            obj.tenant_id = tenant_id

        mock_db.refresh.side_effect = mock_refresh

        result = await service.create(tenant_id, data)

        assert result.name == "IT"
        assert result.description is None


class TestGetDepartment:
    """Tests pour la recuperation de departements."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return DepartmentService(mock_db)

    @pytest.mark.asyncio
    async def test_get_by_id_success(self, service, mock_db):
        """get_by_id retourne un departement existant."""
        dept_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        dept = Department(
            id=dept_id,
            tenant_id=tenant_id,
            name="RH",
            description="Ressources Humaines",
        )

        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = dept
        mock_db.execute.return_value = mock_result

        result = await service.get_by_id(dept_id)

        assert result is not None
        assert result.id == dept_id
        assert result.name == "RH"

    @pytest.mark.asyncio
    async def test_get_by_id_not_found(self, service, mock_db):
        """get_by_id retourne None pour un departement inexistant."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.get_by_id(uuid.uuid4())

        assert result is None


class TestListDepartments:
    """Tests pour la liste des departements."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return DepartmentService(mock_db)

    @pytest.mark.asyncio
    async def test_list_by_tenant_returns_list(self, service, mock_db):
        """list_by_tenant retourne une liste de departements."""
        tenant_id = uuid.uuid4()

        dept1 = Department(id=uuid.uuid4(), tenant_id=tenant_id, name="RH")
        dept2 = Department(id=uuid.uuid4(), tenant_id=tenant_id, name="IT")

        mock_scalars = MagicMock()
        mock_scalars.all.return_value = [dept1, dept2]

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.list_by_tenant(tenant_id)

        assert len(result) == 2
        assert result[0].name == "RH"
        assert result[1].name == "IT"

    @pytest.mark.asyncio
    async def test_list_by_tenant_empty(self, service, mock_db):
        """list_by_tenant retourne une liste vide si aucun departement."""
        mock_scalars = MagicMock()
        mock_scalars.all.return_value = []

        mock_result = MagicMock()
        mock_result.scalars.return_value = mock_scalars
        mock_db.execute.return_value = mock_result

        result = await service.list_by_tenant(uuid.uuid4())

        assert result == []


class TestUpdateDepartment:
    """Tests pour la mise a jour de departements."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return DepartmentService(mock_db)

    @pytest.mark.asyncio
    async def test_update_success(self, service, mock_db):
        """update modifie les champs du departement."""
        dept_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        dept = Department(
            id=dept_id,
            tenant_id=tenant_id,
            name="RH",
            description="Ancienne description",
        )

        # Mock get_by_id to return our dept
        async def mock_get_by_id(d_id):
            return dept

        service.get_by_id = mock_get_by_id

        async def mock_refresh(obj):
            pass

        mock_db.refresh.side_effect = mock_refresh

        data = DepartmentUpdate(name="RH Update", description="Nouvelle description")
        result = await service.update(dept_id, tenant_id, data)

        assert result.name == "RH Update"
        assert result.description == "Nouvelle description"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_wrong_tenant(self, service, mock_db):
        """update retourne None si le tenant ne correspond pas."""
        dept_id = uuid.uuid4()
        wrong_tenant_id = uuid.uuid4()
        correct_tenant_id = uuid.uuid4()

        dept = Department(
            id=dept_id,
            tenant_id=correct_tenant_id,
            name="RH",
        )

        async def mock_get_by_id(d_id):
            return dept

        service.get_by_id = mock_get_by_id

        result = await service.update(dept_id, wrong_tenant_id, DepartmentUpdate(name="New"))

        assert result is None

    @pytest.mark.asyncio
    async def test_update_not_found(self, service, mock_db):
        """update retourne None si le departement n'existe pas."""
        async def mock_get_by_id(d_id):
            return None

        service.get_by_id = mock_get_by_id

        result = await service.update(uuid.uuid4(), uuid.uuid4(), DepartmentUpdate(name="New"))

        assert result is None


class TestDeleteDepartment:
    """Tests pour la suppression de departements."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return DepartmentService(mock_db)

    @pytest.mark.asyncio
    async def test_delete_success(self, service, mock_db):
        """delete supprime un departement."""
        dept_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        dept = Department(
            id=dept_id,
            tenant_id=tenant_id,
            name="RH",
        )

        async def mock_get_by_id(d_id):
            return dept

        service.get_by_id = mock_get_by_id

        result = await service.delete(dept_id, tenant_id)

        assert result is True
        mock_db.delete.assert_called_once_with(dept)
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_delete_wrong_tenant(self, service, mock_db):
        """delete retourne False si le tenant ne correspond pas."""
        dept_id = uuid.uuid4()
        wrong_tenant_id = uuid.uuid4()
        correct_tenant_id = uuid.uuid4()

        dept = Department(
            id=dept_id,
            tenant_id=correct_tenant_id,
            name="RH",
        )

        async def mock_get_by_id(d_id):
            return dept

        service.get_by_id = mock_get_by_id

        result = await service.delete(dept_id, wrong_tenant_id)

        assert result is False
        mock_db.delete.assert_not_called()


class TestUserAssignment:
    """Tests pour l'assignation d'utilisateurs aux departements."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return DepartmentService(mock_db)

    @pytest.mark.asyncio
    async def test_assign_user_success(self, service, mock_db):
        """assign_user assigne un utilisateur a un departement."""
        user_id = uuid.uuid4()
        dept_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        user = User(
            id=user_id,
            tenant_id=tenant_id,
            email="test@example.com",
        )

        dept = Department(
            id=dept_id,
            tenant_id=tenant_id,
            name="RH",
        )

        # Mock user lookup
        async def mock_user_lookup():
            mock_result = MagicMock()
            mock_result.scalar_one_or_none.return_value = user
            return mock_result

        # Mock dept lookup
        async def mock_get_by_id(d_id):
            return dept

        service.get_by_id = mock_get_by_id

        # Mock the user query result
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = user
        mock_db.execute.return_value = mock_user_result

        async def mock_refresh(obj):
            pass

        mock_db.refresh.side_effect = mock_refresh

        result = await service.assign_user(user_id, tenant_id, dept_id, role="member")

        assert isinstance(result, UserDepartment)
        assert result.user_id == user_id
        assert result.department_id == dept_id
        assert result.role == "member"

    @pytest.mark.asyncio
    async def test_assign_user_wrong_tenant_user(self, service, mock_db):
        """assign_user retourne None si l'utilisateur n'appartient pas au tenant."""
        user_id = uuid.uuid4()
        dept_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        # User belongs to a different tenant
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.assign_user(user_id, tenant_id, dept_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_assign_user_wrong_tenant_dept(self, service, mock_db):
        """assign_user retourne None si le departement n'appartient pas au tenant."""
        user_id = uuid.uuid4()
        dept_id = uuid.uuid4()
        tenant_id = uuid.uuid4()
        other_tenant_id = uuid.uuid4()

        user = User(id=user_id, tenant_id=tenant_id, email="test@example.com")

        dept = Department(id=dept_id, tenant_id=other_tenant_id, name="RH")

        # First query returns user, second query returns dept
        query_count = [0]
        async def mock_execute(*args, **kwargs):
            query_count[0] += 1
            if query_count[0] == 1:
                # User query
                mock_result = MagicMock()
                mock_result.scalar_one_or_none.return_value = user
                return mock_result
            else:
                # Dept query - doesn't match get_by_id, so we mock get_by_id directly
                return MagicMock()

        mock_db.execute.return_value = MagicMock()
        mock_db.execute.return_value.scalar_one_or_none.return_value = user

        async def mock_get_by_id(d_id):
            return dept

        service.get_by_id = mock_get_by_id

        result = await service.assign_user(user_id, tenant_id, dept_id)

        assert result is None

    @pytest.mark.asyncio
    async def test_remove_user_success(self, service, mock_db):
        """remove_user supprime l'assignation."""
        user_id = uuid.uuid4()
        dept_id = uuid.uuid4()
        tenant_id = uuid.uuid4()

        ud = UserDepartment(user_id=user_id, department_id=dept_id, role="member")
        dept = Department(id=dept_id, tenant_id=tenant_id, name="RH")

        # Mock the UserDepartment query
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = ud
        mock_db.execute.return_value = mock_result

        async def mock_get_by_id(d_id):
            return dept

        service.get_by_id = mock_get_by_id

        result = await service.remove_user(user_id, tenant_id, dept_id)

        assert result is True
        mock_db.delete.assert_called_once_with(ud)

    @pytest.mark.asyncio
    async def test_remove_user_not_found(self, service, mock_db):
        """remove_user retourne False si l'assignation n'existe pas."""
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        result = await service.remove_user(uuid.uuid4(), uuid.uuid4(), uuid.uuid4())

        assert result is False


class TestUserDepartmentQueries:
    """Tests pour les requetes de departements d'un utilisateur."""

    @pytest.fixture
    def mock_db(self):
        return AsyncMock()

    @pytest.fixture
    def service(self, mock_db):
        return DepartmentService(mock_db)

    @pytest.mark.asyncio
    async def test_get_user_department_ids(self, service, mock_db):
        """get_user_department_ids retourne la liste des IDs de departements."""
        user_id = uuid.uuid4()
        dept1 = uuid.uuid4()
        dept2 = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.all.return_value = [(dept1,), (dept2,)]
        mock_db.execute.return_value = mock_result

        result = await service.get_user_department_ids(user_id)

        assert len(result) == 2
        assert dept1 in result
        assert dept2 in result

    @pytest.mark.asyncio
    async def test_get_user_department_ids_empty(self, service, mock_db):
        """get_user_department_ids retourne une liste vide si aucun departement."""
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await service.get_user_department_ids(uuid.uuid4())

        assert result == []

    @pytest.mark.asyncio
    async def test_get_user_department_roles(self, service, mock_db):
        """get_user_department_roles retourne un dict departement -> role."""
        user_id = uuid.uuid4()
        dept1 = uuid.uuid4()
        dept2 = uuid.uuid4()

        mock_result = MagicMock()
        mock_result.all.return_value = [(dept1, "admin"), (dept2, "member")]
        mock_db.execute.return_value = mock_result

        result = await service.get_user_department_roles(user_id)

        assert len(result) == 2
        assert result[dept1] == "admin"
        assert result[dept2] == "member"
