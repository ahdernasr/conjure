"""Golden app templates — pre-built, pre-tested fallbacks for demo."""

from .generator import (
    write_app_files,
    replace_app_id_placeholder,
    inject_sync_script,
    extract_theme_color,
)

GOLDEN_NAMES = {
    "hiit": "HIIT Timer",
    "poker": "Poker Scoreboard",
    "packing": "Packing List",
}

# Keywords for matching prompts to golden templates
# Only include specific keywords — avoid generic words like "timer", "list", "game"
# that would false-match unrelated prompts
GOLDEN_KEYWORDS = {
    "hiit": ["hiit", "hiit timer", "workout timer", "interval training", "tabata", "work rest"],
    "poker": ["poker", "poker scoreboard", "chip count", "casino", "poker night"],
    "packing": ["packing list", "packing checklist", "travel pack", "luggage", "suitcase"],
}

GOLDEN_TEMPLATES = {}


def deploy_golden(golden_id: str, app_id: str) -> tuple[str, str, str]:
    """Deploy a golden template for the given app_id.
    Returns (app_name, theme_color, html)."""
    raw_html = GOLDEN_TEMPLATES[golden_id]
    app_name = GOLDEN_NAMES[golden_id]

    html = replace_app_id_placeholder(raw_html, app_id)
    theme_color = extract_theme_color(html)
    html = inject_sync_script(html, app_id)

    write_app_files(app_id, html, app_name, theme_color)
    return app_name, theme_color, html


def pick_best_golden(prompt: str) -> str | None:
    """Simple keyword matching to pick the most relevant golden template.
    Returns golden_id or None if no good match.
    Requires at least 1 keyword match — never falls back to a random template."""
    prompt_lower = prompt.lower()
    best_id = None
    best_score = 0

    for golden_id, keywords in GOLDEN_KEYWORDS.items():
        score = sum(1 for kw in keywords if kw in prompt_lower)
        if score > best_score:
            best_score = score
            best_id = golden_id

    # Only return if we actually matched something
    if best_score >= 1:
        return best_id
    return None

# ─────────────────────────────────────────────────────────────────────────────
# 1. HIIT TIMER
# ─────────────────────────────────────────────────────────────────────────────
GOLDEN_TEMPLATES["hiit"] = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#ef4444">
  <title>HIIT Timer</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0a0a0a; color: #e5e5e5;
      min-height: 100dvh; display: flex; flex-direction: column;
      user-select: none; -webkit-user-select: none;
    }
    .header { padding: 16px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .header h1 { font-size: 20px; font-weight: 700; }
    .header p { font-size: 12px; color: #737373; margin-top: 4px; }
    .timer-area { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 24px; gap: 16px; }
    .phase-label { font-size: 14px; text-transform: uppercase; letter-spacing: 2px; color: #737373; }
    .phase-label.work { color: #ef4444; }
    .phase-label.rest { color: #22c55e; }
    .time-display { font-size: 96px; font-weight: 700; font-variant-numeric: tabular-nums; line-height: 1; }
    .round-info { font-size: 18px; color: #a3a3a3; }
    .round-info span { color: #e5e5e5; font-weight: 600; }
    .controls { display: flex; gap: 12px; padding: 24px; justify-content: center; }
    .btn {
      min-height: 52px; min-width: 120px; border: none; border-radius: 12px;
      font-size: 16px; font-weight: 600; cursor: pointer;
      transition: transform 150ms ease;
      font-family: inherit;
    }
    .btn:active { transform: scale(0.97); }
    .btn-primary { background: #ef4444; color: white; }
    .btn-secondary { background: #141414; color: #e5e5e5; border: 1px solid rgba(255,255,255,0.06); }
    .stats { padding: 16px; border-top: 1px solid rgba(255,255,255,0.06); }
    .stats-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; }
    .stat-card { background: #141414; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px; padding: 12px; text-align: center; }
    .stat-value { font-size: 24px; font-weight: 700; font-variant-numeric: tabular-nums; }
    .stat-label { font-size: 11px; color: #737373; margin-top: 4px; }
    .progress-bar { width: 100%; max-width: 300px; height: 6px; background: #1a1a1a; border-radius: 3px; overflow: hidden; }
    .progress-fill { height: 100%; border-radius: 3px; transition: width 100ms linear; }
    .progress-fill.work { background: #ef4444; }
    .progress-fill.rest { background: #22c55e; }
  </style>
</head>
<body>
  <div class="header">
    <h1>HIIT Timer</h1>
    <p>40s work / 20s rest / 8 rounds</p>
  </div>
  <div class="timer-area">
    <div class="phase-label" id="phaseLabel">READY</div>
    <div class="time-display" id="timeDisplay">40</div>
    <div class="progress-bar"><div class="progress-fill work" id="progressFill" style="width:100%"></div></div>
    <div class="round-info">Round <span id="roundDisplay">0</span> / 8</div>
  </div>
  <div class="controls">
    <button class="btn btn-primary" id="startBtn" onclick="toggleTimer()">Start</button>
    <button class="btn btn-secondary" id="resetBtn" onclick="resetTimer()">Reset</button>
  </div>
  <div class="stats">
    <div class="stats-grid">
      <div class="stat-card"><div class="stat-value" id="totalRounds">0</div><div class="stat-label">Total Rounds</div></div>
      <div class="stat-card"><div class="stat-value" id="totalTime">0:00</div><div class="stat-label">Total Time</div></div>
      <div class="stat-card"><div class="stat-value" id="sessions">0</div><div class="stat-label">Sessions</div></div>
    </div>
  </div>
  <script>
    const WORK_TIME = 40, REST_TIME = 20, TOTAL_ROUNDS = 8;
    let timeLeft = WORK_TIME, currentRound = 0, isWork = true, running = false, interval = null, elapsedTotal = 0;

    const STORAGE_KEY = 'conjure_{{APP_ID}}';
    const defaultData = { totalRounds: 0, totalSeconds: 0, sessions: 0, history: [] };

    window.__conjure = {
      getData: function() {
        try { return JSON.parse(localStorage.getItem(STORAGE_KEY)) || {...defaultData}; } catch(e) { return {...defaultData}; }
      },
      setData: function(data) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        updateStats();
      },
      getSchema: function() {
        return { app_id: '{{APP_ID}}', name: 'HIIT Timer', capabilities: ['track_rounds','track_time','get_history'], data_shape: { totalRounds:'number', totalSeconds:'number', sessions:'number', history:'array' }, actions: { get_stats:'Returns workout statistics', reset:'Clears all history' }};
      }
    };

    function updateDisplay() {
      document.getElementById('timeDisplay').textContent = timeLeft;
      document.getElementById('roundDisplay').textContent = currentRound;
      const label = document.getElementById('phaseLabel');
      const fill = document.getElementById('progressFill');
      if (!running && currentRound === 0) { label.textContent = 'READY'; label.className = 'phase-label'; }
      else if (isWork) { label.textContent = 'WORK'; label.className = 'phase-label work'; fill.className = 'progress-fill work'; }
      else { label.textContent = 'REST'; label.className = 'phase-label rest'; fill.className = 'progress-fill rest'; }
      const total = isWork ? WORK_TIME : REST_TIME;
      fill.style.width = (timeLeft / total * 100) + '%';
    }

    function updateStats() {
      const d = window.__conjure.getData();
      document.getElementById('totalRounds').textContent = d.totalRounds || 0;
      const s = d.totalSeconds || 0;
      document.getElementById('totalTime').textContent = Math.floor(s/60) + ':' + String(s%60).padStart(2,'0');
      document.getElementById('sessions').textContent = d.sessions || 0;
    }

    function tick() {
      timeLeft--;
      elapsedTotal++;
      if (timeLeft <= 0) {
        if (isWork) {
          currentRound++;
          const d = window.__conjure.getData();
          d.totalRounds = (d.totalRounds||0) + 1;
          d.totalSeconds = (d.totalSeconds||0) + WORK_TIME;
          window.__conjure.setData(d);
          try { navigator.vibrate([200]); } catch(e) {}
          if (currentRound >= TOTAL_ROUNDS) { finishWorkout(); return; }
          isWork = false; timeLeft = REST_TIME;
        } else {
          isWork = true; timeLeft = WORK_TIME;
          try { navigator.vibrate([100]); } catch(e) {}
        }
      }
      updateDisplay();
    }

    function toggleTimer() {
      if (running) { clearInterval(interval); running = false; document.getElementById('startBtn').textContent = 'Resume'; }
      else {
        if (currentRound === 0 && timeLeft === WORK_TIME) { currentRound = 1; isWork = true; }
        running = true; interval = setInterval(tick, 1000);
        document.getElementById('startBtn').textContent = 'Pause';
      }
      updateDisplay();
    }

    function resetTimer() {
      clearInterval(interval); running = false; timeLeft = WORK_TIME; currentRound = 0; isWork = true; elapsedTotal = 0;
      document.getElementById('startBtn').textContent = 'Start';
      updateDisplay();
    }

    function finishWorkout() {
      clearInterval(interval); running = false;
      const d = window.__conjure.getData();
      d.sessions = (d.sessions||0) + 1;
      d.history = d.history || [];
      d.history.push({ date: new Date().toISOString(), rounds: TOTAL_ROUNDS, duration: elapsedTotal });
      window.__conjure.setData(d);
      document.getElementById('phaseLabel').textContent = 'DONE!';
      document.getElementById('phaseLabel').className = 'phase-label';
      document.getElementById('startBtn').textContent = 'Start';
      try { navigator.vibrate([200,100,200]); } catch(e) {}
      currentRound = 0; timeLeft = WORK_TIME; isWork = true; elapsedTotal = 0;
    }

    updateDisplay();
    updateStats();
  </script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────────────────────
# 2. POKER SCOREBOARD
# ─────────────────────────────────────────────────────────────────────────────
GOLDEN_TEMPLATES["poker"] = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#8b5cf6">
  <title>Poker Scoreboard</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0a0a0a; color: #e5e5e5;
      min-height: 100dvh; display: flex; flex-direction: column;
      user-select: none; -webkit-user-select: none;
    }
    .header { padding: 16px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .header h1 { font-size: 20px; font-weight: 700; }
    .players { flex: 1; padding: 16px; display: flex; flex-direction: column; gap: 12px; }
    .player-card {
      background: #141414; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;
      padding: 16px; display: flex; align-items: center; gap: 16px;
    }
    .player-card.leader { border-color: #8b5cf6; }
    .rank { width: 28px; height: 28px; border-radius: 50%; background: #1a1a1a; display: flex; align-items: center; justify-content: center; font-size: 13px; font-weight: 700; flex-shrink: 0; }
    .player-card.leader .rank { background: #8b5cf6; }
    .player-info { flex: 1; }
    .player-name { font-size: 16px; font-weight: 600; }
    .player-chips { font-size: 28px; font-weight: 700; font-variant-numeric: tabular-nums; color: #8b5cf6; }
    .chip-controls { display: flex; gap: 6px; }
    .chip-btn {
      width: 40px; height: 40px; border-radius: 8px; border: none;
      font-size: 18px; font-weight: 700; cursor: pointer;
      display: flex; align-items: center; justify-content: center;
      transition: transform 150ms ease; font-family: inherit;
    }
    .chip-btn:active { transform: scale(0.93); }
    .chip-btn.minus { background: #1a1a1a; color: #ef4444; border: 1px solid rgba(255,255,255,0.06); }
    .chip-btn.plus { background: #1a1a1a; color: #22c55e; border: 1px solid rgba(255,255,255,0.06); }
    .amount-selector { padding: 12px 16px; border-top: 1px solid rgba(255,255,255,0.06); }
    .amount-label { font-size: 12px; color: #737373; margin-bottom: 8px; }
    .amount-btns { display: flex; gap: 8px; }
    .amount-btn {
      flex: 1; min-height: 44px; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;
      background: #141414; color: #e5e5e5; font-size: 14px; font-weight: 600;
      cursor: pointer; transition: transform 150ms ease; font-family: inherit;
    }
    .amount-btn:active { transform: scale(0.97); }
    .amount-btn.active { background: #8b5cf6; border-color: #8b5cf6; color: white; }
    .footer { padding: 12px 16px; border-top: 1px solid rgba(255,255,255,0.06); display: flex; gap: 8px; }
    .footer-btn {
      flex: 1; min-height: 44px; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;
      background: #141414; color: #e5e5e5; font-size: 14px; cursor: pointer;
      transition: transform 150ms ease; font-family: inherit;
    }
    .footer-btn:active { transform: scale(0.97); }
  </style>
</head>
<body>
  <div class="header"><h1>Poker Night</h1></div>
  <div class="players" id="playerList"></div>
  <div class="amount-selector">
    <div class="amount-label">Chip Amount</div>
    <div class="amount-btns" id="amountBtns"></div>
  </div>
  <div class="footer">
    <button class="footer-btn" onclick="resetScores()">Reset All</button>
  </div>
  <script>
    const PLAYERS = ['Jake', 'Sarah', 'Mike', 'Emma'];
    const AMOUNTS = [5, 10, 25, 50, 100];
    let currentAmount = 25;

    const STORAGE_KEY = 'conjure_{{APP_ID}}';
    const defaultData = { players: {} };
    PLAYERS.forEach(p => defaultData.players[p] = 0);

    window.__conjure = {
      getData: function() {
        try {
          const d = JSON.parse(localStorage.getItem(STORAGE_KEY));
          if (d && d.players) return d;
          return JSON.parse(JSON.stringify(defaultData));
        } catch(e) { return JSON.parse(JSON.stringify(defaultData)); }
      },
      setData: function(data) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        render();
      },
      getSchema: function() {
        return { app_id: '{{APP_ID}}', name: 'Poker Scoreboard', capabilities: ['track_scores','get_leader'], data_shape: { players:'object' }, actions: { get_stats:'Returns player scores', reset:'Clears all scores' }};
      }
    };

    function adjustChips(player, delta) {
      const d = window.__conjure.getData();
      d.players[player] = (d.players[player] || 0) + delta;
      window.__conjure.setData(d);
      try { navigator.vibrate([10]); } catch(e) {}
    }

    function resetScores() {
      const d = window.__conjure.getData();
      PLAYERS.forEach(p => d.players[p] = 0);
      window.__conjure.setData(d);
    }

    function render() {
      const d = window.__conjure.getData();
      const sorted = PLAYERS.slice().sort((a,b) => (d.players[b]||0) - (d.players[a]||0));
      const maxChips = Math.max(...PLAYERS.map(p => d.players[p]||0));
      const list = document.getElementById('playerList');
      list.innerHTML = sorted.map((p, i) => {
        const chips = d.players[p] || 0;
        const isLeader = chips > 0 && chips === maxChips;
        return '<div class="player-card ' + (isLeader ? 'leader' : '') + '">' +
          '<div class="rank">' + (i+1) + '</div>' +
          '<div class="player-info"><div class="player-name">' + p + '</div>' +
          '<div class="player-chips">$' + chips + '</div></div>' +
          '<div class="chip-controls">' +
          '<button class="chip-btn minus" onclick="adjustChips(\\''+p+'\\',-'+currentAmount+')">−</button>' +
          '<button class="chip-btn plus" onclick="adjustChips(\\''+p+'\\','+currentAmount+')">+</button>' +
          '</div></div>';
      }).join('');
    }

    function renderAmounts() {
      document.getElementById('amountBtns').innerHTML = AMOUNTS.map(a =>
        '<button class="amount-btn ' + (a===currentAmount?'active':'') + '" onclick="setAmount('+a+')">$'+a+'</button>'
      ).join('');
    }

    function setAmount(a) { currentAmount = a; renderAmounts(); }

    render();
    renderAmounts();
  </script>
</body>
</html>"""

# ─────────────────────────────────────────────────────────────────────────────
# 3. PACKING LIST
# ─────────────────────────────────────────────────────────────────────────────
GOLDEN_TEMPLATES["packing"] = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
  <meta name="theme-color" content="#f59e0b">
  <title>Packing List</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #0a0a0a; color: #e5e5e5;
      min-height: 100dvh; display: flex; flex-direction: column;
      user-select: none; -webkit-user-select: none;
    }
    .header { padding: 16px; border-bottom: 1px solid rgba(255,255,255,0.06); }
    .header h1 { font-size: 20px; font-weight: 700; }
    .header .subtitle { font-size: 12px; color: #737373; margin-top: 4px; }
    .progress { padding: 12px 16px; }
    .progress-text { font-size: 13px; color: #737373; margin-bottom: 6px; }
    .progress-text span { color: #f59e0b; font-weight: 600; }
    .progress-bar { width: 100%; height: 6px; background: #1a1a1a; border-radius: 3px; overflow: hidden; }
    .progress-fill { height: 100%; background: #f59e0b; border-radius: 3px; transition: width 200ms ease; }
    .add-form { padding: 8px 16px; display: flex; gap: 8px; }
    .add-input {
      flex: 1; min-height: 44px; background: #141414; border: 1px solid rgba(255,255,255,0.06);
      border-radius: 8px; padding: 0 14px; color: #e5e5e5; font-size: 14px;
      font-family: inherit; outline: none;
    }
    .add-input:focus { border-color: #f59e0b; }
    .add-input::placeholder { color: #525252; }
    .add-btn {
      min-height: 44px; min-width: 44px; background: #f59e0b; border: none; border-radius: 8px;
      color: #0a0a0a; font-size: 22px; font-weight: 700; cursor: pointer;
      transition: transform 150ms ease; font-family: inherit;
    }
    .add-btn:active { transform: scale(0.93); }
    .items { flex: 1; overflow-y: auto; padding: 8px 16px; }
    .item {
      display: flex; align-items: center; gap: 12px; padding: 14px;
      background: #141414; border: 1px solid rgba(255,255,255,0.06); border-radius: 12px;
      margin-bottom: 8px; cursor: pointer; transition: transform 150ms ease;
    }
    .item:active { transform: scale(0.99); }
    .item.checked { opacity: 0.5; }
    .item.checked .item-text { text-decoration: line-through; }
    .checkbox {
      width: 24px; height: 24px; border-radius: 6px; border: 2px solid #404040;
      display: flex; align-items: center; justify-content: center; flex-shrink: 0;
      transition: all 150ms ease;
    }
    .item.checked .checkbox { background: #f59e0b; border-color: #f59e0b; }
    .checkmark { display: none; color: #0a0a0a; font-size: 14px; font-weight: 700; }
    .item.checked .checkmark { display: block; }
    .item-text { flex: 1; font-size: 15px; }
    .delete-btn {
      width: 32px; height: 32px; border: none; background: transparent;
      color: #525252; font-size: 18px; cursor: pointer; border-radius: 6px;
      display: flex; align-items: center; justify-content: center;
    }
    .footer { padding: 12px 16px; border-top: 1px solid rgba(255,255,255,0.06); display: flex; gap: 8px; }
    .footer-btn {
      flex: 1; min-height: 44px; border: 1px solid rgba(255,255,255,0.06); border-radius: 8px;
      background: #141414; color: #e5e5e5; font-size: 13px; cursor: pointer;
      transition: transform 150ms ease; font-family: inherit;
    }
    .footer-btn:active { transform: scale(0.97); }
  </style>
</head>
<body>
  <div class="header">
    <h1>Packing List</h1>
    <div class="subtitle">Weekend Trip</div>
  </div>
  <div class="progress">
    <div class="progress-text"><span id="checkedCount">0</span> / <span id="totalCount">0</span> packed</div>
    <div class="progress-bar"><div class="progress-fill" id="progressFill" style="width:0%"></div></div>
  </div>
  <div class="add-form">
    <input class="add-input" id="addInput" type="text" placeholder="Add item..." onkeydown="if(event.key==='Enter')addItem()">
    <button class="add-btn" onclick="addItem()">+</button>
  </div>
  <div class="items" id="itemList"></div>
  <div class="footer">
    <button class="footer-btn" onclick="clearChecked()">Clear Packed</button>
    <button class="footer-btn" onclick="uncheckAll()">Uncheck All</button>
  </div>
  <script>
    const STORAGE_KEY = 'conjure_{{APP_ID}}';
    const defaults = { items: [
      {id:1,text:'Shirts',checked:false},{id:2,text:'Pants',checked:false},
      {id:3,text:'Underwear',checked:false},{id:4,text:'Toiletries',checked:false},
      {id:5,text:'Phone charger',checked:false},{id:6,text:'Sunglasses',checked:false},
      {id:7,text:'Snacks',checked:false},{id:8,text:'Water bottle',checked:false}
    ]};

    window.__conjure = {
      getData: function() {
        try { const d = JSON.parse(localStorage.getItem(STORAGE_KEY)); return (d && d.items) ? d : JSON.parse(JSON.stringify(defaults)); }
        catch(e) { return JSON.parse(JSON.stringify(defaults)); }
      },
      setData: function(data) {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
        render();
      },
      getSchema: function() {
        return { app_id: '{{APP_ID}}', name: 'Packing List', capabilities: ['track_items','check_items'], data_shape: { items:'array' }, actions: { get_stats:'Returns packing progress', reset:'Clears all items' }};
      }
    };

    function addItem() {
      const input = document.getElementById('addInput');
      const text = input.value.trim();
      if (!text) return;
      const d = window.__conjure.getData();
      d.items.push({ id: Date.now(), text, checked: false });
      window.__conjure.setData(d);
      input.value = '';
      try { navigator.vibrate([10]); } catch(e) {}
    }

    function toggleItem(id) {
      const d = window.__conjure.getData();
      const item = d.items.find(i => i.id === id);
      if (item) { item.checked = !item.checked; window.__conjure.setData(d); }
      try { navigator.vibrate([10]); } catch(e) {}
    }

    function deleteItem(id) {
      const d = window.__conjure.getData();
      d.items = d.items.filter(i => i.id !== id);
      window.__conjure.setData(d);
    }

    function clearChecked() {
      const d = window.__conjure.getData();
      d.items = d.items.filter(i => !i.checked);
      window.__conjure.setData(d);
    }

    function uncheckAll() {
      const d = window.__conjure.getData();
      d.items.forEach(i => i.checked = false);
      window.__conjure.setData(d);
    }

    function render() {
      const d = window.__conjure.getData();
      const items = d.items || [];
      const checked = items.filter(i => i.checked).length;
      document.getElementById('checkedCount').textContent = checked;
      document.getElementById('totalCount').textContent = items.length;
      document.getElementById('progressFill').style.width = items.length ? (checked/items.length*100)+'%' : '0%';
      const unchecked = items.filter(i => !i.checked);
      const checkedItems = items.filter(i => i.checked);
      const all = [...unchecked, ...checkedItems];
      document.getElementById('itemList').innerHTML = all.map(item =>
        '<div class="item ' + (item.checked?'checked':'') + '" onclick="toggleItem('+item.id+')">' +
        '<div class="checkbox"><span class="checkmark">✓</span></div>' +
        '<div class="item-text">' + item.text + '</div>' +
        '<button class="delete-btn" onclick="event.stopPropagation();deleteItem('+item.id+')">×</button>' +
        '</div>'
      ).join('');
    }

    render();
  </script>
</body>
</html>"""
