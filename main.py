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
    url = "https://exoplanetarchive.ipac.caltech.edu/TAP/sync?query=select+top+50+pl_name,sy_dist,discoverymethod+from+ps&format=json"
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

@app.get("/object")
def get_object(name: str):
    for obj in cache_data:
        if obj.get("pl_name") == name:
            return obj
    return {"error": "Object not found"}