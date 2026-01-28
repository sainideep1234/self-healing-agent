"""
Dashboard Route - Web UI for monitoring the healing gateway
"""
from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("", response_class=HTMLResponse)
async def dashboard():
    """Serve the monitoring dashboard."""
    return """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Self-Healing API Gateway</title>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-primary: #0f0f23;
            --bg-secondary: #1a1a35;
            --bg-card: #24243e;
            --accent-primary: #6366f1;
            --accent-secondary: #a855f7;
            --accent-success: #22c55e;
            --accent-warning: #eab308;
            --accent-error: #ef4444;
            --text-primary: #f8fafc;
            --text-secondary: #94a3b8;
            --border: rgba(255, 255, 255, 0.1);
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Inter', sans-serif;
            background: linear-gradient(135deg, var(--bg-primary) 0%, var(--bg-secondary) 100%);
            color: var(--text-primary);
            min-height: 100vh;
            padding: 2rem;
        }
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        
        header {
            text-align: center;
            margin-bottom: 3rem;
        }
        
        h1 {
            font-size: 2.5rem;
            font-weight: 700;
            background: linear-gradient(90deg, var(--accent-primary), var(--accent-secondary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: 0.5rem;
        }
        
        .subtitle {
            color: var(--text-secondary);
            font-size: 1.1rem;
        }
        
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 1.5rem;
            margin-bottom: 2rem;
        }
        
        .card {
            background: var(--bg-card);
            border-radius: 16px;
            padding: 1.5rem;
            border: 1px solid var(--border);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
        }
        
        .card:hover {
            transform: translateY(-4px);
            box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
        }
        
        .card-title {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 0.5rem;
        }
        
        .card-value {
            font-size: 2.5rem;
            font-weight: 700;
        }
        
        .card-value.success { color: var(--accent-success); }
        .card-value.warning { color: var(--accent-warning); }
        .card-value.error { color: var(--accent-error); }
        .card-value.primary { color: var(--accent-primary); }
        
        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.25rem 0.75rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 500;
        }
        
        .status-healthy {
            background: rgba(34, 197, 94, 0.2);
            color: var(--accent-success);
        }
        
        .status-degraded {
            background: rgba(234, 179, 8, 0.2);
            color: var(--accent-warning);
        }
        
        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }
        
        .status-healthy .status-dot { background: var(--accent-success); }
        .status-degraded .status-dot { background: var(--accent-warning); }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .section-title {
            font-size: 1.25rem;
            font-weight: 600;
            margin-bottom: 1rem;
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }
        
        .events-list {
            background: var(--bg-card);
            border-radius: 16px;
            border: 1px solid var(--border);
            overflow: hidden;
        }
        
        .event-item {
            display: flex;
            align-items: center;
            gap: 1rem;
            padding: 1rem 1.5rem;
            border-bottom: 1px solid var(--border);
            transition: background 0.2s;
        }
        
        .event-item:hover {
            background: rgba(255, 255, 255, 0.02);
        }
        
        .event-item:last-child {
            border-bottom: none;
        }
        
        .event-type {
            width: 12px;
            height: 12px;
            border-radius: 50%;
            flex-shrink: 0;
        }
        
        .event-type.healing_success { background: var(--accent-success); }
        .event-type.healing_started { background: var(--accent-primary); }
        .event-type.healing_failed { background: var(--accent-error); }
        .event-type.schema_mismatch { background: var(--accent-warning); }
        
        .event-content {
            flex: 1;
            min-width: 0;
        }
        
        .event-endpoint {
            font-family: monospace;
            font-size: 0.9rem;
            color: var(--text-primary);
        }
        
        .event-meta {
            font-size: 0.75rem;
            color: var(--text-secondary);
            margin-top: 0.25rem;
        }
        
        .event-time {
            font-size: 0.75rem;
            color: var(--text-secondary);
        }
        
        .mappings-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 1rem;
        }
        
        .mapping-card {
            background: var(--bg-card);
            border-radius: 12px;
            padding: 1.25rem;
            border: 1px solid var(--border);
        }
        
        .mapping-endpoint {
            font-family: monospace;
            font-size: 0.9rem;
            color: var(--accent-primary);
            margin-bottom: 0.75rem;
        }
        
        .mapping-fields {
            display: flex;
            flex-direction: column;
            gap: 0.5rem;
        }
        
        .field-mapping {
            display: flex;
            align-items: center;
            gap: 0.75rem;
            font-size: 0.85rem;
        }
        
        .field-source {
            font-family: monospace;
            color: var(--accent-error);
            background: rgba(239, 68, 68, 0.1);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }
        
        .field-target {
            font-family: monospace;
            color: var(--accent-success);
            background: rgba(34, 197, 94, 0.1);
            padding: 0.25rem 0.5rem;
            border-radius: 4px;
        }
        
        .field-arrow {
            color: var(--text-secondary);
        }
        
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 0.5rem;
            padding: 0.75rem 1.5rem;
            border-radius: 8px;
            font-size: 0.875rem;
            font-weight: 500;
            border: none;
            cursor: pointer;
            transition: all 0.2s;
        }
        
        .btn-primary {
            background: linear-gradient(135deg, var(--accent-primary), var(--accent-secondary));
            color: white;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 10px 20px rgba(99, 102, 241, 0.3);
        }
        
        .btn-danger {
            background: rgba(239, 68, 68, 0.2);
            color: var(--accent-error);
        }
        
        .btn-danger:hover {
            background: rgba(239, 68, 68, 0.3);
        }
        
        .actions {
            display: flex;
            gap: 0.75rem;
            margin-bottom: 1rem;
        }
        
        .loading {
            text-align: center;
            padding: 2rem;
            color: var(--text-secondary);
        }
        
        .empty-state {
            text-align: center;
            padding: 3rem;
            color: var(--text-secondary);
        }
        
        .empty-state-icon {
            font-size: 3rem;
            margin-bottom: 1rem;
        }
        
        footer {
            text-align: center;
            margin-top: 3rem;
            color: var(--text-secondary);
            font-size: 0.875rem;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🔧 Self-Healing API Gateway</h1>
            <p class="subtitle">Real-time schema drift detection and autonomous healing</p>
        </header>
        
        <!-- Status Cards -->
        <div class="grid" id="status-grid">
            <div class="card">
                <div class="card-title">Gateway Status</div>
                <div id="health-status">
                    <span class="status-badge status-healthy">
                        <span class="status-dot"></span>
                        Loading...
                    </span>
                </div>
            </div>
            <div class="card">
                <div class="card-title">Success Rate (24h)</div>
                <div class="card-value success" id="success-rate">--%</div>
            </div>
            <div class="card">
                <div class="card-title">Healing Events</div>
                <div class="card-value primary" id="total-events">--</div>
            </div>
            <div class="card">
                <div class="card-title">Cached Mappings</div>
                <div class="card-value warning" id="cached-mappings">--</div>
            </div>
        </div>
        
        <!-- Cached Mappings Section -->
        <div class="section-title">📦 Cached Schema Mappings</div>
        <div class="actions">
            <button class="btn btn-primary" onclick="refreshData()">🔄 Refresh</button>
            <button class="btn btn-danger" onclick="clearCache()">🗑️ Clear Cache</button>
        </div>
        <div class="mappings-grid" id="mappings-list">
            <div class="loading">Loading mappings...</div>
        </div>
        
        <br><br>
        
        <!-- Recent Events Section -->
        <div class="section-title">📊 Recent Healing Events</div>
        <div class="events-list" id="events-list">
            <div class="loading">Loading events...</div>
        </div>
        
        <footer>
            <p>Self-Healing API Gateway v1.0.0 • Powered by FastAPI & LLM</p>
        </footer>
    </div>
    
    <script>
        async function fetchHealth() {
            try {
                const res = await fetch('/admin/health');
                const data = await res.json();
                
                const statusEl = document.getElementById('health-status');
                const isHealthy = data.status === 'healthy';
                const statusClass = isHealthy ? 'status-healthy' : 'status-degraded';
                
                statusEl.innerHTML = `
                    <span class="status-badge ${statusClass}">
                        <span class="status-dot"></span>
                        ${data.status.toUpperCase()}
                    </span>
                    <p style="margin-top: 0.5rem; font-size: 0.75rem; color: var(--text-secondary)">
                        Redis: ${data.redis_connected ? '✅' : '❌'} • 
                        MongoDB: ${data.mongodb_connected ? '✅' : '❌'} • 
                        Upstream: ${data.upstream_reachable ? '✅' : '❌'}
                    </p>
                `;
            } catch (e) {
                console.error('Health check failed:', e);
            }
        }
        
        async function fetchStats() {
            try {
                const res = await fetch('/admin/stats?hours=24');
                const data = await res.json();
                
                document.getElementById('success-rate').textContent = 
                    `${data.success_rate || 0}%`;
                document.getElementById('total-events').textContent = 
                    data.total_events || 0;
            } catch (e) {
                console.error('Stats fetch failed:', e);
            }
        }
        
        async function fetchMappings() {
            try {
                const res = await fetch('/admin/mappings');
                const data = await res.json();
                
                document.getElementById('cached-mappings').textContent = data.total;
                
                const listEl = document.getElementById('mappings-list');
                
                if (data.mappings.length === 0) {
                    listEl.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">📭</div>
                            <p>No cached mappings yet</p>
                            <p style="font-size: 0.75rem; margin-top: 0.5rem">
                                Mappings will appear here when schema drift is detected and healed
                            </p>
                        </div>
                    `;
                    return;
                }
                
                listEl.innerHTML = data.mappings.map(m => `
                    <div class="mapping-card">
                        <div class="mapping-endpoint">${m.endpoint}</div>
                        <div class="mapping-fields">
                            ${m.field_mappings.map(f => `
                                <div class="field-mapping">
                                    <span class="field-source">${f.source_field}</span>
                                    <span class="field-arrow">→</span>
                                    <span class="field-target">${f.target_field}</span>
                                    <span style="color: var(--text-secondary); font-size: 0.75rem">
                                        (${Math.round(f.confidence * 100)}%)
                                    </span>
                                </div>
                            `).join('')}
                        </div>
                        <p style="font-size: 0.7rem; color: var(--text-secondary); margin-top: 0.75rem">
                            v${m.version} • ${m.created_by} • ${m.llm_model || 'unknown'}
                        </p>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Mappings fetch failed:', e);
            }
        }
        
        async function fetchEvents() {
            try {
                const res = await fetch('/admin/events?hours=24&limit=20');
                const data = await res.json();
                
                const listEl = document.getElementById('events-list');
                
                if (data.events.length === 0) {
                    listEl.innerHTML = `
                        <div class="empty-state">
                            <div class="empty-state-icon">📭</div>
                            <p>No events yet</p>
                        </div>
                    `;
                    return;
                }
                
                listEl.innerHTML = data.events.map(e => `
                    <div class="event-item">
                        <div class="event-type ${e.event_type}"></div>
                        <div class="event-content">
                            <div class="event-endpoint">${e.endpoint}</div>
                            <div class="event-meta">${e.event_type.replace(/_/g, ' ')}</div>
                        </div>
                        <div class="event-time">${new Date(e.timestamp).toLocaleTimeString()}</div>
                    </div>
                `).join('');
            } catch (e) {
                console.error('Events fetch failed:', e);
            }
        }
        
        async function clearCache() {
            if (!confirm('Clear all cached mappings?')) return;
            
            try {
                await fetch('/admin/mappings', { method: 'DELETE' });
                refreshData();
            } catch (e) {
                console.error('Clear cache failed:', e);
            }
        }
        
        function refreshData() {
            fetchHealth();
            fetchStats();
            fetchMappings();
            fetchEvents();
        }
        
        // Initial load
        refreshData();
        
        // Auto-refresh every 10 seconds
        setInterval(refreshData, 10000);
    </script>
</body>
</html>
    """
