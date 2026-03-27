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

    for (const item of data.feed) {
        const li = document.createElement("li");
        li.innerText = item;
        feed.appendChild(li);
    }

    const leaderboard = document.getElementById("leaderboard");
    leaderboard.innerHTML = "";

    if (data.leaderboard.length === 0) {
        const li = document.createElement("li");
        li.innerText = "Пока нет очков";
        leaderboard.appendChild(li);
    } else {
        for (const player of data.leaderboard) {
            const li = document.createElement("li");
            li.innerText = `${player.username}: ${player.score}`;
            leaderboard.appendChild(li);
        }
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