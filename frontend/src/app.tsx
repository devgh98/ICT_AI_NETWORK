import React, { useEffect, useState } from 'react';
import { 
  LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, Legend 
} from 'recharts';
import { Activity, ShieldAlert, CheckCircle2, Wifi, Radio } from 'lucide-react';

interface Signals {
  Rx1: number;
  Rx2: number;
  Rx3: number;
  Rx4: number;
}

interface FallData {
  status: string;
  prob: number;
  signals: Signals;
}

interface ChartPoint {
  time: string;
  prob: number;
  Rx1: number;
  Rx2: number;
  Rx3: number;
  Rx4: number;
}

const App: React.FC = () => {
  const [data, setData] = useState<FallData>({
    status: '대기 중...',
    prob: 0,
    signals: { Rx1: 0, Rx2: 0, Rx3: 0, Rx4: 0 }
  });
  const [isConnected, setIsConnected] = useState<boolean>(false);
  const [history, setHistory] = useState<ChartPoint[]>([]);

  useEffect(() => {
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => setIsConnected(true);
    
    ws.onmessage = (event) => {
      const parsedData: FallData = JSON.parse(event.data);
      setData(parsedData);

      const now = new Date();
      const timeStr = `${now.getSeconds().toString().padStart(2, '0')}.${Math.floor(now.getMilliseconds() / 100)}`;

      const newPoint: ChartPoint = {
        time: timeStr,
        prob: parsedData.prob,
        Rx1: parsedData.signals.Rx1,
        Rx2: parsedData.signals.Rx2,
        Rx3: parsedData.signals.Rx3,
        Rx4: parsedData.signals.Rx4,
      };

      // 최근 30개의 히스토리 포인트 유지 (실시간 차트 스크롤)
      setHistory((prev) => [...prev.slice(-29), newPoint]);
    };

    ws.onclose = () => setIsConnected(false);

    return () => ws.close();
  }, []);

  const isFallDetected = data.status.includes('낙상');

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 p-6">
      {/* 헤더 */}
      <header className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center pb-6 mb-6 border-b border-slate-800 gap-4">
        <div>
          <div className="flex items-center gap-2">
            <Radio className="w-7 h-7 text-indigo-400" />
            <h1 className="text-2xl font-bold bg-gradient-to-r from-indigo-400 to-cyan-400 bg-clip-text text-transparent">
              Wi-Fi CSI Real-time Fall Detection
            </h1>
          </div>
          <p className="text-sm text-slate-400 mt-1">
            ICT폴리텍대학 AI네트워크과 | 2026년도 Graduation Project (Group 3)
          </p>
        </div>
        
        <div className="flex items-center gap-3 bg-slate-800/80 px-4 py-2 rounded-full border border-slate-700">
          <Wifi className={`w-4 h-4 ${isConnected ? 'text-emerald-400 animate-pulse' : 'text-rose-500'}`} />
          <span className="text-xs font-semibold tracking-wide">
            {isConnected ? 'SYSTEM ONLINE (8888 UDP)' : 'DISCONNECTED'}
          </span>
        </div>
      </header>

      {/* 메인 대시보드 그리드 */}
      <main className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-3 gap-6">
        
        {/* 좌측 카드: 실시간 상태 및 확률 */}
        <div className="space-y-6">
          {/* 상태 위젯 */}
          <div className={`p-6 rounded-2xl border transition-all duration-300 ${
            isFallDetected 
              ? 'bg-rose-950/40 border-rose-500/50 shadow-lg shadow-rose-950/50' 
              : 'bg-slate-800/50 border-slate-700/60'
          }`}>
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Current Status</span>
            <div className="flex items-center gap-4 mt-3">
              {isFallDetected ? (
                <ShieldAlert className="w-12 h-12 text-rose-500 animate-bounce" />
              ) : (
                <CheckCircle2 className="w-12 h-12 text-emerald-400" />
              )}
              <div>
                <h2 className={`text-3xl font-extrabold ${isFallDetected ? 'text-rose-400' : 'text-slate-100'}`}>
                  {data.status}
                </h2>
                <p className="text-xs text-slate-400 mt-1">
                  {isFallDetected ? 'Emergency Event Detected!' : 'Normal Activity Monitored'}
                </p>
              </div>
            </div>
          </div>

          {/* 게이지 바 위젯 */}
          <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700/60">
            <div className="flex justify-between items-center mb-2">
              <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Fall Probability</span>
              <span className={`text-xl font-black ${isFallDetected ? 'text-rose-400' : 'text-indigo-400'}`}>
                {data.prob.toFixed(1)}%
              </span>
            </div>
            <div className="w-full bg-slate-700/50 rounded-full h-3 overflow-hidden">
              <div
                className={`h-3 transition-all duration-300 ${isFallDetected ? 'bg-rose-500' : 'bg-indigo-500'}`}
                style={{ width: `${Math.min(data.prob, 100)}%` }}
              ></div>
            </div>
          </div>

          {/* 수신 단말 실시간 신호 레벨 */}
          <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700/60">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-400 block mb-4">
              Receiver Nodes Power (Avg)
            </span>
            <div className="grid grid-cols-2 gap-3">
              {(['Rx1', 'Rx2', 'Rx3', 'Rx4'] as const).map((node) => (
                <div key={node} className="p-3 bg-slate-900/60 rounded-xl border border-slate-800 flex justify-between items-center">
                  <span className="text-xs font-bold text-slate-400">{node}</span>
                  <span className="text-sm font-semibold text-cyan-400">
                    {data.signals[node]?.toFixed(1) || '0.0'}
                  </span>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 우측 영역: 실시간 대시보드 차트 */}
        <div className="lg:col-span-2 space-y-6">
          
          {/* 차트 1: 4개 Receiver CSI 실시간 신호 파동 */}
          <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700/60">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-4 h-4 text-cyan-400" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Real-Time CSI Subcarrier Waveform (Rx1 ~ Rx4)
              </h3>
            </div>
            <div className="h-56 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history}>
                  <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#64748b" tick={{ fontSize: 10 }} domain={['auto', 'auto']} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155' }} />
                  <Legend wrapperStyle={{ fontSize: '11px' }} />
                  <Line type="monotone" dataKey="Rx1" stroke="#818cf8" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="Rx2" stroke="#38bdf8" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="Rx3" stroke="#34d399" dot={false} strokeWidth={2} />
                  <Line type="monotone" dataKey="Rx4" stroke="#f43f5e" dot={false} strokeWidth={2} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* 차트 2: 낙상 확률 실시간 추이 */}
          <div className="p-6 rounded-2xl bg-slate-800/50 border border-slate-700/60">
            <div className="flex items-center gap-2 mb-4">
              <Activity className="w-4 h-4 text-rose-400" />
              <h3 className="text-sm font-bold uppercase tracking-wider text-slate-300">
                Fall Detection Probability Trend (%)
              </h3>
            </div>
            <div className="h-44 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history}>
                  <XAxis dataKey="time" stroke="#64748b" tick={{ fontSize: 10 }} />
                  <YAxis stroke="#64748b" domain={[0, 100]} tick={{ fontSize: 10 }} />
                  <Tooltip contentStyle={{ backgroundColor: '#0f172a', borderColor: '#334155' }} />
                  <Line type="monotone" dataKey="prob" stroke="#f43f5e" dot={false} strokeWidth={2.5} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

      </main>
    </div>
  );
};

export default App;