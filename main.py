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

def load_data():
    global cache_data
    url = ("https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query="
        "select+pl_name,sy_dist,discoverymethod,pl_bmasse,pl_rade,"
        "pl_orbper,hostname+from+ps&format=json")
    response = requests.get(url)
    cache_data = response.json()

load_data()

@app.get("/")
def home():
    return {"message": "Space backend is running"}

@app.get("/search")
def search(name: str = None):
    results = cache_data
    if name:
        results = [obj for obj in results if name.lower() in obj["pl_name"].lower()]
    return results

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

            obj["description"] = make_description(obj)

            # Add external reference links
            obj["links"] = [
                f"https://exoplanetarchive.ipac.caltech.edu/overview/{obj.get('pl_name')}",
                f"https://en.wikipedia.org/wiki/{obj.get('pl_name').replace(' ', '_')}"
            ]

            return obj

    return {"error": "Object not found"}