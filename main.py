import time
from pathlib import Path
from typing import Dict, List, Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

MATCH_DURATION = 60
PREDICTION_WINDOW = 3

state = {
    "match_started": False,
    "match_start_time": None,
    "match_duration": MATCH_DURATION,
    "events": [
        {"id": 1, "time": 12, "type": "Гол"},
        {"id": 2, "time": 27, "type": "Опасный удар"},
        {"id": 3, "time": 44, "type": "Киберспорт: ключевой фраг"},
    ],
    "processed_event_ids": [],
    "feed": [],
    "scores": {},
    "predictions": {},
}


def reset_match():
    state["match_started"] = False
    state["match_start_time"] = None
    state["processed_event_ids"] = []
    state["feed"] = []
    state["scores"] = {}
    state["predictions"] = {}


def get_match_time() -> int:
    if not state["match_started"] or state["match_start_time"] is None:
        return 0

    elapsed = int(time.time() - state["match_start_time"])
    if elapsed > state["match_duration"]:
        elapsed = state["match_duration"]
    return elapsed


def add_feed_message(message: str):
    state["feed"].insert(0, message)
    state["feed"] = state["feed"][:20]


def process_events():
    if not state["match_started"]:
        return

    now_time = get_match_time()

    for event in state["events"]:
        if event["id"] in state["processed_event_ids"]:
            continue

        if now_time >= event["time"]:
            state["processed_event_ids"].append(event["id"])

            add_feed_message(
                f"⚽ Событие произошло: {event['type']} ({event['time']} сек)"
            )

            for username, prediction_time in list(state["predictions"].items()):
                delta = event["time"] - prediction_time

                if 0 <= delta <= PREDICTION_WINDOW:
                    points = 10 + (PREDICTION_WINDOW - delta)
                    state["scores"][username] = state["scores"].get(username, 0) + points
                    add_feed_message(
                        f"✅ {username} угадал момент события и получил {points} очков"
                    )
                else:
                    add_feed_message(
                        f"❌ {username} не угадал момент события"
                    )

            state["predictions"] = {}

    if now_time >= state["match_duration"] and state["match_started"]:
        state["match_started"] = False
        add_feed_message("🏁 Демо-матч завершен")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )


@app.post("/api/start")
async def start_match():
    reset_match()
    state["match_started"] = True
    state["match_start_time"] = time.time()
    add_feed_message("▶️ Демо-матч начался")
    return {"status": "ok"}


@app.post("/api/join")
async def join(payload: Dict):
    username = str(payload.get("username", "")).strip()

    if not username:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Введите ник"},
        )

    if username not in state["scores"]:
        state["scores"][username] = 0

    add_feed_message(f"👤 Игрок {username} присоединился")
    return {"status": "ok", "username": username}


@app.post("/api/predict")
async def predict(payload: Dict):
    username = str(payload.get("username", "")).strip()

    if not username:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Введите ник"},
        )

    if not state["match_started"]:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Матч еще не начался"},
        )

    current_time = get_match_time()

    if current_time >= state["match_duration"]:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Матч уже завершен"},
        )

    if username not in state["scores"]:
        state["scores"][username] = 0

    state["predictions"][username] = current_time
    add_feed_message(
        f"⏳ {username} сделал прогноз на {current_time} сек: событие произойдет в ближайшие {PREDICTION_WINDOW} сек"
    )

    return {"status": "ok"}


@app.get("/api/state")
async def get_state():
    process_events()

    current_time = get_match_time()

    leaderboard = [
        {"username": username, "score": score}
        for username, score in sorted(
            state["scores"].items(),
            key=lambda item: item[1],
            reverse=True,
        )
    ]

    next_event: Optional[Dict] = None
    for event in state["events"]:
        if event["id"] not in state["processed_event_ids"]:
            next_event = {"time": event["time"]}
            break

    return {
        "match_started": state["match_started"],
        "current_time": current_time,
        "match_duration": state["match_duration"],
        "feed": state["feed"],
        "leaderboard": leaderboard,
        "next_event_hint": next_event,
        "prediction_window": PREDICTION_WINDOW,
    }