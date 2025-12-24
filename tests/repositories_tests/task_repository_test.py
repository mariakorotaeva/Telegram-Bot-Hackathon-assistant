# tests/repositories_tests/task_repository_test.py
import pytest
from datetime import datetime

import repositories.task_repository as repo


# ---------- Dummy Task ----------
class DummyTask:
    def __init__(
        self,
        telegram_id="tg",
        assigned_to="all",
        completed_by=None,
        is_active=True,
    ):
        self.telegram_id = telegram_id
        self.title = "title"
        self.description = "desc"
        self.assigned_to = assigned_to
        self.completed_by = completed_by or []
        self.is_active = is_active
        self.created_at = datetime.utcnow()
        self.created_by = "creator"

    @staticmethod
    def from_model(model):
        # в тестах мы используем модели/задачи как один и тот же объект
        return model

    def to_model(self):
        # возвращаем объект, который FakeSession.refresh может модифицировать
        return self


repo.Task = DummyTask  # безопасно мокируем Task (не TaskModel)


# ---------- Fake DB session & results ----------
class FakeResult:
    def __init__(self, one=None, many=None, rowcount=0):
        self._one = one
        self._many = many or []
        self.rowcount = rowcount

    def scalar_one_or_none(self):
        return self._one

    def scalars(self):
        return self

    def all(self):
        return list(self._many)


class FakeSession:
    def __init__(self, result):
        self.result = result

    async def execute(self, *_):
        # игнорируем stmt, возвращаем заранее подготовленный результат
        return self.result

    async def commit(self):
        pass

    async def refresh(self, *_):
        pass

    def add(self, *_):
        pass


class FakeDB:
    def __init__(self, session):
        self.session = session

    async def __aenter__(self):
        return self.session

    async def __aexit__(self, *args):
        pass


# ---------- SQLAlchemy-like stub statement ----------
class StubStmt:
    def __init__(self, kind="stmt"):
        self.kind = kind
        self._where = None
        self._values = None

    def where(self, *args, **kwargs):
        self._where = (args, kwargs)
        return self

    def order_by(self, *args, **kwargs):
        return self

    def values(self, *args, **kwargs):
        self._values = kwargs
        return self

    def __repr__(self):
        return f"<StubStmt {self.kind} where={self._where} values={self._values}>"


# ---------- Fixture: подмена select/update/delete ----------
@pytest.fixture(autouse=True)
def fake_sqlalchemy(monkeypatch):
    # select(), update(), delete() должны возвращать объекты с .where/.order_by/.values
    monkeypatch.setattr(repo, "select", lambda *args, **kwargs: StubStmt("select"))
    monkeypatch.setattr(repo, "update", lambda *args, **kwargs: StubStmt("update"))
    monkeypatch.setattr(repo, "delete", lambda *args, **kwargs: StubStmt("delete"))


# ---------- Тесты ----------
@pytest.mark.asyncio
async def test_get_by_id_found(monkeypatch):
    task = DummyTask()
    session = FakeSession(FakeResult(one=task))
    monkeypatch.setattr(repo, "get_db", lambda: FakeDB(session))

    r = repo.TaskRepository()
    result = await r.get_by_id(1)

    assert result == task


@pytest.mark.asyncio
async def test_get_by_id_not_found(monkeypatch):
    session = FakeSession(FakeResult(one=None))
    monkeypatch.setattr(repo, "get_db", lambda: FakeDB(session))

    r = repo.TaskRepository()
    assert await r.get_by_id(1) is None


@pytest.mark.asyncio
async def test_create(monkeypatch):
    session = FakeSession(FakeResult())
    monkeypatch.setattr(repo, "get_db", lambda: FakeDB(session))

    r = repo.TaskRepository()
    task = DummyTask()

    result = await r.create(task)
    # в наших заглушках create возвращает объект, который to_model вернул (то есть task)
    assert result == task


@pytest.mark.asyncio
async def test_update(monkeypatch):
    session = FakeSession(FakeResult())
    monkeypatch.setattr(repo, "get_db", lambda: FakeDB(session))

    r = repo.TaskRepository()
    task = DummyTask()

    assert await r.update(task) == task


@pytest.mark.asyncio
async def test_delete(monkeypatch):
    session = FakeSession(FakeResult(rowcount=1))
    monkeypatch.setattr(repo, "get_db", lambda: FakeDB(session))

    r = repo.TaskRepository()
    assert await r.delete("tg") is True

    session2 = FakeSession(FakeResult(rowcount=0))
    monkeypatch.setattr(repo, "get_db", lambda: FakeDB(session2))
    assert await r.delete("not_exists") is False


@pytest.mark.asyncio
async def test_get_all(monkeypatch):
    tasks = [DummyTask(), DummyTask()]
    session = FakeSession(FakeResult(many=tasks))
    monkeypatch.setattr(repo, "get_db", lambda: FakeDB(session))

    r = repo.TaskRepository()
    result = await r.get_all()

    assert isinstance(result, list)
    assert len(result) == 2


@pytest.mark.asyncio
async def test_get_active_by_assignee_and_completed(monkeypatch):
    # первый активен и не завершён для user
    t1 = DummyTask(telegram_id="a", assigned_to="all", completed_by=[])
    # второй — назначен user и уже завершён
    t2 = DummyTask(telegram_id="b", assigned_to="user", completed_by=["user"])
    # третий — назначен user и не завершён
    t3 = DummyTask(telegram_id="c", assigned_to="user", completed_by=[])
    session = FakeSession(FakeResult(many=[t1, t2, t3]))
    monkeypatch.setattr(repo, "get_db", lambda: FakeDB(session))

    r = repo.TaskRepository()
    active = await r.get_active_by_assignee("user")
    completed = await r.get_completed_by_assignee("user")

    # активные: t1 (all and not completed) and t3 (assigned user and not completed)
    assert any(t.telegram_id == "a" for t in active)
    assert any(t.telegram_id == "c" for t in active)
    # completed: t2
    assert any(t.telegram_id == "b" for t in completed)


