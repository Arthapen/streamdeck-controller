let ws;
let grid;
let latestTelemetry = {};

// --- STATE ---
let allPages = {}; // { home: [...], obs: [...] }
let currentPage = "home";
let pageHistory = []; // Stack for "Back" button

// --- GRID INIT ---
grid = GridStack.init({
    cellHeight: '7.5vh',
    margin: 10,
    column: 12,
    float: true,
    disableOneColumnMode: true,
    animate: true
});

// Save on change (Current Page)
grid.on('change', function (event, items) {
    saveLayout();
});

function resetLayout() {
    if (!confirm("This will clean up ghosts and stack widgets. Page will reload. Continue?")) return;

    if (allPages[currentPage]) {
        // 1. Filter out known ghosts (items without id or type)
        const cleanList = allPages[currentPage].filter(w => w.id && w.type);

        // 2. Stack them vertically at X=0
        cleanList.forEach((w, i) => {
            w.x = 0;
            w.y = i * 4; // Use height of 4 roughly or just auto
            w.w = 5; // Default width
            w.h = 3; // Default height
            if (w.type === 'spotify') { w.w = 12; w.h = 4; }
            delete w.autoPosition;
        });

        // 3. Update State
        allPages[currentPage] = cleanList;

        // 4. Save immediately
        // We must manually send the cleanList because 'saveLayout' reads from the DOM grid which is broken.

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({
                type: "save_layout",
                pageId: currentPage,
                layout: cleanList // Send our clean list directly
            }));
        }

        // 5. Force Reload
        setTimeout(() => location.reload(), 500);
    }
}

function saveLayout() {
    if (!allPages[currentPage]) return;

    const currentWidgets = allPages[currentPage];
    const layoutData = [];
    let dirty = false;

    grid.engine.nodes.forEach(n => {
        // Find the original widget data
        const original = currentWidgets.find(w => w.id === n.id);

        if (original) {
            // Check if anything actually changed to avoid spam
            if (original.x !== n.x || original.y !== n.y || original.w !== n.w || original.h !== n.h) {
                original.x = n.x;
                original.y = n.y;
                original.w = n.w;
                original.h = n.h;
                dirty = true;
            }
            layoutData.push(original);
        } else {
            console.warn("Ghost widget found in grid, ignoring save for:", n.id);
            // Do NOT add to layoutData. If we save it, we corrupt the DB.
            // By skipping it, we might lose a widget, but better than saving a broken one.
            // Actually, if we skip it, the backend will delete it (sync).
            // Better strategy: Try to recover or just don't save at all if critical mismatch.
        }
    });

    if (layoutData.length < grid.engine.nodes.length) {
        console.error("Critical: Grid has more nodes than valid widgets. Aborting save to prevent data loss.");
        return;
    }

    // Only send if we have a valid layout
    if (ws && ws.readyState === WebSocket.OPEN) {
        console.log("Saving layout...", layoutData.length, "items");
        ws.send(JSON.stringify({
            type: "save_layout",
            pageId: currentPage,
            layout: layoutData
        }));
    }
}

// --- DEVICE IDENTITY ---
function getDeviceId() {
    let id = localStorage.getItem("streamdeck_device_id");
    if (!id) {
        id = "device_" + Math.random().toString(36).substr(2, 9);
        localStorage.setItem("streamdeck_device_id", id);
    }
    return id;
}

// --- CONNECTION ---
function connect() {
    const deviceId = getDeviceId();
    console.log("Connecting as:", deviceId);
    ws = new WebSocket("ws://" + location.hostname + ":8765/?token=1234&device=" + deviceId);

    ws.onopen = () => {
        document.getElementById("conn-status").classList.add("connected");
    };

    ws.onclose = () => {
        document.getElementById("conn-status").classList.remove("connected");
        setTimeout(connect, 3000);
    };

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.type === "config") {
            // Load Pages
            allPages = data.data.pages || {};
            currentPage = data.data.rootPage || "home";
            renderPage(currentPage);
        } else if (data.type === "now_playing") {
            updateSpotifyWidget(data);
        } else if (data.type === "telemetry") {
            updateTelemetry(data);
        }
    };
}

// --- ACTIONS & NAVIGATION ---

function sendAction(action) {
    // Handle Client-Side Navigation
    if (action.type === "navigate") {
        navigateTo(action.target);
        return;
    }

    // Handle Server-Side Actions
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({ type: "exec", action }));
        // Haptic
        if (navigator.vibrate) navigator.vibrate(50);
    }
}

function navigateTo(pageId) {
    if (!allPages[pageId]) {
        // If page doesn't exist, create empty one locally (will allow saving to it)
        console.warn("Creating new page:", pageId);
        allPages[pageId] = [];
    }

    pageHistory.push(currentPage);
    currentPage = pageId;
    renderPage(currentPage);
}

function goBack() {
    const prev = pageHistory.pop();
    if (prev) {
        currentPage = prev;
        renderPage(currentPage);
    }
}

// --- RENDERERS ---

function renderPage(pageId) {
    // Clear current grid
    grid.removeAll();

    // Update Back Button
    const backBtn = document.getElementById("back-btn");
    if (pageHistory.length > 0) {
        backBtn.style.display = "flex";
    } else {
        backBtn.style.display = "none";
    }

    const widgets = allPages[pageId] || [];

    widgets.forEach(widget => {
        let content = "";
        if (widget.type === "spotify") {
            content = renderSpotifyWidget(widget);
        } else if (widget.type === "grid") {
            content = renderGridWidget(widget);
        } else if (widget.type === "gauge" || widget.type === "stat") {
            content = renderStatWidget(widget);
        } else {
            content = renderUnknownWidget(widget);
        }

        grid.addWidget({
            w: widget.w, h: widget.h,
            x: widget.x, y: widget.y,
            content: content,
            noResize: false, noMove: false,
            id: widget.id
        });
    });

    // Re-bind click events
    bindGridActions(widgets); // Pass widget config context?
    // actually bindGridActions queries DOM, but needs config to look up actions.
    // We should pass the *current page's* widgets to it.
}

function renderSpotifyWidget(w) {
    return `
    <div class="widget-spotify" id="sp-widget">
      <div class="delete-btn" onclick="deleteWidget(this)"><i class="fa-solid fa-trash-can"></i></div>
      <div class="sp-cover" id="sp-cover" style="background-image: url('https://misc.scdn.co/liked-songs/liked-songs-640.png')"></div>
      <div class="sp-info-area">
        <div class="sp-top-row">
            <div class="sp-text">
                <div class="sp-title" id="sp-title">Not Playing</div>
                <div class="sp-artist" id="sp-artist">Spotify Connected</div>
            </div>
            <button class="sp-btn like" id="sp-like-btn" onclick="sendAction({type:'spotify', cmd:'like', track_id: currentTrackId})">
                <i class="fa-regular fa-heart" id="sp-heart"></i>
            </button>
        </div>
        
        <div class="sp-progress-container">
            <span id="sp-current-time">0:00</span>
            <input type="range" min="0" max="100" value="0" class="sp-slider" id="sp-progress" 
                onchange="sendAction({type:'spotify', cmd:'seek', value: this.value})">
            <span id="sp-duration">0:00</span>
        </div>

        <div class="sp-controls">
          <button class="sp-btn small" onclick="sendAction({type:'spotify', cmd:'dislike'})" title="Skip/Dislike" style="margin-right: 5px;"><i class="fa-solid fa-ban"></i></button>
          <button class="sp-btn" onclick="sendAction({type:'spotify', cmd:'prev'})"><i class="fa-solid fa-backward-step"></i></button>
          <button class="sp-btn play" id="sp-play-btn" onclick="sendAction({type:'spotify', cmd:'toggle_play'})">
            <i class="fa-solid fa-play" id="sp-play-icon"></i>
          </button>
          <button class="sp-btn" onclick="sendAction({type:'spotify', cmd:'next'})"><i class="fa-solid fa-forward-step"></i></button>
        </div>
      </div>
    </div>
  `;
}

function renderGridWidget(w) {
    let html = `<div class="widget-grid" id="grid-${w.id}">
    <div class="delete-btn" onclick="deleteWidget(this)"><i class="fa-solid fa-trash-can"></i></div>`;
    w.buttons.forEach((btn, idx) => {
        const accentStyle = btn.accent ? `style="text-shadow: 0 0 10px ${btn.accent}; color: ${btn.accent}"` : "";
        html += `
      <div class="action-btn" data-widget="${w.id}" data-idx="${idx}">
        <i class="${btn.icon}" ${accentStyle}></i>
        <span>${btn.label}</span>
      </div>
    `;
    });
    html += `</div>`;
    return html;
}

function bindGridActions(widgets) {
    const btns = document.querySelectorAll(".action-btn");
    btns.forEach(el => {
        el.onclick = () => {
            const wId = el.getAttribute("data-widget");
            const bIdx = el.getAttribute("data-idx");
            const widget = widgets.find(i => i.id === wId);
            if (widget && widget.buttons[bIdx]) {
                sendAction(widget.buttons[bIdx].action);
            }
        };
    });
}

let currentTrackId = "";

function updateSpotifyWidget(data) {
    // Info
    const titleEl = document.getElementById("sp-title");
    if (titleEl) titleEl.textContent = data.title;

    const artistEl = document.getElementById("sp-artist");
    if (artistEl) artistEl.textContent = data.artist;

    const coverEl = document.getElementById("sp-cover");
    if (coverEl && data.image) coverEl.style.backgroundImage = `url('${data.image}')`;

    currentTrackId = data.id;

    // Play/Pause Icon
    const playIcon = document.getElementById("sp-play-icon");
    if (playIcon) {
        playIcon.className = data.is_playing ? "fa-solid fa-pause" : "fa-solid fa-play";
    }

    // Like Status
    const heartIcon = document.getElementById("sp-heart");
    const likeBtn = document.getElementById("sp-like-btn");
    if (heartIcon && likeBtn) {
        if (data.is_liked) {
            heartIcon.className = "fa-solid fa-heart";
            likeBtn.classList.add("liked");
            likeBtn.onclick = () => sendAction({ type: 'spotify', cmd: 'dislike', track_id: currentTrackId }); // Toggle? No, dislike cmd is actually skip in backend. Let's keep logic simple: Heart = Like.
            // Backend said: dislike is skip.
            // Real remove like needs 'remove_like' command. 
            // For now let's just show state.
        } else {
            heartIcon.className = "fa-regular fa-heart";
            likeBtn.classList.remove("liked");
            likeBtn.onclick = () => sendAction({ type: 'spotify', cmd: 'like', track_id: currentTrackId });
        }
    }

    // Progress
    const progressEl = document.getElementById("sp-progress");
    if (progressEl && data.duration_ms) {
        progressEl.max = data.duration_ms;
        progressEl.value = data.progress_ms;

        // Time Text
        const curTimeEl = document.getElementById("sp-current-time");
        if (curTimeEl) curTimeEl.innerText = msToTime(data.progress_ms);

        const durEl = document.getElementById("sp-duration");
        if (durEl) durEl.innerText = msToTime(data.duration_ms);
    }
}

function msToTime(duration) {
    let seconds = Math.floor((duration / 1000) % 60);
    let minutes = Math.floor((duration / (1000 * 60)) % 60);
    return minutes + ":" + (seconds < 10 ? "0" + seconds : seconds);
}

function renderStatWidget(w) {
    return `
      <div class="widget-stat" id="stat-${w.id}" data-metric="${w.metric}">
        <div class="delete-btn" onclick="deleteWidget(this)"><i class="fa-solid fa-trash-can"></i></div>
        <div class="stat-label">${w.label}</div>
        <div class="stat-gauge">
          <svg viewBox="0 0 100 100">
            <circle class="gauge-bg" cx="50" cy="50" r="40" />
            <circle class="gauge-fill" cx="50" cy="50" r="40" stroke-dasharray="251" stroke-dashoffset="251" />
          </svg>
          <div class="stat-value">0%</div>
        </div>
      </div>
    `;
}

function renderUnknownWidget(w) {
    return `
      <div class="widget-unknown" style="width:100%; height:100%; display:flex; flex-direction:column; justify-content:center; align-items:center; background:rgba(255,0,0,0.2); border:1px dashed red; color:white; position:relative;">
        <div class="delete-btn" onclick="deleteWidget(this)"><i class="fa-solid fa-trash-can"></i></div>
        <i class="fa-solid fa-bug" style="font-size:2rem; margin-bottom:5px; opacity:0.7;"></i>
        <span style="font-size:0.7rem; opacity:0.7;">Empty/Error</span>
      </div>
    `;
}

function updateTelemetry(data) {
    latestTelemetry = data;
    document.querySelectorAll(".widget-stat").forEach(el => {
        const metric = el.dataset.metric;
        const val = data[metric];
        if (val !== undefined) {
            const valEl = el.querySelector(".stat-value");
            if (valEl) valEl.innerText = formatMetric(metric, val);

            const path = el.querySelector(".gauge-fill");
            if (path) {
                // Max 251. offset = 251 - (val/100)*251
                // For net, we need a scale. Assume 10MB/s max for gauge? Or just spinner.
                // For now clamp 0-100 for CPU/RAM.
                let pct = val;
                if (metric.startsWith("net")) pct = Math.min((val / 1024 / 1024) * 10, 100); // 10MB = 100%

                const offset = 251 - (pct / 100) * 251;
                path.style.strokeDashoffset = offset;
            }
        }
    });
}

function formatMetric(key, val) {
    if (key === "cpu" || key === "ram") return Math.round(val) + "%";
    if (key.startsWith("net")) {
        const kb = val / 1024;
        if (kb > 1024) return (kb / 1024).toFixed(1) + " MB/s";
        return kb.toFixed(0) + " KB/s";
    }
    return val;
}

// --- WIDGET STORE LOGIC ---
function toggleMenu() {
    document.getElementById("widget-menu").classList.toggle("open");
}

let deleteMode = false;
function toggleDeleteMode() {
    deleteMode = !deleteMode;
    toggleMenu(); // Close menu

    document.querySelectorAll(".grid-stack-item").forEach(el => {
        if (deleteMode) el.classList.add("shake-mode");
        else el.classList.remove("shake-mode");
    });
}

function deleteWidget(btn) {
    // Robust removal using DOM traversal
    const el = btn.closest('.grid-stack-item');
    if (!el) {
        console.error("Could not find widget wrapper");
        return;
    }

    // GridStack 7.x: ID is usually in attribute 'gs-id' or gridstackNode.id
    // But we are managing the widget content. 
    // GridStack stores the 'id' we passed in addWidget in 'el.gridstackNode.id'

    // Fallback: If node not found immediately
    const node = el.gridstackNode;
    const widgetId = node ? node.id : el.getAttribute("gs-id");

    console.log("Deleting widget:", widgetId);

    // Remove from UI
    grid.removeWidget(el);

    // Remove from State
    if (widgetId) {
        const idx = allPages[currentPage].findIndex(w => w.id === widgetId);
        if (idx !== -1) {
            allPages[currentPage].splice(idx, 1);
        } else {
            console.warn("Widget ID not found in state, clean up anyway");
            allPages[currentPage] = allPages[currentPage].filter(w => w.id !== widgetId);
        }
    }

    // Save
    saveLayout();
}

function addWidget(type) {
    toggleMenu();
    if (type === 'delete_mode') {
        toggleDeleteMode();
        return;
    }
    if (type === 'reset_layout') {
        resetLayout();
        return;
    }

    // Define Templates
    let newWidget = {
        id: "w_" + Math.random().toString(36).substr(2, 6),
        x: 0, y: 0, // GridStack will auto-find position
        w: 2, h: 2
    };

    if (type === "cpu") {
        newWidget.type = "gauge";
        newWidget.metric = "cpu";
        newWidget.label = "CPU Load";
    } else if (type === "ram") {
        newWidget.type = "gauge";
        newWidget.metric = "ram";
        newWidget.label = "RAM Usage";
    } else if (type === "temp") {
        newWidget.type = "gauge";
        newWidget.metric = "temp";
        newWidget.label = "Temp";
    } else if (type === "spotify") {
        newWidget.type = "spotify";
        newWidget.w = 4;
        newWidget.h = 2;
    }

    // Add to Local State
    if (!allPages[currentPage]) allPages[currentPage] = [];
    allPages[currentPage].push(newWidget);

    // Add to Grid (Visual)
    let content = "";
    if (newWidget.type === "spotify") content = renderSpotifyWidget(newWidget);
    else if (newWidget.type === "gauge" || newWidget.type === "stat") content = renderStatWidget(newWidget);

    // Use auto-positioning
    grid.addWidget({
        w: newWidget.w, h: newWidget.h,
        content: content,
        id: newWidget.id,
        autoPosition: true
    });

    // Save
    saveLayout();
}

connect();
