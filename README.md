# ContactHub

**Smart Contact Management System**  
**Your Contacts. Your Space.**

A Streamlit + Python contact manager with account registration, login, password hashing, private per-user contacts, search, add, edit and delete.

## Run on Windows

1. Install Python 3.10 or newer.
2. Open this folder in VS Code.
3. Open Terminal → New Terminal.
4. Create a virtual environment:

   ```powershell
   python -m venv .venv
   ```

5. Activate it:

   ```powershell
   .venv\Scripts\Activate.ps1
   ```

6. Install packages:

   ```powershell
   python -m pip install -r requirements.txt
   ```

7. Start the app:

   ```powershell
   python -m streamlit run app.py
   ```

8. Streamlit will show a local address, usually `http://localhost:8501`.

## Database

The app creates a local SQLite database named `contacthub.db` automatically. It is excluded from Git by `.gitignore`.

## Important deployment note

A local SQLite file is suitable for learning and local testing. Some hosted app platforms use temporary storage, so the database may reset after redeployment or restart. For a public multi-user deployment, connect a managed database with persistent storage before sharing the app widely.

## Security notes

Passwords are stored as PBKDF2-HMAC-SHA256 hashes with unique random salts. Contact queries are restricted by the signed-in user's account ID. Use HTTPS and a persistent managed database for public deployment.
