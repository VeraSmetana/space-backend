from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

cache_data = []

import urllib.parse

def load_simbad_stars():
    query = """
    SELECT main_id, ra, dec, otype
    FROM basic
    WHERE otype = 'Star'
    LIMIT 50
    """

    url = "https://simbad.u-strasbg.fr/simbad/sim-tap/sync"
    params = {
        "query": query,
        "format": "json"
    }

    full_url = url + "?" + urllib.parse.urlencode(params)

    response = requests.get(full_url)
    data = response.json()

    stars = []

    for row in data.get("data", []):
        stars.append({
            "name": row[0],
            "type": "star",
            "ra": row[1],
            "dec": row[2],
            "description": "Star from SIMBAD catalog"
        })

    return stars

def load_data():
    global cache_data

    # NASA exoplanets
    url = (
        "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query="
        "select+pl_name,sy_dist,discoverymethod,pl_bmasse,pl_rade,"
        "pl_orbper,hostname+from+ps&format=json"
    )

    response = requests.get(url)
    planets = response.json()

    planets = [
        {
            "name": p.get("pl_name"),
            "type": "exoplanet",
            "distance": p.get("sy_dist"),
            "mass": p.get("pl_bmasse"),
            "radius": p.get("pl_rade"),
            "discoverymethod": p.get("discoverymethod"),
            "hostname": p.get("hostname"),
            "description": None
        }
        for p in planets
    ]

    stars = load_simbad_stars()

    cache_data = planets + stars

def normalize_object(obj):
    return {
        "name": obj.get("name") or obj.get("pl_name"),
        "type": obj.get("type", "exoplanet"),
        "distance": obj.get("distance") or obj.get("sy_dist"),
        "mass": obj.get("mass") or obj.get("pl_bmasse"),
        "radius": obj.get("radius") or obj.get("pl_rade"),
        "discoverymethod": obj.get("discoverymethod"),
        "hostname": obj.get("hostname"),
        "description": obj.get("description", ""),
    }

@app.get("/")
def home():
    return {"message": "Space backend is running"}

@app.get("/search")
def search(name: str = None, type: str = None, distance: float = None):

    results = cache_data

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

def get_type(obj):
    name = obj.get("pl_name", "").lower()

    # basic rules (you can improve later)
    if "galaxy" in name:
        return "galaxy"
    elif "sun" in name or "star" in name or "centauri" in name:
        return "star"
    else:
        return "exoplanet"

def make_description(obj):
    name = obj.get("pl_name", "This planet")
    star = obj.get("hostname", "its star")
    dist = obj.get("sy_dist")
    mass = obj.get("pl_bmasse")

    text = f"{name} orbits the star {star}. "

    if dist:
        text += f"It is about {dist} light-years away from Earth. "

    if mass:
        if mass < 2:
            text += "It is likely a rocky, Earth-like planet. "
        elif mass < 10:
            text += "It is a super-Earth larger than Earth. "
        else:
            text += "It is a gas giant similar to Jupiter. "

    return text

@app.get("/object")
def get_object(name: str):
    for obj in cache_data:
        if obj.get("pl_name") == name:

            obj["type"] = get_type(obj)
            obj["description"] = make_description(obj)

            # Add external reference links
            obj["links"] = [
                f"https://exoplanetarchive.ipac.caltech.edu/overview/{obj.get('pl_name')}",
                f"https://en.wikipedia.org/wiki/{obj.get('pl_name').replace(' ', '_')}"
            ]

            return obj

    return {"error": "Object not found"}