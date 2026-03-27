import time
from pathlib import Path
from typing import Dict, Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent

app = FastAPI()

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

MATCH_DURATION = 120
PREDICTION_WINDOW = 3
POST_MATCH_RESET_DELAY = 5

state = {
    "match_started": False,
    "match_start_time": None,
    "match_duration": MATCH_DURATION,
    "events": [
        {"id": 1, "time": 10, "type": "Гол"},
        {"id": 2, "time": 25, "type": "Опасный удар"},
        {"id": 3, "time": 40, "type": "Фол"},
        {"id": 4, "time": 60, "type": "Контратака"},
        {"id": 5, "time": 80, "type": "Киберспорт: ключевой фраг"},
        {"id": 6, "time": 100, "type": "Решающий момент"},
    ],
    "processed_event_ids": [],
    "feed": [],
    "scores": {},
    "predictions": {},
    "online_users": [],
    "match_finished_at": None,
}


def full_reset():
    state["match_started"] = False
    state["match_start_time"] = None
    state["processed_event_ids"] = []
    state["feed"] = []
    state["scores"] = {}
    state["predictions"] = {}
    state["online_users"] = []
    state["match_finished_at"] = None


def reset_for_new_match():
    state["match_started"] = False
    state["match_start_time"] = None
    state["processed_event_ids"] = []
    state["feed"] = []
    state["scores"] = {}
    state["predictions"] = {}
    state["online_users"] = []
    state["match_finished_at"] = None


def get_match_time() -> int:
    if not state["match_started"] or state["match_start_time"] is None:
        return 0

    elapsed = int(time.time() - state["match_start_time"])
    if elapsed > state["match_duration"]:
        elapsed = state["match_duration"]
    return elapsed


def add_feed_message(message: str):
    state["feed"].insert(0, message)
    state["feed"] = state["feed"][:30]


def maybe_reset_finished_match():
    if state["match_finished_at"] is None:
        return

    if time.time() - state["match_finished_at"] >= POST_MATCH_RESET_DELAY:
        full_reset()


def process_events():
    maybe_reset_finished_match()

    if not state["match_started"]:
        return

    now_time = get_match_time()

    for event in state["events"]:
        if event["id"] in state["processed_event_ids"]:
            continue

        if now_time >= event["time"]:
            state["processed_event_ids"].append(event["id"])

            add_feed_message(f"📡 Событие: {event['type']} ({event['time']} сек)")

            for username, prediction_time in list(state["predictions"].items()):
                delta = event["time"] - prediction_time

                if 0 <= delta <= PREDICTION_WINDOW:
                    points = 10 + (PREDICTION_WINDOW - delta)
                    state["scores"][username] = state["scores"].get(username, 0) + points
                    add_feed_message(
                        f"✅ {username} точно предсказал событие и получил {points} очков"
                    )
                else:
                    add_feed_message(f"❌ {username} не попал по времени")

            state["predictions"] = {}

    if now_time >= state["match_duration"] and state["match_started"]:
        state["match_started"] = False
        state["match_finished_at"] = time.time()
        add_feed_message("🏁 Матч завершён")
        add_feed_message("♻️ Данные будут очищены через 5 секунд")


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={"request": request},
    )


@app.post("/api/start")
async def start_match():
    reset_for_new_match()
    state["match_started"] = True
    state["match_start_time"] = time.time()
    add_feed_message("▶️ Матч начался")
    return {"status": "ok"}


@app.post("/api/join")
async def join(payload: Dict):
    maybe_reset_finished_match()

    username = str(payload.get("username", "")).strip()

    if not username:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Введите ник"},
        )

    if username not in state["scores"]:
        state["scores"][username] = 0

    if username not in state["online_users"]:
        state["online_users"].append(username)

    add_feed_message(f"👤 {username} подключился к матчу")

    return {"status": "ok", "username": username}


@app.post("/api/predict")
async def predict(payload: Dict):
    maybe_reset_finished_match()

    username = str(payload.get("username", "")).strip()

    if not username:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Введите ник"},
        )

    if not state["match_started"]:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Матч ещё не начался"},
        )

    current_time = get_match_time()

    if current_time >= state["match_duration"]:
        return JSONResponse(
            status_code=400,
            content={"status": "error", "message": "Матч уже завершён"},
        )

    if username not in state["scores"]:
        state["scores"][username] = 0

    if username not in state["online_users"]:
        state["online_users"].append(username)

    state["predictions"][username] = current_time
    add_feed_message(f"⏳ {username} сделал прогноз на {current_time} сек")

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
            next_event = {"time": event["time"], "type": event["type"]}
            break

    return {
        "match_started": state["match_started"],
        "current_time": current_time,
        "match_duration": state["match_duration"],
        "feed": state["feed"],
        "leaderboard": leaderboard,
        "next_event_hint": next_event,
        "prediction_window": PREDICTION_WINDOW,
        "online_users": state["online_users"],
    }