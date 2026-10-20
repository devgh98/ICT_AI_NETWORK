import React, { useEffect, useState } from 'react';

interface FallData {
  status: string;
  prob: number;
}

const App: React.FC = () => {
  const [data, setData] = useState<FallData>({ status: '연결 중...', prob: 0 });
  const [isConnected, setIsConnected] = useState<boolean>(false);

  useEffect(() => {
    // FastAPI 웹소켓 서버로 연결
    const ws = new WebSocket('ws://localhost:8000/ws');

    ws.onopen = () => setIsConnected(true);
    
    ws.onmessage = (event) => {
      const parsedData: FallData = JSON.parse(event.data);
      setData(parsedData);
    };

    ws.onclose = () => setIsConnected(false);

    return () => ws.close();
  }, []);

  const isFallDetected = data.status.includes('낙상');

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-xl w-full max-w-md overflow-hidden">
        
        {/* 헤더 부분 */}
        <div className={`p-6 text-white text-center transition-colors duration-300 ${isFallDetected ? 'bg-red-600' : 'bg-blue-600'}`}>
          <h1 className="text-2xl font-bold tracking-wider">CSI Fall Detection</h1>
          <p className="text-sm opacity-80 mt-1">
            {isConnected ? '🟢 실시간 모니터링 중' : '🔴 서버 연결 끊김'}
          </p>
        </div>

        {/* 상태 표시 부분 */}
        <div className="p-8 text-center">
          <div className="mb-4">
            <span className="text-gray-500 text-sm font-semibold">현재 상태</span>
            <h2 className={`text-4xl font-extrabold mt-2 ${isFallDetected ? 'text-red-600 animate-pulse' : 'text-gray-800'}`}>
              {data.status}
            </h2>
          </div>

          {/* 확률 프로그래스 바 */}
          <div className="mt-8">
            <div className="flex justify-between text-sm font-medium mb-2 text-gray-600">
              <span>낙상 확률</span>
              <span>{data.prob.toFixed(1)}%</span>
            </div>
            <div className="w-full bg-gray-200 rounded-full h-4 overflow-hidden">
              <div
                className={`h-4 transition-all duration-300 ease-out ${isFallDetected ? 'bg-red-500' : 'bg-blue-500'}`}
                style={{ width: `${data.prob}%` }}
              ></div>
            </div>
          </div>
        </div>
        
      </div>
    </div>
  );
};

export default App;