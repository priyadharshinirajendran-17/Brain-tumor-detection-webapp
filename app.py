import os
os.makedirs("uploads", exist_ok=True)
from flask import Flask, render_template, request, redirect, session, send_from_directory
import os, json, base64, time

from model_loader import get_model
from utils import preprocess

from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.fernet import Fernet

app = Flask(__name__)
app.secret_key = "brain_secure"

DATA_FILE = "patients.json"


# ---------------- SECURITY ----------------
def generate_key(password: str, salt: bytes):
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=100000,
    )
    return base64.urlsafe_b64encode(kdf.derive(password.encode()))


def encrypt_key(password):
    salt = os.urandom(16)
    key = generate_key(password, salt)
    f = Fernet(key)
    encrypted = f.encrypt(password.encode())
    return {
        "salt": base64.b64encode(salt).decode(),
        "data": encrypted.decode()
    }


def verify_key(stored, input_password):
    try:
        salt = base64.b64decode(stored["salt"])
        key = generate_key(input_password, salt)
        f = Fernet(key)
        return f.decrypt(stored["data"].encode()).decode() == input_password
    except:
        return False


# ---------------- FILE ROUTE ----------------
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory('uploads', filename)


# ---------------- DATA ----------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except:
        return []


def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=4)


# ---------------- HOME ----------------
@app.route('/')
def home():
    if 'login' not in session:
        return redirect('/login')

    data = load_data()
    return render_template("index.html", data=data, total=len(data))


# ---------------- LOGIN ----------------
@app.route('/login', methods=['GET','POST'])
def login():

    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if username == "admin" and password == "123":
            session['login'] = True
            return redirect('/')

        elif username == "doctor" and password == "123":
            session['login'] = True
            return redirect('/')

        else:
            return "Invalid Login"

    return render_template("login.html")


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------- ADD ----------------
@app.route('/add', methods=['GET','POST'])
def add():

    if request.method == 'POST':

        data = load_data()

        # unique ID
        if data:
            pid = str(max(int(p['id']) for p in data) + 1)
        else:
            pid = "1"

        file = request.files['file']
        os.makedirs("uploads", exist_ok=True)
        file.save(f"uploads/{pid}.jpg")

        patient = {
            "id": pid,
            "name": request.form['name'],
            "age": request.form['age'],
            "gender": request.form['gender'],
            "key": encrypt_key(request.form['key']),
            "history": []
        }

        data.append(patient)
        save_data(data)

        return redirect('/')

    return render_template("add.html")


# ---------------- DELETE ----------------
@app.route('/delete/<pid>')
def delete(pid):

    data = load_data()
    new_data = [p for p in data if p['id'] != pid]
    save_data(new_data)

    img_path = f"uploads/{pid}.jpg"
    if os.path.exists(img_path):
        os.remove(img_path)

    return redirect('/')


# ---------------- SEARCH ----------------
@app.route('/search', methods=['GET', 'POST'])
def search():

    if request.method == 'GET':
        return render_template("search.html")

    pid = request.form['id']
    key = request.form['key']
    model_name = request.form['model']

    data = load_data()

    for p in data:

        if p['id'] == pid:

            # verify key
            if not verify_key(p.get('key'), key):
                return render_template("result.html", error="Invalid Key")

            img_path = f"uploads/{pid}.jpg"

            if not os.path.exists(img_path):
                return render_template("result.html", error="Image not found")

            img = preprocess(img_path)

            # load model
            model = get_model(model_name)

            # prediction
            pred = model.predict(img)
            pred_value = float(pred[0][0])

            confidence = round(max(pred_value, 1 - pred_value) * 100, 2)

            if pred_value > 0.5:
                label = "Tumor"
            else:
                label = "No Tumor"

            result = [{
                "model": model_name.upper(),
                "label": label,
                "confidence": confidence
            }]

            return render_template(
                "result.html",
                patient=p,
                image=f"{pid}.jpg",
                results=result
            )

    return render_template("result.html", error="Patient Not Found")

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))  # Render gives PORT
    app.run(host="0.0.0.0", port=port)