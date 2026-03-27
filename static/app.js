let currentUser = "";

async function api(url, method = "GET", body = null) {
    const options = { method };

    if (body !== null) {
        options.headers = { "Content-Type": "application/json" };
        options.body = JSON.stringify(body);
    }

    const response = await fetch(url, options);
    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.message || "Ошибка запроса");
    }

    return data;
}

function renderState(data) {
    document.getElementById("currentUser").innerText = currentUser || "—";
    document.getElementById("matchStatus").innerText = data.match_started ? "идет" : "не идет";
    document.getElementById("timer").innerText = `${data.current_time} / ${data.match_duration} сек`;
    document.getElementById("windowInfo").innerText = `${data.prediction_window} сек`;

    const feed = document.getElementById("feed");
    feed.innerHTML = "";

    if (data.feed.length === 0) {
        const li = document.createElement("li");
        li.innerText = "Пока событий нет";
        feed.appendChild(li);
    } else {
        for (const item of data.feed) {
            const li = document.createElement("li");
            li.innerText = item;
            feed.appendChild(li);
        }
    }

    const leaderboard = document.getElementById("leaderboard");
    leaderboard.innerHTML = "";

    if (data.leaderboard.length === 0) {
        const li = document.createElement("li");
        li.innerText = "Очков пока нет";
        leaderboard.appendChild(li);
    } else {
        data.leaderboard.forEach((player, index) => {
            const li = document.createElement("li");
            li.innerHTML = `<span>#${index + 1} ${player.username}</span><strong>${player.score}</strong>`;
            leaderboard.appendChild(li);
        });
    }

    const usersList = document.getElementById("onlineUsers");
    usersList.innerHTML = "";

    if (data.online_users.length === 0) {
        const li = document.createElement("li");
        li.innerText = "Никто не подключен";
        usersList.appendChild(li);
    } else {
        data.online_users.forEach(user => {
            const li = document.createElement("li");
            li.innerText = `🟢 ${user}`;
            usersList.appendChild(li);
        });
    }

    const nextEventCard = document.getElementById("nextEventCard");
    if (data.next_event_hint) {
        const secondsLeft = Math.max(0, data.next_event_hint.time - data.current_time);
        nextEventCard.innerHTML = `
            <div class="next-event-type">${data.next_event_hint.type}</div>
            <div class="next-event-time">Ожидается примерно через ${secondsLeft} сек</div>
            <div class="next-event-sub">Пытайся нажать кнопку прогноза заранее</div>
        `;
    } else {
        nextEventCard.innerHTML = `
            <div class="next-event-type">Все события завершены</div>
            <div class="next-event-time">Дождись нового матча</div>
        `;
    }
}

async function refreshState() {
    try {
        const data = await api("/api/state");
        renderState(data);
    } catch (error) {
        console.error(error);
    }
}

document.getElementById("joinBtn").addEventListener("click", async () => {
    const username = document.getElementById("username").value.trim();

    if (!username) {
        alert("Введите ник");
        return;
    }

    try {
        await api("/api/join", "POST", { username });
        currentUser = username;
        await refreshState();
    } catch (error) {
        alert(error.message);
    }
});

document.getElementById("startBtn").addEventListener("click", async () => {
    try {
        await api("/api/start", "POST");
        await refreshState();
    } catch (error) {
        alert(error.message);
    }
});

document.getElementById("predictBtn").addEventListener("click", async () => {
    if (!currentUser) {
        alert("Сначала войдите по нику");
        return;
    }

    try {
        await api("/api/predict", "POST", { username: currentUser });
        await refreshState();
    } catch (error) {
        alert(error.message);
    }
});

refreshState();
setInterval(refreshState, 1000);