from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from pymongo import MongoClient

import qrcode
import os
import uuid

# =====================================================
# APP
# =====================================================

app = FastAPI()

# =====================================================
# STATIC FILES
# =====================================================

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

# =====================================================
# TEMPLATES
# =====================================================

templates = Jinja2Templates(
    directory="templates"
)

# =====================================================
# CREATE QR FOLDER
# =====================================================

os.makedirs(
    "static/qr",
    exist_ok=True
)

# =====================================================
# MONGODB
# =====================================================

MONGO_URI = "mongodb+srv://mahesh:mahesh123@food-trace-cluster.tpzyr6p.mongodb.net/?retryWrites=true&w=majority&appName=food-trace-cluster"

client = MongoClient(
    MONGO_URI
)

db = client["traceability_db"]

users_col = db["users"]

trace_col = db["trace"]

# =====================================================
# HOME PAGE
# =====================================================

@app.get("/", response_class=HTMLResponse)
def home(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="home.html"
    )

# =====================================================
# SIGNUP PAGE
# =====================================================

@app.get("/signup", response_class=HTMLResponse)
def signup_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="signup.html"
    )

# =====================================================
# SIGNUP
# =====================================================

@app.post("/signup")
def signup(

    username: str = Form(...),

    password: str = Form(...),

    role: str = Form(...)

):

    existing_user = users_col.find_one({

        "username": username

    })

    if existing_user:

        return {

            "message": "Username already exists"

        }

    users_col.insert_one({

        "username": username,

        "password": password,

        "role": role

    })

    return RedirectResponse(

        url="/login",

        status_code=303
    )

# =====================================================
# LOGIN PAGE
# =====================================================

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="login.html"
    )

# =====================================================
# LOGIN
# =====================================================

@app.post("/login")
def login(

    username: str = Form(...),

    password: str = Form(...)

):

    user = users_col.find_one({

        "username": username

    })

    if user is None:

        return {

            "message": "User not found"

        }

    if user["password"] != password:

        return {

            "message": "Wrong password"

        }

    role = user.get("role")

    return RedirectResponse(

        url=f"/dashboard?user={username}&role={role}",

        status_code=303
    )

# =====================================================
# DASHBOARD
# =====================================================

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(

    request: Request,

    user: str,

    role: str

):

    batches = list(

        trace_col.find(

            {"updated_by": user},

            {"_id": 0}

        )

    )

    return templates.TemplateResponse(

        request=request,

        name="dashboard.html",

        context={

            "user": user,

            "role": role,

            "batches": batches

        }
    )

# =====================================================
# ADD TRACE
# =====================================================

@app.post("/add")
def add_trace(

    # COMMON
    product: str = Form(...),
    location: str = Form(...),
    date: str = Form(...),
    time: str = Form(...),
    details: str = Form(...),
    updated_by: str = Form(...),

    # OPTIONAL
    batchId: str = Form(None),

    # FARM
    seed_date: str = Form(None),
    harvest_date: str = Form(None),
    fertilizer: str = Form(None),

    # FACTORY
    packaging: str = Form(None),

    # WAREHOUSE
    storage_temp: str = Form(None),
    shelf: str = Form(None),
    humidity: str = Form(None),

    # TRANSPORT
    destination: str = Form(None),
    vehicle: str = Form(None),
    driver: str = Form(None),

    # RETAIL
    shop_name: str = Form(None),
    price: str = Form(None),
    expiry_date: str = Form(None)

):

    # =================================================
    # FIND USER
    # =================================================

    user = users_col.find_one({

        "username": updated_by

    })

    user_role = user["role"]

    # =================================================
    # FARMER CREATE NEW UNIQUE BATCH
    # =================================================

    if user_role == "farm":

        batchId = "BATCH-" + str(uuid.uuid4())[:8].upper()

    # =================================================
    # OTHER USERS UPDATE EXISTING BATCH
    # =================================================

    else:

        existing_batch = trace_col.find_one({

            "batchId": batchId

        })

        if not existing_batch:

            return {

                "message": "Batch ID not found"

            }

    # =================================================
    # QR URL
    # =================================================

    qr_url = f"http://127.0.0.1:8000/result?id={batchId}"

    # =================================================
    # CREATE QR
    # =================================================

    qr_img = qrcode.make(qr_url)

    qr_filename = f"{batchId}.png"

    qr_path = os.path.join(

        "static",
        "qr",
        qr_filename

    )

    qr_img.save(qr_path)

    # =================================================
    # SAVE DATABASE
    # =================================================

    trace_col.insert_one({

        "batchId": batchId,

        "product": product,

        "location": location,

        "date": date,

        "time": time,

        "details": details,

        "updated_by": updated_by,

        "role": user_role,

        # FARM
        "seed_date": seed_date,
        "harvest_date": harvest_date,
        "fertilizer": fertilizer,

        # FACTORY
        "packaging": packaging,

        # WAREHOUSE
        "storage_temp": storage_temp,
        "shelf": shelf,
        "humidity": humidity,

        # TRANSPORT
        "destination": destination,
        "vehicle": vehicle,
        "driver": driver,

        # RETAIL
        "shop_name": shop_name,
        "price": price,
        "expiry_date": expiry_date,

        # QR
        "qr": f"/static/qr/{qr_filename}"

    })

    # =================================================
    # REDIRECT
    # =================================================

    return RedirectResponse(

        url=f"/dashboard?user={updated_by}&role={user_role}",

        status_code=303
    )

# =====================================================
# USER TRACK PAGE
# =====================================================

@app.get("/user", response_class=HTMLResponse)
def user_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="user.html"
    )

# =====================================================
# RESULT PAGE
# =====================================================

@app.get("/result", response_class=HTMLResponse)
def result(

    request: Request,

    id: str

):

    trace_data = list(

        trace_col.find(

            {"batchId": id},

            {"_id": 0}

        )

    )

    return templates.TemplateResponse(

        request=request,

        name="result.html",

        context={

            "batch": id,

            "trace_data": trace_data

        }
    )

# =====================================================
# HEALTH CHECK
# =====================================================

@app.get("/health")
def health():

    return {

        "status": "running",

        "database": "connected"

    }
