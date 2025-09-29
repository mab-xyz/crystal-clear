import pytest
from sqlmodel import Session, SQLModel, create_engine

# Use an in-memory SQLite database
TEST_DB_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DB_URL, echo=True)


@pytest.fixture(name="session")
def session_fixture():
    """
    Creates a new database session for a test.
    The tables are created before the test and dropped after the test.
    """
    # Create all tables
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        yield session

    # Drop all tables after the test (optional for in-memory DB)
    SQLModel.metadata.drop_all(engine)
