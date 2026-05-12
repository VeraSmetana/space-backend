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
def load_simbad_stars():
    url = "https://simbad.u-strasbg.fr/simbad/sim-tap/sync"

    query = """
    SELECT TOP 5 main_id, ra, dec
    FROM basic
    """

    params = {
        "query": query,
        "format": "json"
    }

    response = requests.get(url, params=params)

    print("SIMBAD STATUS:", response.status_code)
    print("SIMBAD RAW:", response.text[:1000])

    return []

# -----------------------------
# GALAXIES (NED)
# -----------------------------
import csv
from io import StringIO

def load_galaxies():
    url = "https://ned.ipac.caltech.edu/tap/sync"

    query = """
    SELECT TOP 20
        objname,
        z,
        ra,
        dec
    FROM NEDTAP
    WHERE z IS NOT NULL
    """

    params = {
        "query": query,
        "format": "csv"
    }

    response = requests.get(url, params=params)

    print("NED STATUS:", response.status_code)
    print("NED RAW (first 300 chars):", response.text[:300])

    if response.status_code != 200:
        return []

    try:
        f = StringIO(response.text)
        reader = csv.reader(f)

        rows = list(reader)

        # skip header row if it exists
        if rows and "objname" in rows[0][0].lower():
            rows = rows[1:]

        galaxies = []

        for row in rows:
            if len(row) < 4:
                continue

            galaxies.append({
                "id": f"gal_{row[0].replace(' ', '_')}",
                "name": row[0],
                "type": "galaxy",
                "redshift": row[1],
                "ra": row[2],
                "dec": row[3],
                "description": "Galaxy from NED database"
            })

        return galaxies

    except Exception as e:
        print("NED parsing error:", e)
        return []


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

    planets = []

    for p in planets_raw:
        planets.append({
            "id": f"exo_{p.get('pl_name', '').replace(' ', '_')}",
            "name": p.get("pl_name"),
            "type": "exoplanet",
            "distance": p.get("sy_dist"),
            "mass": p.get("pl_bmasse"),
            "radius": p.get("pl_rade"),
            "discoverymethod": p.get("discoverymethod"),
            "hostname": p.get("hostname"),
            "description": None
        })

    stars = load_simbad_stars()
    galaxies = load_galaxies()

    all_objects = planets + stars + galaxies

    cache_data.clear()

    for obj in all_objects:
        if obj.get("id"):
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
def search(name: str = None, type: str = None, distance: float = None):

    results = list(cache_data.values())

    if name:
        results = [
            obj for obj in results
            if name.lower() in (obj.get("name") or "").lower()
        ]

    if type:
        results = [
            obj for obj in results
            if obj.get("type") == type
        ]

    if distance:
        results = [
            obj for obj in results
            if obj.get("distance") is not None
            and obj["distance"] <= float(distance)
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