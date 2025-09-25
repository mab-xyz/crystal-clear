from sqlmodel import SQLModel, create_engine, Session
from api.core.config import settings


engine = create_engine(settings.database_url, echo=True)  # Set echo=False to reduce logs

def get_session():
    with Session(engine) as session:
        yield session


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)