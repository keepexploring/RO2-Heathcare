from fastapi import FastAPI
from mqtt_handler import start_mqtt
import asyncio

app = FastAPI(title="Sensor Backend")

@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    loop.create_task(start_mqtt())

@app.get("/ping")
async def ping():
    return {"msg": "pong"}
