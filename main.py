from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import sqlite3
from datetime import datetime

app = FastAPI(title="SkillEdge Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE = "skilledge.db"


def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

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
            created_at TEXT NOT NULL
        )
    """)

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

    conn.commit()
    conn.close()


init_db()


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


@app.get("/")
def home():
    return {"message": "SkillEdge Backend is running"}


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/bookings")
def create_booking(booking: Booking):
    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO bookings
        (customer_name, phone, service, address, booking_date,
         booking_time, rate, status, created_at)
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

    conn.commit()
    booking_id = cursor.lastrowid
    conn.close()

    return {
        "message": "Booking created successfully",
        "booking_id": booking_id,
        "status": "Pending"
    }


@app.get("/bookings")
def get_bookings():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM bookings ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return [dict(row) for row in rows]


@app.get("/bookings/{booking_id}")
def get_booking(booking_id: int):
    conn = get_db()
    row = conn.execute(
        "SELECT * FROM bookings WHERE id = ?",
        (booking_id,)
    ).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=404, detail="Booking not found")

    return dict(row)


@app.patch("/bookings/{booking_id}/status")
def update_booking_status(booking_id: int, status: str):
    allowed_statuses = [
        "Pending", "Accepted", "Rejected",
        "Cancelled", "Completed"
    ]

    if status not in allowed_statuses:
        raise HTTPException(
            status_code=400,
            detail="Invalid status"
        )

    conn = get_db()
    cursor = conn.execute(
        "UPDATE bookings SET status = ? WHERE id = ?",
        (status, booking_id)
    )
    conn.commit()
    conn.close()

    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Booking not found")

    return {
        "message": "Booking status updated",
        "booking_id": booking_id,
        "status": status
    }


@app.post("/providers")
def create_provider(provider: Provider):
    conn = get_db()

    cursor = conn.execute("""
        INSERT INTO providers
        (name, phone, service, address, status, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        provider.name,
        provider.phone,
        provider.service,
        provider.address,
        "Active",
        datetime.now().isoformat()
    ))

    conn.commit()
    provider_id = cursor.lastrowid
    conn.close()

    return {
        "message": "Provider created successfully",
        "provider_id": provider_id
    }


@app.get("/providers")
def get_providers():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM providers ORDER BY id DESC"
    ).fetchall()
    conn.close()

    return [dict(row) for row in rows]
