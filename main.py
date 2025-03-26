from fastapi import FastAPI, HTTPException, Request,Cookie,Header,Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse,RedirectResponse,JSONResponse

from google.cloud import firestore
from models import DriverDeleteRequest
from fastapi import Query
import requests
from fastapi import Form
from pydantic import BaseModel
from config import db
from models import Driver, Team
import os

# Set Google Cloud Firestore Credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "web-app-3931e-de5fadd1ee07.json"

app = FastAPI()
db = firestore.Client()
API_KEY = "AIzaSyDAX-wXCsom37DNvktXAhjVcLjl9tWEebI"
FIREBASE_PROJECT_ID = "web-app-3931e"

# Simulated user session storage
fake_user_session = {"is_logged_in": False}  # Change this dynamically in real implementation

#  Mount static files for frontend (JS, CSS)
app.mount("/static", StaticFiles(directory="static"), name="static")

#  Setup Jinja2 templates
templates = Jinja2Templates(directory="templates")

class TokenRequest(BaseModel):
    idToken: str

# ---------------- Serve Pages ---------------- #
@app.get("/", response_class=RedirectResponse)
async def home_redirect():
    return RedirectResponse(url="/dashboard", status_code=302)

@app.post("/login")
async def login(request: Request):
    try:
        data = await request.json()
        print(" Received Login Request Data:", data)

        id_token = data.get("idToken")
        if not id_token:
            print(" No ID token received.")
            return JSONResponse(status_code=400, content={"detail": "ID token is required"})

        user = verify_firebase_token(id_token)
        if not user:
            print(" Invalid Firebase Token")
            return JSONResponse(status_code=401, content={"detail": "Invalid Firebase token"})

        response = RedirectResponse(url="/dashboard", status_code=303)
        response.set_cookie(key="token", value=id_token, httponly=True, max_age=3600)
        print("Login successful! Redirecting to dashboard.")
        return response
    except Exception as e:
        print(f"Login Error: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Internal Server Error: {str(e)}"})


#  Fix: Add a dedicated /login route
@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard_page(request: Request):
    id_token = request.cookies.get("token")
    user = None

    if id_token:
        user = verify_firebase_token(id_token)  

    return templates.TemplateResponse("dashboard.html", {"request": request, "user": user})

@app.get("/add-driver", response_class=HTMLResponse)
async def add_driver_page(request: Request, token: str = Cookie(None)):
    print(f"📝 Received token: {token}")  # Log token for debugging

    if not token:
        print(" No token found in cookies. Sending error response.")
        return Response(content="Unauthorized: Please log in.", status_code=401)

    user = verify_firebase_token(token)
    print("user data =",user)  # Log token for debugging
    if not user:
        print(" Invalid token. Sending error response.")
        return Response(content="Unauthorized: Invalid token.", status_code=401)

    print(f"User authenticated: {user['email']}")
    return templates.TemplateResponse("add_driver.html", {"request": request})

@app.post("/add-driver")
async def add_driver(request: Request, authorization: str = Header(None)):
    """Adds a new driver to Firestore if authenticated."""
    
    if not authorization or not authorization.startswith("Bearer "):
        print(" No Authorization header found.")
        raise HTTPException(status_code=401, detail="Unauthorized: No token provided.")

    id_token = authorization.split("Bearer ")[1]  # Extract token
    print("Received ID Token:", id_token)

    user = verify_firebase_token(id_token)
    if not user:
        print("Invalid Firebase Token")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token")

    try:
        data = await request.json()
        print("Received Driver Data:", data)

        # Ensure required fields are present
        required_fields = ["name", "age", "poles", "wins", "points", "titles", "fastestLaps", "team"]
        for field in required_fields:
            if field not in data:
                raise HTTPException(status_code=400, detail=f"Missing field: {field}")

        driver_ref = db.collection("drivers").document(data["name"])
        driver_ref.set({
            "name": data["name"],
            "age": int(data["age"]),
            "totalPolePositions": int(data["poles"]),
            "totalRaceWins": int(data["wins"]),
            "totalPointsScored": int(data["points"]),
            "totalWorldTitles": int(data["titles"]),
            "totalFastestLaps": int(data["fastestLaps"]),
            "team": data["team"]
        })

        print("Driver successfully added to Firestore.")
        return JSONResponse(status_code=200, content={"message": "Driver added successfully!"})

    except Exception as e:
        print(f"Error adding driver: {e}")
        return JSONResponse(status_code=500, content={"detail": f"Internal Server Error: {str(e)}"})

@app.get("/add-team", response_class=HTMLResponse)
async def add_team_page(request: Request):
    token = request.cookies.get("token")  # Explicitly get token from cookies

    print(f"Received token: {token}")  # Debugging log

    if not token:
        print(" No token found in cookies. Sending error response.")
        return RedirectResponse(url="/login")

    user = verify_firebase_token(token)
    if not user:
        print("Invalid token. Sending error response.")
        return RedirectResponse(url="/login")

    print(f"User authenticated: {user['email']}")
    return templates.TemplateResponse("add_team.html", {"request": request})

@app.post("/add-team")
async def add_team(request: Request, authorization: str = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Unauthorized: No token provided.")

    id_token = authorization.split("Bearer ")[1]
    user = verify_firebase_token(id_token)
    print(user, "user")
    if not user:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid token")

    data = await request.json()
    required_fields = ["name", "yearFounded", "totalPolePositions", "totalRaceWins", "totalConstructorTitles", "totalConstructorTitles"]
    for field in required_fields:
        if field not in data:
            raise HTTPException(status_code=400, detail=f"Missing field: {field}")

    db.collection("teams").document(data["name"]).set(data)
    return JSONResponse(status_code=200, content={"message": "Team added successfully!"})

@app.get("/query-drivers", response_class=HTMLResponse)
async def query_drivers_page(request: Request):
    return templates.TemplateResponse("query_drivers.html", {"request": request})

@app.get("/query-teams", response_class=HTMLResponse)
async def query_teams_page(request: Request):
    return templates.TemplateResponse("query_teams.html", {"request": request})

@app.get("/get-driver-data")
async def get_driver_data(request: Request, name: str):
    driver_ref = db.collection("drivers").document(name).get()
    
    if not driver_ref.exists:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    driver_data = driver_ref.to_dict()
    
    # If request is from Fetch API or AJAX, return JSON
    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return JSONResponse(content=driver_data)  
    
    #  If request is from direct URL, return the template
    return templates.TemplateResponse("edit-driver.html", {
        "request": request,
        "driver": driver_data,
        "name": name
    })

@app.post("/update-driver")
async def update_driver(
    name: str = Form(...),
    age: int = Form(0),  
    totalFastestLaps: int = Form(0),
    totalPointsScored: int = Form(0),
    totalPolePositions: int = Form(0),
    totalRaceWins: int = Form(0),
    totalWorldTitles: int = Form(0),
    team: str = Form(...)
):
    if not name or not team:
        raise HTTPException(status_code=400, detail="Name and team are required fields.")

    driver_ref = db.collection("drivers").document(name)
    driver_doc = driver_ref.get()

    if not driver_doc.exists:
        raise HTTPException(status_code=404, detail="Driver not found")

    # Perform update in a single operation
    update_data = {
    "age": age,
    "totalFastestLaps": totalFastestLaps,
    "totalPointsScored": totalPointsScored,
    "totalPolePositions": totalPolePositions,
    "totalRaceWins": totalRaceWins,
    "totalWorldTitles": totalWorldTitles,
    "team": team,
    # Remove only necessary unwanted fields
    "previousSeasonPosition": firestore.DELETE_FIELD,
    "totalConstructorTitles": firestore.DELETE_FIELD,
    "yearFounded": firestore.DELETE_FIELD
}


    driver_ref.update(update_data)

    return {"success": True, "message": "Driver updated successfully, unwanted fields removed"}

@app.get("/driver_details")
async def driver_details(request: Request, id: str):
    return templates.TemplateResponse("driver_details.html", {"request": request, "driver_id": id})

@app.get("/get-driver/{driver_id}")
async def get_driver(driver_id: str):
    driver_ref = db.collection("drivers").document(driver_id).get()
    
    if not driver_ref.exists:
        raise HTTPException(status_code=404, detail="Driver not found")
    
    return driver_ref.to_dict()


@app.get("/compare_drivers")
async def compare_drivers(request: Request, driver1: str, driver2: str):
    # Check if both driver1 and driver2 are provided
    if not driver1 or not driver2:
        raise HTTPException(status_code=400, detail="Both driver1 and driver2 parameters must be provided.")

    # Fetch data for driver1
    driver1_ref = db.collection("drivers").document(driver1)
    driver1_doc = driver1_ref.get()

    # Fetch data for driver2
    driver2_ref = db.collection("drivers").document(driver2)
    driver2_doc = driver2_ref.get()

    # Check if both drivers exist in the Firestore database
    if not driver1_doc.exists or not driver2_doc.exists:
        raise HTTPException(status_code=404, detail="One or both drivers not found")

     # Extract the data
    driver1_data = driver1_doc.to_dict()
    driver2_data = driver2_doc.to_dict()

    # Add Firestore document IDs explicitly
    driver1_data["id"] = driver1_doc.id
    driver2_data["id"] = driver2_doc.id
    
    # Return the comparison page with the driver data
    return templates.TemplateResponse("compare_drivers.html", {
        "request": request,
        "driver1": driver1_data,
        "driver2": driver2_data
    })

# ---------------- Fetch All Drivers ---------------- #
@app.get("/get-all-drivers")
async def get_all_drivers():
    drivers_ref = db.collection("drivers").stream()
    drivers = [{"name": doc.id, **doc.to_dict()} for doc in drivers_ref]
    return {"drivers": drivers}  


@app.get("/get-team-data", response_class=HTMLResponse)
async def update_team_page(request: Request, name: str):
    if not name:
        raise HTTPException(status_code=400, detail="Team name is required")
    
    team_ref = db.collection("teams").document(name).get()
    if not team_ref.exists:
        raise HTTPException(status_code=404, detail="Team not found")
    
    team_data = team_ref.to_dict()
    return templates.TemplateResponse("edit-team.html", {"request": request, "team": team_data, "name": name})



@app.post("/update-team")
async def update_team(
    name: str = Form(...),
    yearFounded: int = Form(0),
    totalRaceWins: int = Form(0),
    totalConstructorTitles: int = Form(0),
    totalPolePositions: int = Form(0),
    finishingPositionLastSeason: int = Form(0)
):
    if not name:
        raise HTTPException(status_code=400, detail="Team name is required.")

    team_ref = db.collection("teams").document(name)
    team_doc = team_ref.get()

    if not team_doc.exists:
        raise HTTPException(status_code=404, detail="Team not found")

    # Perform update in a single operation
    update_data = {
        "yearFounded": yearFounded,
        "totalRaceWins": totalRaceWins,
        "totalConstructorTitles": totalConstructorTitles,
        "totalPolePositions": totalPolePositions,
        "finishingPositionLastSeason": finishingPositionLastSeason,
        # Remove only necessary unwanted fields
        "fastestLaps": firestore.DELETE_FIELD,
        "pointsScored": firestore.DELETE_FIELD,
        "polePositions": firestore.DELETE_FIELD,
        "raceWins": firestore.DELETE_FIELD,
        "worldTitles": firestore.DELETE_FIELD
    }

    team_ref.update(update_data)

    return {"success": True, "message": "Team updated successfully, unwanted fields removed"}

@app.get("/compare_teams")
async def compare_teams(request: Request, team1: str, team2: str):
    if not team1 or not team2:
        raise HTTPException(status_code=400, detail="Both team1 and team2 parameters must be provided.")
    
    team1_ref = db.collection("teams").document(team1)
    team1_doc = team1_ref.get()
    
    team2_ref = db.collection("teams").document(team2)
    team2_doc = team2_ref.get()
    
    if not team1_doc.exists or not team2_doc.exists:
        raise HTTPException(status_code=404, detail="One or both teams not found")
    
    team1_data = team1_doc.to_dict()
    team2_data = team2_doc.to_dict()
    
    team1_data["id"] = team1_doc.id
    team2_data["id"] = team2_doc.id
    
    return templates.TemplateResponse("compare_teams.html", {
        "request": request,
        "team1": team1_data,
        "team2": team2_data
    })

@app.get("/team_details", response_class=HTMLResponse)
async def team_details(request: Request, id: str):
    return templates.TemplateResponse("team_details.html", {"request": request, "team_id": id})

@app.get("/get-teams-data", response_class=JSONResponse)
async def get_teams_data(request: Request, id: str = Query(..., alias="id")):
    """Fetch team details from Firestore using team ID"""

    #  Debugging: Log the full request
    print(f"Received request: {request.query_params}")

    if not id:  
        return JSONResponse(status_code=400, content={"detail": "Missing team ID"})

    team_ref = db.collection("teams").document(id).get()

    if not team_ref.exists:
        return JSONResponse(status_code=404, content={"detail": "Team not found"})

    team_data = team_ref.to_dict()
    team_data["id"] = id  # Ensure the ID is included

    return JSONResponse(content=team_data)

# ---------------- Fetch All Teams ---------------- #
@app.get("/get-all-teams")
async def get_all_teams():
    try:
        teams_ref = db.collection("teams").stream()
        teams = [{"id": doc.id, **doc.to_dict()} for doc in teams_ref]
        return {"teams": teams}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching teams: {str(e)}")
    
    
# ---------------- Fetch All Teams ---------------- #
@app.get("/get-all-teams")
async def get_all_teams():
    teams_ref = db.collection("teams").stream()
    teams = [{"name": doc.id, **doc.to_dict()} for doc in teams_ref]
    return {"teams": teams}


# ---------------- Query Drivers API ---------------- #
@app.get("/query-drivers-results")
async def query_drivers(attribute: str, comparison: str, value: int):
    drivers_ref = db.collection("drivers")

    # Define Firestore query
    if comparison == "lt":
        query_ref = drivers_ref.where(attribute, "<", value)
    elif comparison == "gt":
        query_ref = drivers_ref.where(attribute, ">", value)
    elif comparison == "eq":
        query_ref = drivers_ref.where(attribute, "==", value)
    else:
        raise HTTPException(status_code=400, detail="Invalid comparison operator")

    # Fetch results
    query_snapshot = query_ref.stream()
    drivers = [{"name": doc.id, **doc.to_dict()} for doc in query_snapshot]

    return {"drivers": drivers}

# ---------------- Query Teams API ---------------- #
@app.get("/query-teams-results")
async def query_teams(attribute: str, comparison: str, value: int):
    teams_ref = db.collection("teams")

    # Define Firestore query
    if comparison == "lt":
        query_ref = teams_ref.where(attribute, "<", value)
    elif comparison == "gt":
        query_ref = teams_ref.where(attribute, ">", value)
    elif comparison == "eq":
        query_ref = teams_ref.where(attribute, "==", value)
    else:
        raise HTTPException(status_code=400, detail="Invalid comparison operator")

    # Fetch results
    query_snapshot = query_ref.stream()
    teams = [{"name": doc.id, **doc.to_dict()} for doc in query_snapshot]

    return {"teams": teams}

# DELETE Driver API
@app.post("/delete-driver")
async def delete_driver(request: DriverDeleteRequest):
    driver_ref = db.collection("drivers").document(request.name)  # Assuming name is the document ID
    driver = driver_ref.get()

    if not driver.exists:
        raise HTTPException(status_code=404, detail="Driver not found.")

    driver_ref.delete()
    return {"success": True, "message": f"Driver {request.name} deleted successfully."}


# DELETE Team API
@app.delete("/delete-team")
async def delete_team(id: str = Query(..., description="Team ID to delete")):
    try:
        team_ref = db.collection("teams").document(id)
        team_doc = team_ref.get()

        if not team_doc.exists:
            raise HTTPException(status_code=404, detail="Team not found.")

        team_ref.delete()
        return {"success": True, "message": f"Team {id} deleted successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")

def verify_firebase_token(id_token):

    try:
        url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={API_KEY}"
        response = requests.post(url, json={"idToken": id_token})  #CORRECT! Use requests.post()
        data = response.json()
        
        if "users" in data:
            print("Token verified successfully:", data["users"][0]["email"])
            return data["users"][0]  # Return user data if valid token
        print(" Invalid token received:", data)
        return None
    except Exception as e:
        print(f" Token verification failed: {e}")
        return None