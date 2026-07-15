from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests
import urllib.parse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

cache_data = {}


# -----------------------------
# SIMBAD STARS
# -----------------------------
def search_simbad(name):
    if not name:
        return []

    url = "https://simbad.cds.unistra.fr/simbad/sim-id"

    params = {
        "Ident": name,
        "output.format": "json"
    }

    response = requests.get(url, params=params)

    print("SIMBAD STATUS:", response.status_code)

    if response.status_code != 200:
        return []

    try:
        data = response.json()
    except Exception:
        print(response.text[:500])
        return []

    try:
        main_id = data["data"]["main_id"]
    except Exception:
        return []

    return [{
        "id": f"star_{main_id.replace(' ', '_')}",
        "name": main_id,
        "type": "star",
        "distance": None,
        "description": "Star from SIMBAD"
    }]
# -----------------------------
# GALAXIES (NED)
# -----------------------------
def search_ned(name):
    if not name:
        return []

    url = "https://ned.ipac.caltech.edu/srs/ObjectLookup"

    params = {
        "name": name
    }

    response = requests.get(url, params=params)

    print("NED STATUS:", response.status_code)
    print("NED RESPONSE:", response.text[:300])

    if response.status_code != 200:
        return []

    try:
        data = response.json()
    except Exception:
        return []

    preferred = data.get("Preferred")

    if not preferred:
        return []

    return [{
        "id": f"gal_{preferred.get('Name','unknown').replace(' ', '_')}",
        "name": preferred.get("Name"),
        "type": "galaxy",
        "distance": None,
        "description": "Galaxy from NASA/IPAC NED"
    }]

# -----------------------------
# LOAD ALL DATA
# -----------------------------
def load_data():
    global cache_data

    url = (
        "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query="
        "select+pl_name,sy_dist,discoverymethod,pl_bmasse,pl_rade,"
        "pl_orbper,hostname+from+ps&format=json"
    )

    response = requests.get(url)

    if response.status_code != 200:
        planets_raw = []
    else:
        try:
            planets_raw = response.json()
        except Exception:
            planets_raw = []

    cache_data.clear()

    for p in planets_raw:
        obj = {
            "id": f"exo_{p.get('pl_name', '').replace(' ', '_')}",
            "name": p.get("pl_name"),
            "type": "exoplanet",
            "distance": p.get("sy_dist"),
            "mass": p.get("pl_bmasse"),
            "radius": p.get("pl_rade"),
            "discoverymethod": p.get("discoverymethod"),
            "hostname": p.get("hostname"),
            "description": None
        }

        cache_data[obj["id"]] = obj


# -----------------------------
# ROOT
# -----------------------------
@app.get("/")
def home():
    return {"message": "Space backend is running"}


# -----------------------------
# SEARCH
# -----------------------------
@app.get("/search")
def search(name: str = "", type: str = "", distance: float = None):

    type = type.lower()

    if type == "star":
        return search_simbad(name)

    if type == "galaxy":
        return search_ned(name)

    results = list(cache_data.values())

    if type == "exoplanet":
        results = [
            obj for obj in results
            if obj.get("type") == "exoplanet"
        ]

    if name:
        results = [
            obj for obj in results
            if name.lower() in obj.get("name","").lower()
        ]

    return results


# -----------------------------
# DESCRIPTION
# -----------------------------
def make_description(obj):

    name = obj.get("name") or obj.get("pl_name") or "Unknown object"
    obj_type = obj.get("type", "unknown")

    dist = obj.get("distance") or obj.get("sy_dist")
    mass = obj.get("mass") or obj.get("pl_bmasse")

    text = f"{name} is a {obj_type}. "

    if dist:
        text += f"It is about {dist} light-years away. "

    if obj_type == "exoplanet" and mass:
        if mass < 2:
            text += "It is likely a rocky Earth-like planet. "
        elif mass < 10:
            text += "It is a super-Earth. "
        else:
            text += "It is a gas giant. "

    return text


# -----------------------------
# SINGLE OBJECT
# -----------------------------
@app.get("/object")
def get_object(id: str):
    obj = cache_data.get(id)

    if not obj:
        return {"error": "Object not found"}

    obj["description"] = make_description(obj)

    obj_name = obj.get("name", "Unknown")

    obj["links"] = [
        f"https://en.wikipedia.org/wiki/{obj_name.replace(' ', '_')}"
    ]

    return obj


# -----------------------------
# STARTUP
# -----------------------------
@app.on_event("startup")
def startup_event():
    load_data()