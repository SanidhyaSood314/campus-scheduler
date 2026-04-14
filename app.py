from datetime import datetime, date as date_type
from flask import Flask, request, jsonify
import sqlite3
import json
import secrets
import os

app = Flask(__name__)

from flask_cors import CORS
CORS(app)

# ======================================
# CONFIGURATION
# ======================================

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")
admin_sessions = set()

# ======================================
# DATABASE INITIALIZATION
# ======================================

def init_db():
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        venue TEXT,
        event_type TEXT,
        event_name TEXT,
        booker_name TEXT DEFAULT 'Unknown',
        date TEXT,
        start_time TEXT,
        end_time TEXT,
        status TEXT
    )
    """)

    # Migration: add booker_name column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE bookings ADD COLUMN booker_name TEXT DEFAULT 'Unknown'")
    except sqlite3.OperationalError:
        pass  # Column already exists

    conn.commit()
    conn.close()

init_db()

# ======================================
# HELPERS
# ======================================

# IMPORTANT: Always use explicit column names in SELECT queries to avoid column
# order mismatch caused by ALTER TABLE appending booker_name at the end in
# databases that were created before the migration was added.
BOOKING_COLS = "id, venue, event_type, event_name, booker_name, date, start_time, end_time, status"

def is_admin(req):
    token = req.headers.get("X-Admin-Token") or req.args.get("admin_token")
    return bool(token and token in admin_sessions)


def validate_times(start_time, end_time, booking_date):
    try:
        new_start = datetime.strptime(start_time, "%H:%M")
        new_end   = datetime.strptime(end_time,   "%H:%M")
    except ValueError:
        return None, None, "Invalid time format. Use HH:MM."

    if new_start >= new_end:
        return None, None, "Start time must be before end time."

    try:
        parsed_date = datetime.strptime(booking_date, "%Y-%m-%d").date()
    except ValueError:
        return None, None, "Invalid date format. Use YYYY-MM-DD."

    if parsed_date < date_type.today():
        return None, None, "Cannot book a venue for a past date."

    return new_start, new_end, None


def check_conflict(cursor, venue, booking_date, new_start, new_end, exclude_id=None):
    if exclude_id:
        cursor.execute("""
            SELECT id, event_name, start_time, end_time FROM bookings
            WHERE venue = ? AND date = ? AND status = 'Approved' AND id != ?
        """, (venue, booking_date, exclude_id))
    else:
        cursor.execute("""
            SELECT id, event_name, start_time, end_time FROM bookings
            WHERE venue = ? AND date = ? AND status = 'Approved'
        """, (venue, booking_date))

    for row in cursor.fetchall():
        ex_start = datetime.strptime(row[2], "%H:%M")
        ex_end   = datetime.strptime(row[3], "%H:%M")
        if new_start < ex_end and new_end > ex_start:
            return row
    return None


def row_to_dict(row):
    """
    Map a DB row to a dict using positional indexing.
    Always use BOOKING_COLS in SELECT to guarantee this order:
    0=id, 1=venue, 2=event_type, 3=event_name, 4=booker_name,
    5=date, 6=start_time, 7=end_time, 8=status
    """
    return {
        "id":          row[0],
        "venue":       row[1],
        "event_type":  row[2],
        "event_name":  row[3],
        "booker_name": row[4] if row[4] else "Unknown",
        "date":        row[5],
        "start_time":  row[6],
        "end_time":    row[7],
        "status":      row[8],
    }

# ======================================
# HOME
# ======================================

@app.route("/")
def home():
    return "Smart Campus Scheduler Backend Running 🚀"

# ======================================
# ADMIN AUTH
# ======================================

@app.route("/admin/login", methods=["POST"])
def admin_login():
    data     = request.json or {}
    password = data.get("password", "")
    if password == ADMIN_PASSWORD:
        token = secrets.token_hex(32)
        admin_sessions.add(token)
        return jsonify({"success": True, "token": token})
    return jsonify({"success": False, "message": "Incorrect password."}), 401


@app.route("/admin/logout", methods=["POST"])
def admin_logout():
    data  = request.json or {}
    token = data.get("token")
    if token and token in admin_sessions:
        admin_sessions.discard(token)
        return jsonify({"success": True, "message": "Logged out."})
    return jsonify({"success": False, "message": "Token not found."}), 400


@app.route("/admin/verify", methods=["GET"])
def admin_verify():
    return jsonify({"valid": is_admin(request)})

# ======================================
# VENUES
# ======================================

@app.route("/venues", methods=["GET"])
def get_venues():
    with open("venues.json", "r") as f:
        venues = json.load(f)
    return jsonify(venues)

# ======================================
# BOOKING ROUTES
# ======================================

@app.route("/book", methods=["POST"])
def book():
    try:
        data = request.json or {}

        required = ["venue", "event_type", "event_name", "booker_name", "date", "start_time", "end_time"]
        for field in required:
            if not str(data.get(field, "")).strip():
                return jsonify({"success": False, "message": f"'{field}' is required."}), 400

        venue        = data["venue"].strip()
        event_type   = data["event_type"].strip()
        event_name   = data["event_name"].strip()
        booker_name  = data["booker_name"].strip()
        booking_date = data["date"]
        start_time   = data["start_time"]
        end_time     = data["end_time"]

        new_start, new_end, err = validate_times(start_time, end_time, booking_date)
        if err:
            return jsonify({"success": False, "message": err}), 400

        conn   = sqlite3.connect("database.db")
        cursor = conn.cursor()

        conflict = check_conflict(cursor, venue, booking_date, new_start, new_end)
        if conflict:
            conn.close()
            return jsonify({
                "success": False,
                "message": f"Slot occupied by '{conflict[1]}' ({conflict[2]}–{conflict[3]}). Choose another time."
            }), 409

        cursor.execute("""
            INSERT INTO bookings (venue, event_type, event_name, booker_name, date, start_time, end_time, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending')
        """, (venue, event_type, event_name, booker_name, booking_date, start_time, end_time))

        conn.commit()
        booking_id = cursor.lastrowid
        conn.close()

        return jsonify({
            "success": True,
            "id": booking_id, "venue": venue, "event_type": event_type,
            "event_name": event_name, "booker_name": booker_name,
            "date": booking_date, "start_time": start_time,
            "end_time": end_time, "status": "Pending"
        }), 201

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/bookings", methods=["GET"])
def view_bookings():
    try:
        status = request.args.get("status")
        venue  = request.args.get("venue")
        date   = request.args.get("date")

        conn   = sqlite3.connect("database.db")
        cursor = conn.cursor()

        # Use explicit column list — avoids column-order bugs from ALTER TABLE migrations
        query  = f"SELECT {BOOKING_COLS} FROM bookings WHERE 1=1"
        params = []

        if status:
            query += " AND status = ?"
            params.append(status)
        if venue:
            query += " AND venue = ?"
            params.append(venue)
        if date:
            query += " AND date = ?"
            params.append(date)

        query += " ORDER BY date ASC, start_time ASC"
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        return jsonify([row_to_dict(r) for r in rows])

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/booking/<int:booking_id>", methods=["PUT"])
def update_booking(booking_id):
    try:
        data = request.json or {}

        required = ["venue", "event_type", "event_name", "booker_name", "date", "start_time", "end_time"]
        for field in required:
            if not str(data.get(field, "")).strip():
                return jsonify({"success": False, "message": f"'{field}' is required."}), 400

        venue        = data["venue"].strip()
        event_type   = data["event_type"].strip()
        event_name   = data["event_name"].strip()
        booker_name  = data["booker_name"].strip()
        booking_date = data["date"]
        start_time   = data["start_time"]
        end_time     = data["end_time"]

        new_start, new_end, err = validate_times(start_time, end_time, booking_date)
        if err:
            return jsonify({"success": False, "message": err}), 400

        conn   = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT id FROM bookings WHERE id = ?", (booking_id,))
        if cursor.fetchone() is None:
            conn.close()
            return jsonify({"success": False, "message": "Booking not found."}), 404

        conflict = check_conflict(cursor, venue, booking_date, new_start, new_end, exclude_id=booking_id)
        if conflict:
            conn.close()
            return jsonify({
                "success": False,
                "message": f"Time conflict with '{conflict[1]}' ({conflict[2]}–{conflict[3]})."
            }), 409

        cursor.execute("""
            UPDATE bookings
            SET venue=?, event_type=?, event_name=?, booker_name=?, date=?, start_time=?, end_time=?, status='Pending'
            WHERE id=?
        """, (venue, event_type, event_name, booker_name, booking_date, start_time, end_time, booking_id))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True, "message": "Booking updated and reset to Pending.",
            "id": booking_id, "venue": venue, "event_type": event_type,
            "event_name": event_name, "booker_name": booker_name,
            "date": booking_date, "start_time": start_time,
            "end_time": end_time, "status": "Pending"
        })

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/booking/<int:booking_id>", methods=["DELETE"])
def delete_booking(booking_id):
    try:
        # FIX: Delete now requires admin authentication
        if not is_admin(request):
            return jsonify({"success": False, "message": "Unauthorized. Admin access required to delete bookings."}), 403

        conn   = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE id = ?", (booking_id,))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"success": False, "message": "Booking not found."}), 404

        conn.close()
        return jsonify({"success": True, "message": "Booking deleted."})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/approve/<int:booking_id>", methods=["PUT"])
def approve_booking(booking_id):
    try:
        if not is_admin(request):
            return jsonify({"success": False, "message": "Unauthorized. Admin access required."}), 403

        conn   = sqlite3.connect("database.db")
        cursor = conn.cursor()

        cursor.execute("SELECT venue, date, start_time, end_time FROM bookings WHERE id = ?", (booking_id,))
        row = cursor.fetchone()
        if not row:
            conn.close()
            return jsonify({"success": False, "message": "Booking not found."}), 404

        venue, booking_date, start_time, end_time = row
        new_start = datetime.strptime(start_time, "%H:%M")
        new_end   = datetime.strptime(end_time,   "%H:%M")

        conflict = check_conflict(cursor, venue, booking_date, new_start, new_end, exclude_id=booking_id)
        if conflict:
            conn.close()
            return jsonify({
                "success": False,
                "message": f"Cannot approve: conflicts with '{conflict[1]}' ({conflict[2]}–{conflict[3]})."
            }), 409

        cursor.execute("UPDATE bookings SET status='Approved' WHERE id=?", (booking_id,))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Booking approved."})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/reject/<int:booking_id>", methods=["PUT"])
def reject_booking(booking_id):
    try:
        if not is_admin(request):
            return jsonify({"success": False, "message": "Unauthorized. Admin access required."}), 403

        conn   = sqlite3.connect("database.db")
        cursor = conn.cursor()
        cursor.execute("UPDATE bookings SET status='Rejected' WHERE id=?", (booking_id,))
        conn.commit()

        if cursor.rowcount == 0:
            conn.close()
            return jsonify({"success": False, "message": "Booking not found."}), 404

        conn.close()
        return jsonify({"success": True, "message": "Booking rejected."})

    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


# ======================================
# RUN
# ======================================

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
