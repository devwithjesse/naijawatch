"""sqlite_to_neon.py
Copy data from a local SQLite database into a Postgres (Neon) database using SQLAlchemy models.

Usage:
  python sqlite_to_neon.py --sqlite backend/naijawatch.db --pg "postgres://user:pass@host:5432/dbname" [--commit]

Notes:
- This script uses the application's SQLAlchemy models (app.models) and will create tables in the
  Postgres target if they don't exist.
- By default it runs in dry-run mode and only prints what it *would* do. Pass --commit to actually
  write to the Postgres database.
- Order of table copying respects simple FK dependencies. For very large DBs you may need to tune
  batch sizes.
"""

from __future__ import annotations

import argparse
import sys

from app.database import Base
from dotenv import load_dotenv

load_dotenv()

# Import application's models and Base
from app.models import (
    Article,
    DigestSubscriber,
    Event,
    EventSource,
    EventStatistics,
    EventType,
    Location,
    RiskSnapshot,
    Source,
    State,
)
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker


def copy_table(sqlite_sess, pg_sess, Model, pk_name: str = "id", commit: bool = False):
    rows = sqlite_sess.query(Model).all()
    print(f"Found {len(rows)} rows in table {Model.__tablename__}")
    count = 0
    for r in rows:
        data = {}
        for col in Model.__table__.columns:
            name = col.name
            # copy attribute value as-is
            val = getattr(r, name)
            data[name] = val
        # Create new instance for Postgres — set attributes explicitly to avoid re-using identity map
        obj = Model()
        for k, v in data.items():
            setattr(obj, k, v)
        pg_sess.add(obj)
        count += 1
        # flush periodically to surface any integrity errors early
        if count % 200 == 0:
            pg_sess.flush()
            if commit:
                pg_sess.commit()
    # After all rows for this table are staged, flush once to ensure FK checks run now
    pg_sess.flush()
    if commit:
        pg_sess.commit()
        print(f"Inserted {count} rows into {Model.__tablename__} (committed)")
    else:
        # In dry-run mode we do not commit or rollback here; the caller will rollback after full run
        print(f"Dry-run: {count} rows staged for {Model.__tablename__}")


def reset_sequences(pg_engine):
    # For Postgres, reset sequences to max(id)
    with pg_engine.connect() as conn:
        for table, seq_col in [
            ("sources", "id"),
            ("states", "id"),
            ("event_types", "id"),
            ("locations", "id"),
            ("articles", "id"),
            ("events", "id"),
            ("event_statistics", "id"),
            ("risk_snapshots", "id"),
            ("digest_subscribers", "id"),
        ]:
            try:
                res = conn.execute(text(f"SELECT MAX({seq_col}) FROM {table}"))
                max_id = res.scalar() or 0
                # setval only if sequence exists
                seq_name = f"{table}_id_seq"
                conn.execute(
                    text(f"SELECT setval('{seq_name}', :val, true)"),
                    {"val": int(max_id)},
                )
                print(f"Set sequence {seq_name} to {max_id}")
            except Exception as e:
                print(f"Warning: could not reset sequence for {table}: {e}")


def create_tables(pg_engine):
    print("Creating tables in Postgres if they do not exist...")
    Base.metadata.create_all(bind=pg_engine)


def main(sqlite_path: str, pg_url: str, commit: bool = False):
    sqlite_url = f"sqlite:///{sqlite_path}"
    sqlite_engine = create_engine(sqlite_url, connect_args={"check_same_thread": False})
    PgEngine = create_engine(pg_url)

    # Create tables in Postgres
    create_tables(PgEngine)

    SqliteSession = sessionmaker(bind=sqlite_engine)
    PgSession = sessionmaker(bind=PgEngine)

    sqlite_sess = SqliteSession()
    pg_sess = PgSession()

    try:
        # Copy in an order that satisfies FKs
        copy_table(sqlite_sess, pg_sess, Source, commit=commit)
        copy_table(sqlite_sess, pg_sess, State, commit=commit)
        copy_table(sqlite_sess, pg_sess, EventType, commit=commit)
        copy_table(sqlite_sess, pg_sess, Location, commit=commit)
        copy_table(sqlite_sess, pg_sess, Article, commit=commit)
        copy_table(sqlite_sess, pg_sess, Event, commit=commit)
        copy_table(sqlite_sess, pg_sess, EventStatistics, commit=commit)
        copy_table(sqlite_sess, pg_sess, EventSource, commit=commit)
        copy_table(sqlite_sess, pg_sess, RiskSnapshot, commit=commit)
        copy_table(sqlite_sess, pg_sess, DigestSubscriber, commit=commit)

        if commit:
            print("All tables copied — resetting sequences...")
            reset_sequences(PgEngine)
            print("Done.")
        else:
            # In dry-run mode everything was staged but not committed — rollback to leave PG clean
            pg_sess.rollback()
            print("Dry-run complete. No changes were committed to Postgres.")
    except Exception as e:
        print(f"Error during migration: {e}")
        # Rollback on error to leave PG clean
        try:
            pg_sess.rollback()
        except Exception:
            pass
    finally:
        sqlite_sess.close()
        pg_sess.close()


if __name__ == "__main__":
    import os

    parser = argparse.ArgumentParser(description="Migrate SQLite -> Postgres (Neon)")
    parser.add_argument("--sqlite", required=True, help="Path to sqlite db file")
    parser.add_argument(
        "--pg",
        required=False,
        help="Postgres DATABASE_URL (defaults to env var DATABASE_URL)",
    )
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Actually write to Postgres (default: dry-run)",
    )
    args = parser.parse_args()

    pg_url = args.pg or os.environ.get("DATABASE_URL")
    if not args.sqlite or not pg_url:
        print("--sqlite and --pg (or env DATABASE_URL) are required")
        sys.exit(1)

    main(args.sqlite, pg_url, commit=args.commit)
