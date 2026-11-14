"""One-shot loader that runs only when the operational database is empty."""

from pathlib import Path

from sqlalchemy import create_engine, text

from app.db.load import load
from app.evaluation.service import load_ground_truth
from app.settings import settings


def main() -> None:
    engine = create_engine(settings.database_url)
    with engine.connect() as connection:
        employee_count = connection.execute(
            text("SELECT count(*) FROM public.employee")
        ).scalar_one()
    if employee_count:
        print(f"Database already contains {employee_count} employees; seed skipped.")
        return
    data = Path("/app/data")
    load(data / "csv")
    load_ground_truth(data)


if __name__ == "__main__":
    main()
