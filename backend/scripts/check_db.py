from sqlalchemy import text

from app.db.session import engine


def main() -> None:
    with engine.connect() as connection:
        row = connection.execute(
            text("SELECT current_database(), current_user, version()")
        ).one()
    print(f"database={row[0]}")
    print(f"user={row[1]}")
    print(f"version={row[2]}")


if __name__ == "__main__":
    main()
