import torch
import torch.nn as nn
import numpy as np
import socket
import threading
import asyncio
from collections import deque
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ==========================================
# 1. 모델 아키텍처 정의 (이전과 동일)
# ==========================================
class BuoyCNNLSTM(nn.Module):
    def __init__(self, hidden_dim=64, num_layers=2, num_classes=2):
        super(BuoyCNNLSTM, self).__init__()
        self.feature_extractor = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=(3, 3), padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(1, 2)), 
            nn.Conv2d(16, 32, kernel_size=(3, 3), padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(1, 2)), 
            nn.Flatten()
        )
        self.lstm = nn.LSTM(input_size=2048, hidden_size=hidden_dim, num_layers=num_layers, batch_first=True, dropout=0.2)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, num_classes)
        )
    def forward(self, x):
        batch_size, timesteps, dev, sub = x.size()
        c_in = x.view(batch_size * timesteps, 1, dev, sub)
        c_out = self.feature_extractor(c_in)
        r_in = c_out.view(batch_size, timesteps, -1)
        r_out, _ = self.lstm(r_in)
        return self.fc(r_out[:, -1, :])

# ==========================================
# 2. 전역 상태 및 FastAPI 설정
# ==========================================
app = FastAPI()

# CORS 설정 (React 프론트엔드 접근 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 프론트엔드로 전달할 실시간 전역 상태
latest_result = {"status": "대기 중...", "prob": 0.0}

# ==========================================
# 3. 백그라운드 UDP & AI 추론 스레드
# ==========================================
def udp_inference_loop():
    global latest_result
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    model = BuoyCNNLSTM().to(device)
    model_path = 'C:/CSI_FALL_DETECTION/csi_data/Preprocessed/buoy_cnn_lstm_model.pth'
    
    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.eval()
        print("✅ [백엔드] AI 모델 로드 완료!")
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        return

    UDP_IP = "0.0.0.0" 
    UDP_PORT = 8888    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"📡 [백엔드] 무선 수신 대기 중... (포트: {UDP_PORT})")

    sliding_window = deque(maxlen=100)
    current_frame = {k: np.zeros(64) for k in ['Rx1', 'Rx2', 'Rx3', 'Rx4']}

    while True:
        data, _ = sock.recvfrom(4096)
        raw_line = data.decode('utf-8', errors='ignore').strip()
        parts = raw_line.split(',')
        
        if len(parts) >= 65:
            dev_id = parts[0].strip()
            if dev_id in current_frame:
                try:
                    current_frame[dev_id] = np.array(parts[1:65], dtype=np.float32)
                except ValueError:
                    continue
                    
            if dev_id == 'Rx1':
                frame_array = np.array([current_frame['Rx1'], current_frame['Rx2'], current_frame['Rx3'], current_frame['Rx4']])
                sliding_window.append(frame_array)

                if len(sliding_window) == 100:
                    input_tensor = torch.tensor(np.array(sliding_window), dtype=torch.float32).unsqueeze(0).to(device)
                    with torch.no_grad():
                        output = model(input_tensor)
                        probability = torch.softmax(output, dim=1)
                        pred_class = torch.argmax(probability, dim=1).item()
                        fall_prob = probability[0][1].item() * 100

                    # 예측 결과를 전역 상태에 즉시 갱신
                    latest_result = {
                        "status": "낙상 감지!!" if pred_class == 1 else "정상 상태",
                        "prob": round(fall_prob, 1)
                    }

# ==========================================
# 4. FastAPI 엔드포인트
# ==========================================
@app.on_event("startup")
def startup_event():
    # 서버가 켜질 때 AI 추론 루프를 백그라운드에서 실행
    thread = threading.Thread(target=udp_inference_loop, daemon=True)
    thread.start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # 0.1초마다 프론트엔드로 최신 상태 JSON 전송
            await websocket.send_json(latest_result)
            await asyncio.sleep(0.1)
    except Exception as e:
        print("웹소켓 연결 종료")

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)