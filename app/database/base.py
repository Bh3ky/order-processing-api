from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy ORM models."""

    pass






# NOTES:
# Every model that inherits from Base contributes its table metadata 
# to Base.metadata. Alembic will later use this metadata to detect schema
# changes and generate migrations.