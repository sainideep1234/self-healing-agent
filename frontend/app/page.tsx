'use client';

import { useState, useEffect, useRef } from 'react';
import { 
  Zap, AlertTriangle, CheckCircle, Brain, DollarSign, 
  ToggleLeft, ToggleRight, RefreshCw, Trash2, Power,
  ArrowRight, Shield, Activity
} from 'lucide-react';

// Types
interface AgentThought {
  id: string;
  type: 'alert' | 'analyzing' | 'scanning' | 'hypothesis' | 'patching' | 'retrying' | 'success' | 'failure' | 'waiting' | 'info';
  message: string;
  timestamp: string;
  confidence?: number;
  cost_usd?: number;
  details?: Record<string, any>;
  requires_approval?: boolean;
}

interface Stats {
  subscribers: number;
  total_thoughts: number;
  total_cost_usd: number;
  session_healings: number;
  pending_approval: boolean;
}

interface ApiResponse {
  status_code: number;
  body: any;
  healed: boolean;
  healing_details?: {
    from_cache: boolean;
    mapping_version: number;
    field_mappings?: Array<{source: string; target: string; confidence: number}>;
    duration_ms: number;
  };
}

// Thought type styling
const thoughtStyles: Record<string, { icon: string; color: string; bg: string }> = {
  alert: { icon: '🔴', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30' },
  analyzing: { icon: '🧐', color: 'text-blue-400', bg: 'bg-blue-500/10 border-blue-500/30' },
  scanning: { icon: '🔍', color: 'text-purple-400', bg: 'bg-purple-500/10 border-purple-500/30' },
  hypothesis: { icon: '💡', color: 'text-yellow-400', bg: 'bg-yellow-500/10 border-yellow-500/30' },
  patching: { icon: '🛠️', color: 'text-orange-400', bg: 'bg-orange-500/10 border-orange-500/30' },
  retrying: { icon: '🔄', color: 'text-cyan-400', bg: 'bg-cyan-500/10 border-cyan-500/30' },
  success: { icon: '🟢', color: 'text-green-400', bg: 'bg-green-500/10 border-green-500/30' },
  failure: { icon: '❌', color: 'text-red-400', bg: 'bg-red-500/10 border-red-500/30' },
  waiting: { icon: '⏸️', color: 'text-amber-400', bg: 'bg-amber-500/10 border-amber-500/30' },
  info: { icon: 'ℹ️', color: 'text-slate-400', bg: 'bg-slate-500/10 border-slate-500/30' },
};

// API Configuration - uses environment variables for production
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
const MOCK_API_URL = process.env.NEXT_PUBLIC_MOCK_API_URL || 'http://localhost:8001';

export default function ChaosPlayground() {
  // State
  const [thoughts, setThoughts] = useState<AgentThought[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [mockMode, setMockMode] = useState<string>('stable');
  const [humanInLoop, setHumanInLoop] = useState(false);
  const [isBreaking, setIsBreaking] = useState(false);
  const [lastResponse, setLastResponse] = useState<ApiResponse | null>(null);
  const [originalData, setOriginalData] = useState<any>(null);
  const [transformedData, setTransformedData] = useState<any>(null);
  const [pendingApproval, setPendingApproval] = useState(false);
  
  const thoughtsEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Auto-scroll to bottom of thoughts
  useEffect(() => {
    thoughtsEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thoughts]);

  // SSE Connection
  useEffect(() => {
    const connectSSE = () => {
      const eventSource = new EventSource(`${API_URL}/chaos/stream`);
      eventSourceRef.current = eventSource;

      eventSource.onopen = () => {
        setIsConnected(true);
        console.log('SSE Connected');
      };

      eventSource.onmessage = (event) => {
        try {
          const thought = JSON.parse(event.data);
          if (thought.type === 'connected') {
            return;
          }
          setThoughts(prev => [...prev.slice(-50), thought]);
          
          if (thought.requires_approval) {
            setPendingApproval(true);
          }
        } catch (e) {
          console.error('Parse error:', e);
        }
      };

      eventSource.onerror = () => {
        setIsConnected(false);
        eventSource.close();
        // Reconnect after 3 seconds
        setTimeout(connectSSE, 3000);
      };
    };

    connectSSE();

    return () => {
      eventSourceRef.current?.close();
    };
  }, []);

  // Fetch stats periodically
  useEffect(() => {
    const fetchStats = async () => {
      try {
        const res = await fetch(`${API_URL}/chaos/stats`);
        const data = await res.json();
        setStats(data.stream);
      } catch (e) {
        console.error('Stats fetch error:', e);
      }
    };

    fetchStats();
    const interval = setInterval(fetchStats, 5000);
    return () => clearInterval(interval);
  }, []);

  // Fetch mock mode
  useEffect(() => {
    const fetchMode = async () => {
      try {
        const res = await fetch(`${API_URL}/chaos/mock-mode`);
        const data = await res.json();
        setMockMode(data.mode || 'stable');
      } catch (e) {
        console.error('Mode fetch error:', e);
      }
    };
    fetchMode();
  }, []);

  // Break the API!
  const breakAPI = async () => {
    setIsBreaking(true);
    try {
      const res = await fetch(`${API_URL}/chaos/break`, { method: 'POST' });
      const data = await res.json();
      setMockMode('drifted');
      
      // Trigger a request to see the healing
      await triggerRequest();
    } catch (e) {
      console.error('Break API error:', e);
    }
    setIsBreaking(false);
  };

  // Fix the API
  const fixAPI = async () => {
    try {
      await fetch(`${API_URL}/chaos/fix`, { method: 'POST' });
      setMockMode('stable');
      setOriginalData(null);
      setTransformedData(null);
      setLastResponse(null);
    } catch (e) {
      console.error('Fix API error:', e);
    }
  };

  // Trigger a test request
  const triggerRequest = async () => {
    try {
      // First get the raw upstream response
      const rawRes = await fetch(`${MOCK_API_URL}/api/users/1`);
      const rawData = await rawRes.json();
      setOriginalData(rawData);

      // Then make request through proxy
      const proxyRes = await fetch(`${API_URL}/api/users/1`);
      const proxyData = await proxyRes.json();
      
      const healed = proxyRes.headers.get('X-Schema-Healed') === 'true';
      const cacheHit = proxyRes.headers.get('X-Healing-Cache') === 'hit';
      
      setTransformedData(proxyData);
      setLastResponse({
        status_code: proxyRes.status,
        body: proxyData,
        healed,
        healing_details: healed ? {
          from_cache: cacheHit,
          mapping_version: 1,
          duration_ms: 0
        } : undefined
      });
    } catch (e) {
      console.error('Request error:', e);
    }
  };

  // Toggle human in the loop
  const toggleHumanInLoop = async () => {
    const newState = !humanInLoop;
    try {
      await fetch(`${API_URL}/chaos/human-in-loop`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: newState, threshold: 0.7 })
      });
      setHumanInLoop(newState);
    } catch (e) {
      console.error('Human in loop toggle error:', e);
    }
  };

  // Approve/Reject healing
  const handleApproval = async (approved: boolean) => {
    try {
      await fetch(`${API_URL}/chaos/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ approved })
      });
      setPendingApproval(false);
    } catch (e) {
      console.error('Approval error:', e);
    }
  };

  // Clear stream
  const clearStream = async () => {
    try {
      await fetch(`${API_URL}/chaos/clear`, { method: 'DELETE' });
      setThoughts([]);
    } catch (e) {
      console.error('Clear error:', e);
    }
  };

  return (
    <div className="min-h-screen p-6">
      {/* Header */}
      <header className="text-center mb-8">
        <h1 className="text-4xl font-bold gradient-text mb-2">
          🎮 Chaos Playground
        </h1>
        <p className="text-slate-400 text-lg">
          Watch AI heal broken APIs in real-time
        </p>
        
        {/* Stats Bar */}
        <div className="flex items-center justify-center gap-6 mt-4">
          <div className="flex items-center gap-2">
            <div className={`status-dot ${isConnected ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-slate-400">
              {isConnected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
          
          <div className="flex items-center gap-2">
            <Activity className="w-4 h-4 text-purple-400" />
            <span className="text-sm text-slate-400">
              {stats?.session_healings || 0} healings
            </span>
          </div>
          
          <div className="flex items-center gap-2">
            <DollarSign className="w-4 h-4 text-green-400" />
            <span className="text-sm text-green-400 font-mono">
              ${(stats?.total_cost_usd || 0).toFixed(4)}
            </span>
          </div>
        </div>
      </header>

      {/* Main Three-Pane Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 max-w-7xl mx-auto">
        
        {/* LEFT PANE: Legacy System (The Problem) */}
        <div className="glass-card p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <AlertTriangle className="w-5 h-5 text-yellow-400" />
              Legacy API
            </h2>
            <span className={`px-3 py-1 rounded-full text-xs font-medium ${
              mockMode === 'stable' 
                ? 'bg-green-500/20 text-green-400' 
                : mockMode === 'drifted'
                ? 'bg-red-500/20 text-red-400'
                : 'bg-purple-500/20 text-purple-400'
            }`}>
              {mockMode.toUpperCase()}
            </span>
          </div>

          {/* JSON Preview */}
          <div className="bg-black/30 rounded-lg p-4 flex-1 overflow-auto mb-4 font-mono text-sm">
            <div className="text-slate-500 text-xs mb-2">// Current API Response</div>
            {originalData ? (
              <pre className="text-slate-300">
                {JSON.stringify(originalData, null, 2)}
              </pre>
            ) : (
              <div className="text-slate-500 italic">
                Click "Break API" to see schema drift
              </div>
            )}
          </div>

          {/* Chaos Controls */}
          <div className="space-y-3">
            <button
              onClick={breakAPI}
              disabled={isBreaking}
              className={`w-full py-4 rounded-xl font-bold text-lg transition-all ${
                isBreaking 
                  ? 'bg-red-800/50 text-red-300 cursor-wait'
                  : 'chaos-button text-white'
              }`}
            >
              {isBreaking ? (
                <span className="flex items-center justify-center gap-2">
                  <RefreshCw className="w-5 h-5 animate-spin" />
                  Breaking...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <Zap className="w-5 h-5" />
                  💥 BREAK THIS API!
                </span>
              )}
            </button>
            
            <button
              onClick={fixAPI}
              className="w-full py-3 rounded-xl bg-green-500/20 text-green-400 font-semibold hover:bg-green-500/30 transition-all"
            >
              🔧 Reset to Stable
            </button>

            <button
              onClick={triggerRequest}
              className="w-full py-3 rounded-xl bg-purple-500/20 text-purple-400 font-semibold hover:bg-purple-500/30 transition-all"
            >
              🚀 Trigger Request
            </button>
          </div>

          {/* Schema Changes */}
          {mockMode === 'drifted' && (
            <div className="mt-4 p-3 bg-red-500/10 rounded-lg border border-red-500/30">
              <div className="text-xs text-red-400 font-semibold mb-2">⚠️ Schema Changed:</div>
              <div className="text-xs text-slate-400 space-y-1">
                <div>user_id → uid</div>
                <div>name → full_name</div>
                <div>email → email_address</div>
              </div>
            </div>
          )}
        </div>

        {/* MIDDLE PANE: Agent Brain (The Magic) */}
        <div className="glass-card p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <Brain className="w-5 h-5 text-purple-400" />
              Agent Brain
            </h2>
            <button
              onClick={clearStream}
              className="p-2 rounded-lg bg-slate-700/50 hover:bg-slate-700 transition-colors"
            >
              <Trash2 className="w-4 h-4 text-slate-400" />
            </button>
          </div>

          {/* Human in the Loop Toggle */}
          <div className="flex items-center justify-between p-3 bg-slate-800/50 rounded-lg mb-4">
            <div className="flex items-center gap-2">
              <Shield className="w-4 h-4 text-amber-400" />
              <span className="text-sm">Human Approval</span>
            </div>
            <button
              onClick={toggleHumanInLoop}
              className="transition-transform hover:scale-110"
            >
              {humanInLoop ? (
                <ToggleRight className="w-8 h-8 text-green-400" />
              ) : (
                <ToggleLeft className="w-8 h-8 text-slate-500" />
              )}
            </button>
          </div>

          {/* Thought Stream */}
          <div className="flex-1 overflow-y-auto space-y-2 pr-2 max-h-[400px]">
            {thoughts.length === 0 ? (
              <div className="text-center text-slate-500 py-8">
                <Brain className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>Agent is waiting...</p>
                <p className="text-xs mt-1">Break the API to see healing in action!</p>
              </div>
            ) : (
              thoughts.map((thought) => {
                const style = thoughtStyles[thought.type] || thoughtStyles.info;
                return (
                  <div
                    key={thought.id}
                    className={`thought-bubble p-3 rounded-lg border ${style.bg} animate-fade-in`}
                  >
                    <div className="flex items-start gap-2">
                      <span className="text-lg">{style.icon}</span>
                      <div className="flex-1 min-w-0">
                        <p className={`text-sm ${style.color}`}>
                          {thought.message}
                        </p>
                        <div className="flex items-center gap-3 mt-1">
                          {thought.confidence != null && (
                            <span className="text-xs text-slate-500">
                              Confidence: {(thought.confidence * 100).toFixed(0)}%
                            </span>
                          )}
                          {thought.cost_usd != null && (
                            <span className="text-xs text-green-500 font-mono">
                              ${thought.cost_usd.toFixed(4)}
                            </span>
                          )}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
            <div ref={thoughtsEndRef} />
          </div>

          {/* Approval Buttons */}
          {pendingApproval && (
            <div className="mt-4 p-4 bg-amber-500/10 rounded-lg border border-amber-500/30 animate-pulse">
              <p className="text-sm text-amber-400 mb-3 font-semibold">
                ⏸️ Agent needs your approval!
              </p>
              <div className="flex gap-3">
                <button
                  onClick={() => handleApproval(true)}
                  className="flex-1 py-2 rounded-lg bg-green-500/20 text-green-400 font-semibold hover:bg-green-500/30"
                >
                  ✓ Approve
                </button>
                <button
                  onClick={() => handleApproval(false)}
                  className="flex-1 py-2 rounded-lg bg-red-500/20 text-red-400 font-semibold hover:bg-red-500/30"
                >
                  ✗ Reject
                </button>
              </div>
            </div>
          )}
        </div>

        {/* RIGHT PANE: Live Result (The Proof) */}
        <div className="glass-card p-6 flex flex-col">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold flex items-center gap-2">
              <CheckCircle className="w-5 h-5 text-green-400" />
              Result
            </h2>
            {lastResponse?.healed ? (
              <span className="px-3 py-1 rounded-full text-xs font-medium bg-green-500/20 text-green-400 animate-pulse">
                ✨ HEALED
              </span>
            ) : transformedData && mockMode === 'stable' ? (
              <span className="px-3 py-1 rounded-full text-xs font-medium bg-blue-500/20 text-blue-400">
                ✓ VALID
              </span>
            ) : null}
          </div>

          {/* Diff View - Shows comparison when healed, single view when stable */}
          {transformedData ? (
            <div className="flex-1 overflow-auto">
              {/* Show vertical diff view when healed (drifted mode) */}
              {lastResponse?.healed && originalData ? (
                <div className="space-y-3">
                  {/* BEFORE - Original Broken Response */}
                  <div className="relative">
                    <div className="absolute -left-1 top-0 bottom-0 w-1 bg-red-500 rounded-full" />
                    <div className="pl-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs font-bold rounded">
                          BEFORE
                        </span>
                        <span className="text-xs text-red-400">
                          ❌ Broken Schema from API
                        </span>
                      </div>
                      <div className="bg-red-500/10 rounded-lg p-3 text-xs font-mono overflow-auto border border-red-500/30 max-h-[140px]">
                        <pre className="text-red-300/80">
                          {JSON.stringify(originalData, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>

                  {/* Arrow showing transformation */}
                  <div className="flex items-center justify-center py-1">
                    <div className="flex items-center gap-2 px-4 py-2 bg-purple-500/20 rounded-full border border-purple-500/30">
                      <span className="text-purple-400 text-sm font-semibold">🤖 AI Fixed</span>
                      <svg className="w-4 h-4 text-purple-400 animate-bounce" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 14l-7 7m0 0l-7-7m7 7V3" />
                      </svg>
                    </div>
                  </div>

                  {/* AFTER - Fixed Response */}
                  <div className="relative">
                    <div className="absolute -left-1 top-0 bottom-0 w-1 bg-green-500 rounded-full" />
                    <div className="pl-4">
                      <div className="flex items-center gap-2 mb-2">
                        <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs font-bold rounded">
                          AFTER
                        </span>
                        <span className="text-xs text-green-400">
                          ✓ Healed by Agent
                        </span>
                      </div>
                      <div className="bg-green-500/10 rounded-lg p-3 text-xs font-mono overflow-auto border border-green-500/30 max-h-[140px] glow-success">
                        <pre className="text-green-300">
                          {JSON.stringify(transformedData, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>

                  {/* Mapping Details - Compact */}
                  <div className="p-3 bg-purple-500/10 rounded-lg border border-purple-500/30">
                    <div className="text-xs text-purple-400 font-semibold mb-2">
                      🔗 Mappings Applied:
                    </div>
                    <div className="flex flex-wrap gap-2 text-xs">
                      <span className="px-2 py-1 bg-slate-800 rounded text-slate-300">uid → user_id</span>
                      <span className="px-2 py-1 bg-slate-800 rounded text-slate-300">full_name → name</span>
                      <span className="px-2 py-1 bg-slate-800 rounded text-slate-300">email_address → email</span>
                      <span className="px-2 py-1 bg-slate-800 rounded text-slate-300">registered_date → created_at</span>
                    </div>
                  </div>
                </div>
              ) : (
                /* Show single response when in stable mode (no healing needed) */
                <div className="mb-4">
                  <div className="text-xs text-green-400 font-semibold mb-2">
                    ✓ API Response {mockMode === 'stable' && '(No healing needed)'}
                  </div>
                  <div className="bg-green-500/10 rounded-lg p-3 text-xs font-mono overflow-auto border border-green-500/30 max-h-[300px]">
                    <pre className="text-slate-300">
                      {JSON.stringify(transformedData, null, 2)}
                    </pre>
                  </div>
                  {mockMode === 'stable' && (
                    <div className="mt-3 p-3 bg-blue-500/10 rounded-lg border border-blue-500/30">
                      <p className="text-xs text-blue-400">
                        💡 Schema matches expected format. Click "Break API" to simulate schema drift!
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div className="flex-1 flex items-center justify-center text-slate-500">
              <div className="text-center">
                <Power className="w-12 h-12 mx-auto mb-3 opacity-30" />
                <p>No results yet</p>
                <p className="text-xs mt-1">Click "Trigger Request" to see the API response!</p>
              </div>
            </div>
          )}

          {/* Response Status */}
          {lastResponse && (
            <div className={`mt-4 p-4 rounded-lg ${
              lastResponse.healed 
                ? 'bg-green-500/10 border border-green-500/30 glow-success'
                : 'bg-slate-500/10 border border-slate-500/30'
            }`}>
              <div className="flex items-center justify-between">
                <div>
                  <div className="text-xs text-slate-400">Status</div>
                  <div className={`text-2xl font-bold ${
                    lastResponse.status_code === 200 ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {lastResponse.status_code}
                  </div>
                </div>
                {lastResponse.healing_details && (
                  <div className="text-right">
                    <div className="text-xs text-slate-400">Cache</div>
                    <div className={`text-sm font-semibold ${
                      lastResponse.healing_details.from_cache ? 'text-cyan-400' : 'text-amber-400'
                    }`}>
                      {lastResponse.healing_details.from_cache ? 'HIT ⚡' : 'MISS'}
                    </div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Cost Counter (Bottom Right) */}
      <div className="fixed bottom-6 right-6 glass-card px-4 py-3 flex items-center gap-3">
        <DollarSign className="w-5 h-5 text-green-400" />
        <div>
          <div className="text-xs text-slate-400">Session Cost</div>
          <div className="text-lg font-mono text-green-400">
            ${(stats?.total_cost_usd || 0).toFixed(4)}
          </div>
        </div>
      </div>
    </div>
  );
}

// Mapping Row Component
function MappingRow({ source, target, confidence }: { source: string; target: string; confidence: number }) {
  const confidenceColor = confidence >= 0.8 ? 'text-green-400' : confidence >= 0.6 ? 'text-yellow-400' : 'text-red-400';
  
  return (
    <div className="flex items-center gap-2 text-sm">
      <code className="px-2 py-1 bg-red-500/20 text-red-400 rounded">{source}</code>
      <ArrowRight className="w-4 h-4 text-slate-500" />
      <code className="px-2 py-1 bg-green-500/20 text-green-400 rounded">{target}</code>
      <span className={`text-xs font-mono ${confidenceColor}`}>
        {(confidence * 100).toFixed(0)}%
      </span>
    </div>
  );
}
