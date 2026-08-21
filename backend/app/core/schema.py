from sqlalchemy import inspect, text


def ensure_customer_account_schema(engine) -> None:
    """Apply the small additive migration needed by existing local installs."""
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "users" not in tables or "vehicles" not in tables:
        return

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    vehicle_columns = {column["name"] for column in inspector.get_columns("vehicles")}
    payment_columns = {column["name"] for column in inspector.get_columns("payments")} if "payments" in tables else set()
    statements = []
    if "full_name" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN full_name VARCHAR(100)")
    if "national_id" not in user_columns:
        statements.append("ALTER TABLE users ADD COLUMN national_id VARCHAR(30)")
    if "user_id" not in vehicle_columns:
        statements.append("ALTER TABLE vehicles ADD COLUMN user_id INTEGER")
    if "payments" in tables and "reservation_id" not in payment_columns:
        statements.append("ALTER TABLE payments ADD COLUMN reservation_id INTEGER")

    with engine.begin() as connection:
        for statement in statements:
            connection.execute(text(statement))
        # A reservation payment has no parking session. Older databases were
        # created before reservation payments existed and made this column
        # mandatory, so relax that constraint without touching existing data.
        if "payments" in tables and "parking_session_id" in payment_columns:
            connection.execute(text("ALTER TABLE payments ALTER COLUMN parking_session_id DROP NOT NULL"))
        connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_national_id ON users (national_id)"))
        connection.execute(text("CREATE INDEX IF NOT EXISTS ix_vehicles_user_id ON vehicles (user_id)"))
        if "payments" in tables:
            connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_payments_reservation_id ON payments (reservation_id)"))
