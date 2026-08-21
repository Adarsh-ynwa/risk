"""Copy the complete local SQLite dataset into the deployed PostgreSQL database.

The destination URL is intentionally accepted only through an environment
variable so credentials are not placed in shell history as command arguments.
"""

import argparse
import os
import sys
from pathlib import Path

from sqlalchemy import create_engine, delete, func, select, text

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))

from app.database import Base  # noqa: E402
from app.models import db_models  # noqa: F401, E402


def normalize_postgres_url(url: str) -> str:
    if url.startswith("postgres://"):
        return url.replace("postgres://", "postgresql+psycopg://", 1)
    if url.startswith("postgresql://"):
        return url.replace("postgresql://", "postgresql+psycopg://", 1)
    return url


def row_counts(engine) -> dict[str, int]:
    with engine.connect() as connection:
        return {
            table.name: connection.scalar(select(func.count()).select_from(table)) or 0
            for table in Base.metadata.sorted_tables
        }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source",
        type=Path,
        default=BACKEND_DIR / "data" / "airisk.db",
        help="Path to the local SQLite database",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Required confirmation that destination data may be replaced",
    )
    args = parser.parse_args()

    source_path = args.source.resolve()
    if not source_path.is_file():
        raise SystemExit(f"Local database not found: {source_path}")

    target_url = os.getenv("TARGET_DATABASE_URL", "").strip()
    if not target_url:
        raise SystemExit("Set TARGET_DATABASE_URL to Render's external PostgreSQL URL.")
    target_url = normalize_postgres_url(target_url)
    if not target_url.startswith("postgresql+psycopg://"):
        raise SystemExit("TARGET_DATABASE_URL must point to PostgreSQL.")
    if not args.replace:
        raise SystemExit("Run again with --replace after checking the displayed instructions.")

    source = create_engine(f"sqlite:///{source_path.as_posix()}")
    target = create_engine(target_url, pool_pre_ping=True)
    Base.metadata.create_all(target)

    source_counts = row_counts(source)
    print("Local rows to migrate:")
    for name, count in source_counts.items():
        print(f"  {name}: {count}")

    with source.connect() as source_connection, target.begin() as target_connection:
        for table in reversed(Base.metadata.sorted_tables):
            target_connection.execute(delete(table))

        for table in Base.metadata.sorted_tables:
            result = source_connection.execute(select(table))
            copied = 0
            while True:
                rows = result.mappings().fetchmany(1000)
                if not rows:
                    break
                target_connection.execute(table.insert(), [dict(row) for row in rows])
                copied += len(rows)
                if copied % 10000 == 0:
                    print(f"  copied {table.name}: {copied}/{source_counts[table.name]}")
            print(f"Finished {table.name}: {copied}")

        for table in Base.metadata.sorted_tables:
            if "id" not in table.c:
                continue
            table_name = table.name.replace('"', '""')
            target_connection.execute(
                text(
                    "SELECT setval(pg_get_serial_sequence(:table_name, 'id'), "
                    f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM \"{table_name}\""
                ),
                {"table_name": table.name},
            )

    target_counts = row_counts(target)
    if target_counts != source_counts:
        raise SystemExit(f"Count verification failed: local={source_counts}, target={target_counts}")
    print("Migration completed and row counts verified successfully.")


if __name__ == "__main__":
    main()
