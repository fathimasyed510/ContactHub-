import os
import hmac
import hashlib
import sqlite3
from pathlib import Path
from contextlib import contextmanager

import streamlit as st

APP_DIR = Path(__file__).parent
DB_PATH = Path(os.getenv("CONTACTHUB_DB", APP_DIR / "contacthub.db"))

st.set_page_config(
    page_title="ContactHub | Smart Contact Management",
    page_icon="📇",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&family=Manrope:wght@600;700;800&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
.stApp { background: #f5f7fb; }
.block-container { padding-top: 1.7rem; max-width: 1250px; }
[data-testid="stSidebar"] { background: #101b36; }
[data-testid="stSidebar"] * { color: #f3f6ff !important; }
.brand { font-family: Manrope,sans-serif; font-size: 2rem; font-weight: 800; color:#172554; }
.tagline { color:#64748b; margin-top:-8px; }
.hero { background: linear-gradient(115deg,#172554,#3156a6); color:white; padding:26px 30px; border-radius:18px; margin: 12px 0 24px; }
.hero h2 { color:white; margin:0; font-family:Manrope,sans-serif; }
.hero p { color:#dbeafe; margin:7px 0 0; }
.metric { background:white; border:1px solid #e7ebf3; padding:18px; border-radius:15px; }
.metric-label { color:#64748b; font-size:.88rem; }
.metric-value { color:#172554; font-size:1.8rem; font-weight:800; }
.panel { background:white; border:1px solid #e7ebf3; padding:20px; border-radius:16px; }
.small-muted { color:#64748b; font-size:.9rem; }
div.stButton > button { border-radius:10px; font-weight:600; }
</style>
""", unsafe_allow_html=True)


@contextmanager
def db():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize_database():
    with db() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE COLLATE NOCASE,
                salt BLOB NOT NULL,
                password_hash BLOB NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        con.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                email TEXT DEFAULT '',
                phone TEXT DEFAULT '',
                company TEXT DEFAULT '',
                notes TEXT DEFAULT '',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY(owner_id) REFERENCES users(id) ON DELETE CASCADE
            )
        """)


def password_digest(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 310_000)


def create_user(username: str, password: str):
    salt = os.urandom(16)
    digest = password_digest(password, salt)
    with db() as con:
        con.execute(
            "INSERT INTO users(username, salt, password_hash) VALUES (?, ?, ?)",
            (username.strip(), salt, digest),
        )


def authenticate(username: str, password: str):
    with db() as con:
        user = con.execute(
            "SELECT id, username, salt, password_hash FROM users WHERE username = ?",
            (username.strip(),),
        ).fetchone()
    if user and hmac.compare_digest(password_digest(password, user["salt"]), user["password_hash"]):
        return {"id": user["id"], "username": user["username"]}
    return None


def get_contacts(owner_id: int, search: str = ""):
    with db() as con:
        return con.execute("""
            SELECT * FROM contacts
            WHERE owner_id = ?
              AND (name LIKE ? OR email LIKE ? OR phone LIKE ? OR company LIKE ?)
            ORDER BY name COLLATE NOCASE
        """, (owner_id, f"%{search}%", f"%{search}%", f"%{search}%", f"%{search}%")).fetchall()


def save_contact(owner_id, name, email, phone, company, notes, contact_id=None):
    with db() as con:
        if contact_id:
            con.execute("""
                UPDATE contacts SET name=?, email=?, phone=?, company=?, notes=?
                WHERE id=? AND owner_id=?
            """, (name, email, phone, company, notes, contact_id, owner_id))
        else:
            con.execute("""
                INSERT INTO contacts(owner_id,name,email,phone,company,notes)
                VALUES (?,?,?,?,?,?)
            """, (owner_id, name, email, phone, company, notes))


def delete_contact(owner_id, contact_id):
    with db() as con:
        con.execute("DELETE FROM contacts WHERE id=? AND owner_id=?", (contact_id, owner_id))


initialize_database()

if "user" not in st.session_state:
    st.session_state.user = None
if "edit_contact" not in st.session_state:
    st.session_state.edit_contact = None

def login_screen():
    left, right = st.columns([1.15, 0.85], gap="large")
    with left:
        st.markdown('<div class="brand">ContactHub</div><div class="tagline">Your Contacts. Your Space.</div>', unsafe_allow_html=True)
        st.markdown("""
        <div class="hero" style="margin-top:28px">
          <h2>All your connections, beautifully organised.</h2>
          <p>A simple, private space to save, search and manage your contacts.</p>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("###  Stay organised")
        st.write("Keep contact details together, find people quickly, and manage your personal contact list from one dashboard.")
        st.caption("Each account sees only the contacts saved under that account.")
    with right:
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        tab_login, tab_register = st.tabs(["Log in", "Create account"])
        with tab_login:
            st.subheader("Welcome back")
            with st.form("login_form"):
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submitted = st.form_submit_button("Log in", use_container_width=True)
            if submitted:
                user = authenticate(username, password)
                if user:
                    st.session_state.user = user
                    st.rerun()
                st.error("Incorrect username or password.")
        with tab_register:
            st.subheader("Create your account")
            with st.form("register_form"):
                new_username = st.text_input("Choose a username")
                new_password = st.text_input("Create a password", type="password")
                confirm = st.text_input("Confirm password", type="password")
                submitted = st.form_submit_button("Create account", use_container_width=True)
            if submitted:
                if len(new_username.strip()) < 3:
                    st.error("Username must contain at least 3 characters.")
                elif len(new_password) < 8:
                    st.error("Use a password with at least 8 characters.")
                elif new_password != confirm:
                    st.error("The passwords do not match.")
                else:
                    try:
                        create_user(new_username, new_password)
                        st.success("Account created. You can now log in.")
                    except sqlite3.IntegrityError:
                        st.error("That username is already taken.")
        st.markdown("</div>", unsafe_allow_html=True)


def dashboard():
    user = st.session_state.user
    owner_id = user["id"]
    with st.sidebar:
        st.markdown("## 📇 ContactHub")
        st.caption("SMART CONTACT MANAGEMENT")
        st.divider()
        st.write(f"Signed in as **{user['username']}**")
        page = st.radio("NAVIGATION", ["Overview", "My Contacts", "Add Contact"], label_visibility="visible")
        st.divider()
        if st.button("Log out", use_container_width=True):
            st.session_state.user = None
            st.session_state.edit_contact = None
            st.rerun()

    contacts = get_contacts(owner_id)
    st.markdown('<div class="brand">ContactHub</div><div class="tagline">Smart Contact Management System · Your Contacts. Your Space.</div>', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="hero">
      <h2>Welcome, {user['username']} 👋</h2>
      <p>Your contacts, neatly organised in one place.</p>
    </div>
    """, unsafe_allow_html=True)

    if page == "Overview":
        total = len(contacts)
        with_email = sum(bool(c["email"]) for c in contacts)
        with_phone = sum(bool(c["phone"]) for c in contacts)
        c1, c2, c3 = st.columns(3)
        for col, label, value in [
            (c1, "TOTAL CONTACTS", total),
            (c2, "WITH EMAIL", with_email),
            (c3, "WITH PHONE", with_phone),
        ]:
            with col:
                st.markdown(f'<div class="metric"><div class="metric-label">{label}</div><div class="metric-value">{value}</div></div>', unsafe_allow_html=True)
        st.subheader("Recently added")
        if contacts:
            for c in contacts[:5]:
                with st.container(border=True):
                    a, b = st.columns([3,1])
                    a.markdown(f"**{c['name']}**")
                    a.caption(" · ".join(x for x in [c["company"], c["email"], c["phone"]] if x) or "No additional details")
                    b.caption("Contact")
        else:
            st.info("You haven't added any contacts yet. Choose **Add Contact** to get started.")

    elif page == "Add Contact":
        st.subheader("➕ Add a new contact")
        with st.form("add_contact", clear_on_submit=True):
            name = st.text_input("Full name *")
            email = st.text_input("Email address")
            phone = st.text_input("Phone number")
            company = st.text_input("Company")
            notes = st.text_area("Notes")
            submitted = st.form_submit_button("Save contact", use_container_width=True)
        if submitted:
            if not name.strip():
                st.error("Please enter the contact's name.")
            else:
                save_contact(owner_id, name.strip(), email.strip(), phone.strip(), company.strip(), notes.strip())
                st.success("Contact saved successfully.")
                st.rerun()

    elif page == "My Contacts":
        st.subheader("👥 My Contacts")
        query = st.text_input("Search by name, email, phone or company", placeholder="Start typing...")
        results = get_contacts(owner_id, query.strip())
        st.caption(f"{len(results)} contact(s) found")
        if not results:
            st.info("No contacts found. Try another search or add a contact.")
        for c in results:
            with st.container(border=True):
                top, actions = st.columns([4, 1.5])
                with top:
                    st.markdown(f"### {c['name']}")
                    details = [("✉️", c["email"]), ("📞", c["phone"]), ("🏢", c["company"])]
                    for icon, value in details:
                        if value:
                            st.write(f"{icon} {value}")
                    if c["notes"]:
                        st.caption(f"Notes: {c['notes']}")
                with actions:
                    if st.button("Edit", key=f"edit_{c['id']}", use_container_width=True):
                        st.session_state.edit_contact = dict(c)
                    if st.button("Delete", key=f"delete_{c['id']}", use_container_width=True):
                        delete_contact(owner_id, c["id"])
                        st.success("Contact deleted.")
                        st.rerun()

        current = st.session_state.edit_contact
        if current:
            st.divider()
            st.subheader(f"Edit: {current['name']}")
            with st.form("edit_contact_form"):
                name = st.text_input("Full name *", value=current["name"])
                email = st.text_input("Email address", value=current["email"])
                phone = st.text_input("Phone number", value=current["phone"])
                company = st.text_input("Company", value=current["company"])
                notes = st.text_area("Notes", value=current["notes"])
                save = st.form_submit_button("Save changes")
            if save:
                if not name.strip():
                    st.error("Name is required.")
                else:
                    save_contact(owner_id, name.strip(), email.strip(), phone.strip(), company.strip(), notes.strip(), current["id"])
                    st.session_state.edit_contact = None
                    st.success("Changes saved.")
                    st.rerun()
            if st.button("Cancel editing"):
                st.session_state.edit_contact = None
                st.rerun()

if st.session_state.user is None:
    login_screen()
else:
    dashboard()

st.markdown("<div style='text-align:center;color:#94a3b8;padding:28px 0 8px;font-size:12px'>ContactHub · Smart Contact Management System</div>", unsafe_allow_html=True)
