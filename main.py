from fastapi.middleware.cors import CORSMiddleware
    
from fastapi import FastAPI

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

import requests

cache_data = []

def load_data(): 
    global cache_data
    url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+top+50+pl_name,sy_dist,discoverymethod+from+ps&format=json"
    response = requests.get(url)
    cache_data = response.json()

@app.get("/")
def home():
    return {"message": "Space backend is running"}
space_objects = [
    {
        "name": "Proxima Centauri",
        "type": "star",
        "distance": 4.24,
        "description": "Nearest known star to the Sun.",
        "id": "proxima-centauri"
    },
    {
        "name": "Andromeda Galaxy",
        "type": "galaxy",
        "distance": 2537000,
        "description": "Nearest major galaxy to the Milky Way.",
        "id": "andromeda-galaxy"
    }
]

load_data()

@app.get("/search")
def search(type: str = None, distance: float = None, discoverymethod: str = None, id: str = None, name: str = None):
    results = cache_data

    if name:
        results = [obj for obj in results if name.lower() in obj["pl_name"].lower()]

    if type:
        results = [obj for obj in results if obj.get("type") == type]

    if distance:
        results = [obj for obj in results if obj["sy_dist"] <= distance]

    if discoverymethod:
        results = [obj for obj in results if obj.get("discoverymethod") == discoverymethod]

    if id:
        results = [obj for obj in results if obj.get("id") == id]

    return results
print(cache_data[:3])

@app.get("/object")
def get_object(id: str):
    for obj in cache_data:
        if obj.get("id") == id:
            return obj
    return {"error": "Object not found"}
