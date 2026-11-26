from flask import (
    Flask, request, redirect, url_for,
    session, render_template_string, flash
)
import sqlite3
import os
import uuid
from werkzeug.utils import secure_filename
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.secret_key = "change-this-secret-key"

DATABASE = "lost_found.db"
UPLOAD_FOLDER = "static/uploads"

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


# ---------------- DATABASE ----------------

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()

    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            location TEXT NOT NULL,
            photo TEXT,
            contact TEXT NOT NULL,
            question TEXT NOT NULL,
            answer_hash TEXT NOT NULL,
            owner_pin TEXT NOT NULL,
            status TEXT DEFAULT 'Open'
        )
    """)

    conn.commit()
    conn.close()


init_db()


# ---------------- HTML DESIGN ----------------

HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>Lost & Found</title>

    <style>
        body {
            font-family: Arial;
            background: #f1f5f9;
            margin: 0;
            color: #1e293b;
        }

        header {
            background: #1e3a8a;
            color: white;
            padding: 25px;
            text-align: center;
        }

        nav {
            background: #172554;
            padding: 15px;
            text-align: center;
        }

        nav a {
            color: white;
            text-decoration: none;
            margin: 12px;
        }

        .container {
            max-width: 900px;
            margin: 25px auto;
            padding: 15px;
        }

        .card {
            background: white;
            padding: 20px;
            margin-bottom: 20px;
            border-radius: 12px;
            box-shadow: 0 3px 10px #0001;
        }

        input, textarea {
            width: 100%;
            padding: 11px;
            margin: 8px 0 15px;
            box-sizing: border-box;
            border: 1px solid #ccc;
            border-radius: 6px;
        }

        button {
            background: #2563eb;
            color: white;
            padding: 11px 18px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
        }

        button:hover {
            background: #1d4ed8;
        }

        img {
            max-width: 100%;
            max-height: 220px;
            object-fit: contain;
            border-radius: 8px;
        }

        .open {
            color: green;
            font-weight: bold;
        }

        .claimed {
            color: red;
            font-weight: bold;
        }

        .message {
            background: #dbeafe;
            padding: 12px;
            border-radius: 6px;
            margin-bottom: 15px;
        }

        a {
            color: #2563eb;
        }
    </style>
</head>

<body>

<header>
    <h1>🔎 Lost & Found</h1>
    <p>Helping lost belongings find their owners</p>
</header>

<nav>
    <a href="/">Home</a>
    <a href="/post">Post Found Item</a>
    <a href="/open">Open Items</a>
    <a href="/claimed">Claimed Items</a>
</nav>

<div class="container">

    {% with messages = get_flashed_messages() %}
        {% for message in messages %}
            <div class="message">{{ message }}</div>
        {% endfor %}
    {% endwith %}

    {{ content | safe }}

</div>

</body>
</html>
"""


# ---------------- HOME PAGE ----------------

@app.route("/")
def home():

    conn = get_db()

    open_count = conn.execute(
        "SELECT COUNT(*) FROM items WHERE status='Open'"
    ).fetchone()[0]

    claimed_count = conn.execute(
        "SELECT COUNT(*) FROM items WHERE status='Claimed'"
    ).fetchone()[0]

    conn.close()

    content = f"""
    <div class="card">
        <h2>Welcome to Lost & Found!</h2>
        <p>Found something? Help someone get it back.</p>
        <p>Lost something? Search our found items.</p>
        <a href="/post"><button>Post Found Item</button></a>
    </div>

    <div class="card">
        <h2>Website Statistics</h2>
        <h3>🟢 Open Items: {open_count}</h3>
        <h3>🔴 Claimed Items: {claimed_count}</h3>
    </div>

    <div class="card">
        <h2>Find Your Belongings</h2>
        <form action="/search" method="GET">
            <input name="q" placeholder="Search item or location">
            <button type="submit">Search</button>
        </form>
    </div>
    """

    return render_template_string(HTML, content=content)


# ---------------- POST ITEM ----------------

@app.route("/post", methods=["GET", "POST"])
def post():

    if request.method == "POST":

        name = request.form["name"].strip()
        description = request.form["description"].strip()
        location = request.form["location"].strip()
        contact = request.form["contact"].strip()
        question = request.form["question"].strip()
        answer = request.form["answer"].strip()
        pin = request.form["pin"].strip()

        photo = request.files.get("photo")
        photo_name = None

        if not all([name, location, contact, question, answer, pin]):
            flash("Please fill in all required fields.")
            return redirect("/post")

        if photo and photo.filename:

            filename = secure_filename(photo.filename)
            extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

            if extension not in ALLOWED_EXTENSIONS:
                flash("Only JPG, JPEG, PNG and WEBP images are allowed.")
                return redirect("/post")

            photo_name = str(uuid.uuid4()) + "." + extension

            photo.save(
                os.path.join(app.config["UPLOAD_FOLDER"], photo_name)
            )

        conn = get_db()

        conn.execute("""
            INSERT INTO items
            (name, description, location, photo,
             contact, question, answer_hash, owner_pin)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            name, description, location, photo_name,
            contact, question,
            generate_password_hash(answer.lower()),
            generate_password_hash(pin)
        ))

        conn.commit()
        conn.close()

        flash("Your found item has been posted successfully!")
        return redirect("/open")

    content = """
    <div class="card">
        <h2>Post a Found Item</h2>

        <form method="POST" enctype="multipart/form-data">

            Item Name *
            <input name="name" required placeholder="Example: Black Wallet">

            Description
            <textarea name="description"
                placeholder="Describe the item"></textarea>

            Found Location *
            <input name="location" required
                placeholder="Example: OIST College, Bhopal">

            Upload Photo
            <input type="file" name="photo"
                accept=".jpg,.jpeg,.png,.webp">

            Your Contact Details *
            <input name="contact" required
                placeholder="Phone number or email">

            <h3>Secret Verification</h3>

            Verification Question *
            <input name="question" required
                placeholder="Example: What is written inside the wallet?">

            Correct Answer *
            <input name="answer" required
                placeholder="Enter secret answer">

            <h3>Owner Security PIN</h3>

            <input type="password" name="pin" required
                placeholder="Create a PIN to manage status">

            <button type="submit">Post Item</button>

        </form>
    </div>
    """

    return render_template_string(HTML, content=content)


# ---------------- SHOW ITEMS ----------------

def show_items(status):

    conn = get_db()

    items = conn.execute(
        "SELECT * FROM items WHERE status=? ORDER BY id DESC",
        (status,)
    ).fetchall()

    conn.close()

    content = f"<h2>{status} Items</h2>"

    for item in items:

        photo_html = ""

        if item["photo"]:
            photo_html = f'<img src="/static/uploads/{item["photo"]}">'

        content += f"""
        <div class="card">

            <h2>{item['name']}</h2>

            {photo_html}

            <p>{item['description']}</p>

            <p>📍 Location: {item['location']}</p>

            <p>Status:
                <span class="{status.lower()}">
                    {status}
                </span>
            </p>

            <a href="/item/{item['id']}">
                View Details
            </a>

        </div>
        """

    if not items:
        content += "<div class='card'>No items found.</div>"

    return render_template_string(HTML, content=content)


@app.route("/open")
def open_items():
    return show_items("Open")


@app.route("/claimed")
def claimed_items():
    return show_items("Claimed")


# ---------------- ITEM DETAILS ----------------

@app.route("/item/<int:item_id>", methods=["GET", "POST"])
def item_details(item_id):

    conn = get_db()

    item = conn.execute(
        "SELECT * FROM items WHERE id=?",
        (item_id,)
    ).fetchone()

    conn.close()

    if not item:
        return "Item not found", 404

    error = ""

    if request.method == "POST":

        answer = request.form.get("answer", "").strip()

        if check_password_hash(
            item["answer_hash"], answer.lower()
        ):

            session.setdefault("unlocked", [])

            if item_id not in session["unlocked"]:
                session["unlocked"].append(item_id)

            session.modified = True

            return redirect(url_for(
                "item_details", item_id=item_id
            ))

        else:
            error = "Incorrect answer! Try again."

    unlocked = item_id in session.get("unlocked", [])

    photo_html = ""

    if item["photo"]:
        photo_html = f'<img src="/static/uploads/{item["photo"]}">'

    contact_html = ""

    if unlocked:
        contact_html = f"""
        <h3>Contact Details</h3>
        <p>{item['contact']}</p>
        """
    else:
        contact_html = f"""
        <h3>🔐 Verify Ownership</h3>
        <p>{item['question']}</p>

        <form method="POST">
            <input name="answer" required
                placeholder="Enter your answer">
            <button type="submit">Unlock Contact</button>
        </form>

        <p style="color:red">{error}</p>
        """

    content = f"""
    <div class="card">

        <h2>{item['name']}</h2>

        {photo_html}

        <p>{item['description']}</p>

        <p>📍 Found at: {item['location']}</p>

        <p>Status: <b>{item['status']}</b></p>

        {contact_html}

    </div>

    <div class="card">
        <h3>Owner: Update Item Status</h3>

        <form method="POST" action="/claim/{item_id}">

            <input type="password" name="pin"
                placeholder="Enter owner PIN" required>

            <button type="submit">
                Mark as Claimed
            </button>

        </form>
    </div>

    <a href="/open">Back to Open Items</a>
    """

    return render_template_string(HTML, content=content)


# ---------------- CLAIM STATUS ----------------

@app.route("/claim/<int:item_id>", methods=["POST"])
def claim_item(item_id):

    pin = request.form.get("pin", "")

    conn = get_db()

    item = conn.execute(
        "SELECT * FROM items WHERE id=?",
        (item_id,)
    ).fetchone()

    if not item:
        conn.close()
        return "Item not found", 404

    if check_password_hash(item["owner_pin"], pin):

        conn.execute(
            "UPDATE items SET status='Claimed' WHERE id=?",
            (item_id,)
        )

        conn.commit()
        flash("Item successfully marked as claimed!")

    else:
        flash("Incorrect owner PIN!")

    conn.close()

    return redirect(url_for("item_details", item_id=item_id))


# ---------------- SEARCH ----------------

@app.route("/search")
def search():

    query = request.args.get("q", "").strip()

    conn = get_db()

    items = conn.execute("""
        SELECT * FROM items
        WHERE name LIKE ?
        OR location LIKE ?
        ORDER BY id DESC
    """, (
        "%" + query + "%",
        "%" + query + "%"
    )).fetchall()

    conn.close()

    content = f"<h2>Search Results: {query}</h2>"

    for item in items:

        content += f"""
        <div class="card">
            <h3>{item['name']}</h3>
            <p>📍 {item['location']}</p>
            <p>Status: {item['status']}</p>
            <a href="/item/{item['id']}">View Details</a>
        </div>
        """

    if not items:
        content += "<p>No matching items found.</p>"

    return render_template_string(HTML, content=content)


# ---------------- RUN APP ----------------

if __name__ == "__main__":
    app.run(debug=True)