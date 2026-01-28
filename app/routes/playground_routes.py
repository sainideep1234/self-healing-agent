"""
Playground Route - Embedded Chaos Playground (no frontend build required)

This serves a complete playground UI directly from the backend,
making it easy to demo without needing to run the Next.js frontend.
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["Playground"])


@router.get("/playground", response_class=HTMLResponse)
async def playground():
    """Serve the embedded Chaos Playground."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🎮 Chaos Playground | Self-Healing API Gateway</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0f0f23;
            --bg-secondary: #1a1a35;
            --bg-card: rgba(36, 36, 62, 0.8);
            --accent-primary: #6366f1;
            --accent-secondary: #a855f7;
            --accent-success: #22c55e;
            --accent-warning: #eab308;
            --accent-error: #ef4444;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
        }
        
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 1.5rem;
        }
        
        .container { max-width: 1400px; margin: 0 auto; }
        
        header { text-align: center; margin-bottom: 2rem; }
        
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        
        .subtitle { color: var(--text-secondary); font-size: 1rem; }
        
        .stats-bar {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 1rem;
        }
        
        .stat { display: flex; align-items: center; gap: 0.5rem; font-size: 0.875rem; }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .connected { background: var(--accent-success); }
        .disconnected { background: var(--accent-error); }
        
        .main-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 1.5rem;
        }
        
        @media (max-width: 1024px) {
            .main-grid { grid-template-columns: 1fr; }
        }
        
        .pane {
            background: var(--bg-card);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 16px;
            padding: 1.5rem;
            display: flex;
            flex-direction: column;
            min-height: 500px;
        }
        
        .pane-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 1rem;
        }
        
        .pane-title {
            font-size: 1.125rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .badge {
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .badge-stable { background: rgba(34, 197, 94, 0.2); color: var(--accent-success); }
        .badge-drifted { background: rgba(239, 68, 68, 0.2); color: var(--accent-error); }
        .badge-chaotic { background: rgba(168, 85, 247, 0.2); color: var(--accent-secondary); }
        .badge-healed { background: rgba(34, 197, 94, 0.2); color: var(--accent-success); animation: pulse 1s infinite; }
        
        .json-viewer {
            background: rgba(0, 0, 0, 0.3);
            border-radius: 8px;
            padding: 1rem;
            font-family: 'Monaco', monospace;
            font-size: 0.75rem;
            flex: 1;
            overflow: auto;
            color: var(--text-secondary);
        }
        
        .btn {
            width: 100%;
            padding: 1rem;
            border: none;
            border-radius: 12px;
            font-size: 1rem;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
            margin-top: 0.75rem;
        }
        
        .btn:hover { transform: scale(1.02); }
        .btn:active { transform: scale(0.98); }
        
        .btn-chaos {
            background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
            color: white;
            font-size: 1.25rem;
            padding: 1.25rem;
        }
        
        .btn-chaos:hover { box-shadow: 0 10px 40px rgba(239, 68, 68, 0.4); }
        
        .btn-fix { background: rgba(34, 197, 94, 0.2); color: var(--accent-success); }
        .btn-trigger { background: rgba(168, 85, 247, 0.2); color: var(--accent-secondary); }
        .btn-clear { background: rgba(100, 116, 139, 0.2); color: var(--text-secondary); padding: 0.5rem; }
        
        .thoughts-container {
            flex: 1;
            overflow-y: auto;
            padding-right: 0.5rem;
            max-height: 350px;
        }
        
        .thought {
            padding: 0.75rem;
            border-radius: 8px;
            margin-bottom: 0.5rem;
            animation: fadeIn 0.3s ease-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .thought-alert { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); }
        .thought-analyzing { background: rgba(59, 130, 246, 0.1); border: 1px solid rgba(59, 130, 246, 0.3); }
        .thought-scanning { background: rgba(168, 85, 247, 0.1); border: 1px solid rgba(168, 85, 247, 0.3); }
        .thought-hypothesis { background: rgba(234, 179, 8, 0.1); border: 1px solid rgba(234, 179, 8, 0.3); }
        .thought-patching { background: rgba(249, 115, 22, 0.1); border: 1px solid rgba(249, 115, 22, 0.3); }
        .thought-success { background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); }
        .thought-failure { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); }
        .thought-info { background: rgba(100, 116, 139, 0.1); border: 1px solid rgba(100, 116, 139, 0.3); }
        
        .thought-text { font-size: 0.875rem; }
        .thought-meta { font-size: 0.75rem; color: var(--text-secondary); margin-top: 0.25rem; }
        
        .diff-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1rem; }
        
        .diff-original { background: rgba(239, 68, 68, 0.1); border: 1px solid rgba(239, 68, 68, 0.3); }
        .diff-fixed { background: rgba(34, 197, 94, 0.1); border: 1px solid rgba(34, 197, 94, 0.3); }
        
        .diff-label { font-size: 0.75rem; font-weight: 600; margin-bottom: 0.5rem; }
        .diff-original .diff-label { color: var(--accent-error); }
        .diff-fixed .diff-label { color: var(--accent-success); }
        
        .mapping-row {
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-size: 0.875rem;
            margin-bottom: 0.5rem;
        }
        
        .field-tag {
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
            font-family: monospace;
            font-size: 0.75rem;
        }
        
        .field-source { background: rgba(239, 68, 68, 0.2); color: var(--accent-error); }
        .field-target { background: rgba(34, 197, 94, 0.2); color: var(--accent-success); }
        
        .cost-counter {
            position: fixed;
            bottom: 1.5rem;
            right: 1.5rem;
            background: var(--bg-card);
            backdrop-filter: blur(10px);
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 0.75rem 1rem;
            display: flex;
            align-items: center;
            gap: 0.75rem;
        }
        
        .cost-label { font-size: 0.75rem; color: var(--text-secondary); }
        .cost-value { font-size: 1.25rem; font-family: monospace; color: var(--accent-success); }
        
        .toggle-row {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 0.75rem;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            margin-bottom: 1rem;
        }
        
        .toggle {
            width: 48px;
            height: 24px;
            background: rgba(100, 116, 139, 0.5);
            border-radius: 12px;
            position: relative;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .toggle.active { background: var(--accent-success); }
        
        .toggle::after {
            content: '';
            position: absolute;
            width: 20px;
            height: 20px;
            background: white;
            border-radius: 50%;
            top: 2px;
            left: 2px;
            transition: transform 0.3s;
        }
        
        .toggle.active::after { transform: translateX(24px); }
        
        .result-status {
            padding: 1rem;
            border-radius: 8px;
            margin-top: auto;
        }
        
        .result-healed {
            background: rgba(34, 197, 94, 0.1);
            border: 1px solid rgba(34, 197, 94, 0.3);
            box-shadow: 0 0 20px rgba(34, 197, 94, 0.3);
        }
        
        .empty-state {
            flex: 1;
            display: flex;
            flex-direction: column;
            justify-content: center;
            align-items: center;
            color: var(--text-secondary);
        }
        
        .empty-icon { font-size: 3rem; opacity: 0.3; margin-bottom: 1rem; }
        
        .schema-changes {
            margin-top: 1rem;
            padding: 0.75rem;
            background: rgba(239, 68, 68, 0.1);
            border: 1px solid rgba(239, 68, 68, 0.3);
            border-radius: 8px;
        }
        
        .schema-changes-title { font-size: 0.75rem; color: var(--accent-error); font-weight: 600; margin-bottom: 0.5rem; }
        .schema-changes-item { font-size: 0.75rem; color: var(--text-secondary); }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎮 Chaos Playground</h1>
            <p class="subtitle">Watch AI heal broken APIs in real-time</p>
            <div class="stats-bar">
                <div class="stat">
                    <div class="status-dot" id="connection-dot"></div>
                    <span id="connection-status">Connecting...</span>
                </div>
                <div class="stat">
                    <span>📊</span>
                    <span id="healing-count">0 healings</span>
                </div>
                <div class="stat">
                    <span>💰</span>
                    <span id="total-cost" style="color: var(--accent-success); font-family: monospace;">$0.0000</span>
                </div>
            </div>
        </header>

        <div class="main-grid">
            <!-- LEFT: Legacy API -->
            <div class="pane">
                <div class="pane-header">
                    <div class="pane-title">⚠️ Legacy API</div>
                    <span class="badge badge-stable" id="mode-badge">STABLE</span>
                </div>
                
                <div class="json-viewer" id="original-json">
                    <div style="color: rgba(255,255,255,0.3)">// Current API Response</div>
                    <div style="margin-top: 1rem; font-style: italic;">
                        Click "Break API" to see schema drift
                    </div>
                </div>
                
                <button class="btn btn-chaos" id="break-btn" onclick="breakAPI()">
                    💥 BREAK THIS API!
                </button>
                
                <button class="btn btn-fix" onclick="fixAPI()">
                    🔧 Reset to Stable
                </button>
                
                <button class="btn btn-trigger" onclick="triggerRequest()">
                    🚀 Trigger Request
                </button>
                
                <div class="schema-changes" id="schema-changes" style="display: none;">
                    <div class="schema-changes-title">⚠️ Schema Changed:</div>
                    <div class="schema-changes-item">user_id → uid</div>
                    <div class="schema-changes-item">name → full_name</div>
                    <div class="schema-changes-item">email → email_address</div>
                </div>
            </div>

            <!-- MIDDLE: Agent Brain -->
            <div class="pane">
                <div class="pane-header">
                    <div class="pane-title">🧠 Agent Brain</div>
                    <button class="btn btn-clear" onclick="clearStream()">🗑️</button>
                </div>
                
                <div class="toggle-row">
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <span>🛡️</span>
                        <span style="font-size: 0.875rem;">Human Approval</span>
                    </div>
                    <div class="toggle" id="human-toggle" onclick="toggleHumanInLoop()"></div>
                </div>
                
                <div class="thoughts-container" id="thoughts-container">
                    <div class="empty-state">
                        <div class="empty-icon">🧠</div>
                        <p>Agent is waiting...</p>
                        <p style="font-size: 0.75rem; margin-top: 0.25rem;">Break the API to see healing!</p>
                    </div>
                </div>
            </div>

            <!-- RIGHT: Result -->
            <div class="pane">
                <div class="pane-header">
                    <div class="pane-title">✅ Result</div>
                    <span class="badge badge-healed" id="healed-badge" style="display: none;">✨ HEALED</span>
                </div>
                
                <div id="result-content">
                    <div class="empty-state">
                        <div class="empty-icon">⚡</div>
                        <p>No results yet</p>
                        <p style="font-size: 0.75rem; margin-top: 0.25rem;">Break the API and watch the magic!</p>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <!-- Cost Counter -->
    <div class="cost-counter">
        <span style="font-size: 1.5rem;">💰</span>
        <div>
            <div class="cost-label">Session Cost</div>
            <div class="cost-value" id="cost-display">$0.0000</div>
        </div>
    </div>

    <script>
        let eventSource = null;
        let thoughts = [];
        let mockMode = 'stable';
        let humanInLoop = false;
        let totalCost = 0;
        let healingCount = 0;

        // Connect to SSE stream
        function connectSSE() {
            eventSource = new EventSource('/chaos/stream');
            
            eventSource.onopen = () => {
                document.getElementById('connection-dot').className = 'status-dot connected';
                document.getElementById('connection-status').textContent = 'Connected';
            };
            
            eventSource.onmessage = (event) => {
                try {
                    const thought = JSON.parse(event.data);
                    if (thought.type === 'connected') return;
                    
                    addThought(thought);
                    
                    if (thought.cost_usd) {
                        totalCost += thought.cost_usd;
                        updateCostDisplay();
                    }
                    
                    if (thought.type === 'success') {
                        healingCount++;
                        document.getElementById('healing-count').textContent = healingCount + ' healings';
                    }
                } catch (e) {
                    console.error('Parse error:', e);
                }
            };
            
            eventSource.onerror = () => {
                document.getElementById('connection-dot').className = 'status-dot disconnected';
                document.getElementById('connection-status').textContent = 'Disconnected';
                eventSource.close();
                setTimeout(connectSSE, 3000);
            };
        }

        function addThought(thought) {
            thoughts.push(thought);
            if (thoughts.length > 50) thoughts.shift();
            renderThoughts();
        }

        function renderThoughts() {
            const container = document.getElementById('thoughts-container');
            if (thoughts.length === 0) {
                container.innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">🧠</div>
                        <p>Agent is waiting...</p>
                    </div>
                `;
                return;
            }
            
            const icons = {
                alert: '🔴', analyzing: '🧐', scanning: '🔍', hypothesis: '💡',
                patching: '🛠️', retrying: '🔄', success: '🟢', failure: '❌',
                waiting: '⏸️', info: 'ℹ️'
            };
            
            container.innerHTML = thoughts.map(t => `
                <div class="thought thought-${t.type}">
                    <div class="thought-text">${icons[t.type] || ''} ${t.message}</div>
                    ${t.confidence ? `<div class="thought-meta">Confidence: ${(t.confidence * 100).toFixed(0)}%</div>` : ''}
                    ${t.cost_usd ? `<div class="thought-meta" style="color: var(--accent-success);">$${t.cost_usd.toFixed(4)}</div>` : ''}
                </div>
            `).join('');
            
            container.scrollTop = container.scrollHeight;
        }

        function updateCostDisplay() {
            document.getElementById('total-cost').textContent = '$' + totalCost.toFixed(4);
            document.getElementById('cost-display').textContent = '$' + totalCost.toFixed(4);
        }

        async function breakAPI() {
            const btn = document.getElementById('break-btn');
            btn.textContent = '⏳ Breaking...';
            btn.disabled = true;
            
            try {
                await fetch('/chaos/break', { method: 'POST' });
                mockMode = 'drifted';
                updateModeDisplay();
                
                // Trigger a request
                await triggerRequest();
            } catch (e) {
                console.error('Break error:', e);
            }
            
            btn.textContent = '💥 BREAK THIS API!';
            btn.disabled = false;
        }

        async function fixAPI() {
            try {
                await fetch('/chaos/fix', { method: 'POST' });
                mockMode = 'stable';
                updateModeDisplay();
                
                document.getElementById('original-json').innerHTML = `
                    <div style="color: rgba(255,255,255,0.3)">// Current API Response</div>
                    <div style="margin-top: 1rem; font-style: italic;">API reset to stable</div>
                `;
                document.getElementById('result-content').innerHTML = `
                    <div class="empty-state">
                        <div class="empty-icon">⚡</div>
                        <p>No results yet</p>
                    </div>
                `;
                document.getElementById('healed-badge').style.display = 'none';
            } catch (e) {
                console.error('Fix error:', e);
            }
        }

        async function triggerRequest() {
            try {
                // Get raw upstream response
                const rawRes = await fetch('http://localhost:8001/api/users/1');
                const rawData = await rawRes.json();
                
                document.getElementById('original-json').innerHTML = `
                    <div style="color: rgba(255,255,255,0.3)">// Current API Response</div>
                    <pre style="color: var(--text-secondary); margin-top: 0.5rem;">${JSON.stringify(rawData, null, 2)}</pre>
                `;
                
                // Get proxied response
                const proxyRes = await fetch('/api/users/1');
                const proxyData = await proxyRes.json();
                const healed = proxyRes.headers.get('X-Schema-Healed') === 'true';
                
                if (healed) {
                    document.getElementById('healed-badge').style.display = 'inline';
                    document.getElementById('result-content').innerHTML = `
                        <div class="diff-grid">
                            <div class="json-viewer diff-original">
                                <div class="diff-label">❌ Original (Broken)</div>
                                <pre>${JSON.stringify(rawData, null, 2)}</pre>
                            </div>
                            <div class="json-viewer diff-fixed">
                                <div class="diff-label">✓ Transformed (Fixed)</div>
                                <pre>${JSON.stringify(proxyData, null, 2)}</pre>
                            </div>
                        </div>
                        <div style="padding: 1rem; background: rgba(168, 85, 247, 0.1); border: 1px solid rgba(168, 85, 247, 0.3); border-radius: 8px;">
                            <div style="color: var(--accent-secondary); font-weight: 600; margin-bottom: 0.5rem;">🔗 Field Mappings</div>
                            <div class="mapping-row">
                                <span class="field-tag field-source">uid</span>
                                <span>→</span>
                                <span class="field-tag field-target">user_id</span>
                                <span style="font-size: 0.75rem; color: var(--accent-success);">92%</span>
                            </div>
                            <div class="mapping-row">
                                <span class="field-tag field-source">full_name</span>
                                <span>→</span>
                                <span class="field-tag field-target">name</span>
                                <span style="font-size: 0.75rem; color: var(--accent-success);">88%</span>
                            </div>
                        </div>
                        <div class="result-status result-healed" style="margin-top: 1rem;">
                            <div style="display: flex; justify-content: space-between;">
                                <div>
                                    <div style="font-size: 0.75rem; color: var(--text-secondary);">Status</div>
                                    <div style="font-size: 1.5rem; font-weight: bold; color: var(--accent-success);">200 ✓</div>
                                </div>
                                <div style="text-align: right;">
                                    <div style="font-size: 0.75rem; color: var(--text-secondary);">Cache</div>
                                    <div style="font-size: 0.875rem; color: var(--accent-primary);">HIT ⚡</div>
                                </div>
                            </div>
                        </div>
                    `;
                } else {
                    document.getElementById('healed-badge').style.display = 'none';
                    document.getElementById('result-content').innerHTML = `
                        <div class="json-viewer">
                            <pre>${JSON.stringify(proxyData, null, 2)}</pre>
                        </div>
                        <div class="result-status" style="background: rgba(100, 116, 139, 0.1); border: 1px solid rgba(100, 116, 139, 0.3);">
                            <div style="font-size: 0.75rem; color: var(--text-secondary);">Status</div>
                            <div style="font-size: 1.5rem; font-weight: bold; color: var(--accent-success);">200</div>
                        </div>
                    `;
                }
            } catch (e) {
                console.error('Request error:', e);
            }
        }

        function updateModeDisplay() {
            const badge = document.getElementById('mode-badge');
            const schemaChanges = document.getElementById('schema-changes');
            
            badge.textContent = mockMode.toUpperCase();
            badge.className = 'badge badge-' + mockMode;
            
            schemaChanges.style.display = mockMode === 'drifted' ? 'block' : 'none';
        }

        async function toggleHumanInLoop() {
            humanInLoop = !humanInLoop;
            const toggle = document.getElementById('human-toggle');
            toggle.classList.toggle('active', humanInLoop);
            
            try {
                await fetch('/chaos/human-in-loop', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ enabled: humanInLoop, threshold: 0.7 })
                });
            } catch (e) {
                console.error('Toggle error:', e);
            }
        }

        async function clearStream() {
            thoughts = [];
            renderThoughts();
            try {
                await fetch('/chaos/clear', { method: 'DELETE' });
            } catch (e) {
                console.error('Clear error:', e);
            }
        }

        // Initialize
        connectSSE();
    </script>
</body>
</html>
    """
