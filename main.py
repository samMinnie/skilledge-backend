```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from datetime import datetime

app = FastAPI(title="SkillEdge Backend")


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================================================
# DATABASE
# =========================================================

DATABASE = "skilledge.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():

    conn = get_db()

    # -----------------------------------------------------
    # BOOKINGS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            phone TEXT NOT NULL,
            service TEXT NOT NULL,
            address TEXT NOT NULL,
            booking_date TEXT,
            booking_time TEXT,
            rate TEXT,
            status TEXT DEFAULT 'Pending',
            assigned_provider_id INTEGER,
            created_at TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # PROVIDERS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS providers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT NOT NULL,
            service TEXT NOT NULL,
            address TEXT,
            status TEXT DEFAULT 'Active',
            created_at TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # NOTIFICATIONS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER,
            provider_id INTEGER,
            message TEXT NOT NULL,
            is_read INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        )
    """)

    # -----------------------------------------------------
    # DATABASE MIGRATION
    # -----------------------------------------------------

    # Existing databases may not have assigned_provider_id.
    try:
        conn.execute(
            "ALTER TABLE bookings ADD COLUMN assigned_provider_id INTEGER"
        )
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


init_db()


# =========================================================
# MODELS
# =========================================================

class Booking(BaseModel):
    customer_name: str
    phone: str
    service: str
    address: str
    booking_date: str | None = None
    booking_time: str | None = None
    rate: str | None = None


class Provider(BaseModel):
    name: str
    phone: str
    service: str
    address: str | None = None


class ProviderUpdate(BaseModel):
    name: str | None = None
    phone: str | None = None
    service: str | None = None
    address: str | None = None
    status: str | None = None


class NotificationRead(BaseModel):
    is_read: bool = True


# =========================================================
# HOME / HEALTH
# =========================================================

@app.get("/")
def home():
    return {
        "message": "SkillEdge Backend is running",
        "version": "2.0"
    }


@app.get("/health")
def health():
    return {
        "status": "ok"
    }


# =========================================================
# BOOKINGS
# =========================================================

@app.post("/bookings")
def create_booking(booking: Booking):

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO bookings
        (
            customer_name,
            phone,
            service,
            address,
            booking_date,
            booking_time,
            rate,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        booking.customer_name,
        booking.phone,
        booking.service,
        booking.address,
        booking.booking_date,
        booking.booking_time,
        booking.rate,
        "Pending",
        datetime.now().isoformat()
    ))

    booking_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "message": "Booking created successfully",
        "booking_id": booking_id,
        "status": "Pending"
    }


@app.get("/bookings")
def get_bookings():

    conn = get_db()

    rows = conn.execute("""
        SELECT
            b.*,
            p.name AS provider_name,
            p.phone AS provider_phone
        FROM bookings b
        LEFT JOIN providers p
        ON b.assigned_provider_id = p.id
        ORDER BY b.id DESC
    """).fetchall()

    conn.close()

    return [dict(row) for row in rows]


# API alias
@app.get("/api/bookings")
def get_api_bookings():

    return get_bookings()


@app.get("/bookings/{booking_id}")
def get_booking(booking_id: int):

    conn = get_db()

    row = conn.execute("""
        SELECT
            b.*,
            p.name AS provider_name,
            p.phone AS provider_phone
        FROM bookings b
        LEFT JOIN providers p
        ON b.assigned_provider_id = p.id
        WHERE b.id = ?
    """, (booking_id,)).fetchone()

    conn.close()

    if row is None:
        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    return dict(row)


# =========================================================
# BOOKING STATUS
# =========================================================

@app.patch("/bookings/{booking_id}/status")
def update_booking_status(
    booking_id: int,
    status: str
):

    allowed_statuses = [
        "Pending",
        "Accepted",
        "Rejected",
        "Cancelled",
        "Completed"
    ]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )

    conn = get_db()

    cursor = conn.execute("""
        UPDATE bookings
        SET status = ?
        WHERE id = ?
    """, (
        status,
        booking_id
    ))

    conn.commit()

    if cursor.rowcount == 0:

        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    conn.close()

    return {
        "message": "Booking status updated",
        "booking_id": booking_id,
        "status": status
    }


# =========================================================
# PROVIDERS
# =========================================================

@app.post("/providers")
def create_provider(provider: Provider):

    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO providers
        (
            name,
            phone,
            service,
            address,
            status,
            created_at
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        provider.name,
        provider.phone,
        provider.service,
        provider.address,
        "Active",
        datetime.now().isoformat()
    ))

    provider_id = cursor.lastrowid

    conn.commit()
    conn.close()

    return {
        "message": "Provider created successfully",
        "provider_id": provider_id
    }


@app.get("/providers")
def get_providers():

    conn = get_db()

    rows = conn.execute("""
        SELECT *
        FROM providers
        ORDER BY id DESC
    """).fetchall()

    conn.close()

    return [dict(row) for row in rows]


@app.get("/api/providers")
def get_api_providers():

    return get_providers()


@app.patch("/providers/{provider_id}")
def update_provider(
    provider_id: int,
    provider: ProviderUpdate
):

    conn = get_db()

    existing = conn.execute("""
        SELECT *
        FROM providers
        WHERE id = ?
    """, (provider_id,)).fetchone()

    if existing is None:

        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Provider not found"
        )

    name = (
        provider.name
        if provider.name is not None
        else existing["name"]
    )

    phone = (
        provider.phone
        if provider.phone is not None
        else existing["phone"]
    )

    service = (
        provider.service
        if provider.service is not None
        else existing["service"]
    )

    address = (
        provider.address
        if provider.address is not None
        else existing["address"]
    )

    status = (
        provider.status
        if provider.status is not None
        else existing["status"]
    )

    conn.execute("""
        UPDATE providers
        SET
            name = ?,
            phone = ?,
            service = ?,
            address = ?,
            status = ?
        WHERE id = ?
    """, (
        name,
        phone,
        service,
        address,
        status,
        provider_id
    ))

    conn.commit()
    conn.close()

    return {
        "message": "Provider updated successfully",
        "provider_id": provider_id
    }


@app.delete("/providers/{provider_id}")
def delete_provider(provider_id: int):

    conn = get_db()

    cursor = conn.execute("""
        DELETE FROM providers
        WHERE id = ?
    """, (provider_id,))

    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        raise HTTPException(
            status_code=404,
            detail="Provider not found"
        )

    return {
        "message": "Provider deleted successfully",
        "provider_id": provider_id
    }


# =========================================================
# ASSIGN PROVIDER TO BOOKING
# =========================================================

@app.patch("/bookings/{booking_id}/provider")
def assign_provider(
    booking_id: int,
    provider_id: int
):

    conn = get_db()

    booking = conn.execute("""
        SELECT *
        FROM bookings
        WHERE id = ?
    """, (booking_id,)).fetchone()

    if booking is None:

        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Booking not found"
        )

    provider = conn.execute("""
        SELECT *
        FROM providers
        WHERE id = ?
    """, (provider_id,)).fetchone()

    if provider is None:

        conn.close()

        raise HTTPException(
            status_code=404,
            detail="Provider not found"
        )

    conn.execute("""
        UPDATE bookings
        SET assigned_provider_id = ?
        WHERE id = ?
    """, (
        provider_id,
        b
```
