import torch
import torch.nn as nn
import numpy as np
import socket
import threading
import asyncio
import time
from collections import deque
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ==========================================
# 1. AI 모델 아키텍처 정의
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

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

latest_result = {
    "status": "대기 중...",
    "prob": 0.0,
    "signals": {"Rx1": 0.0, "Rx2": 0.0, "Rx3": 0.0, "Rx4": 0.0}
}

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
        print(f"⚠️ 모델 로드 실패: {e}")
        return

    # ====================================================
    # [메인 모드] 실제 하드웨어 통신 (ESP32 수신)
    # ====================================================
    # 노트북 와이파이 고정 IP로 변경 필수! (예: 192.168.0.5)
    UDP_IP = "192.168.0.5" 
    UDP_PORT = 8888    
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_IP, UDP_PORT))
    print(f"📡 [실제 수신 모드] ESP32 데이터 수신 대기 중... ({UDP_IP}:{UDP_PORT})")

    sliding_window = deque(maxlen=100)
    current_frame = {k: np.zeros(64) for k in ['Rx1', 'Rx2', 'Rx3', 'Rx4']}

    while True:
        data, addr = sock.recvfrom(4096)
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

                signals = {
                    "Rx1": float(np.mean(current_frame['Rx1'])),
                    "Rx2": float(np.mean(current_frame['Rx2'])),
                    "Rx3": float(np.mean(current_frame['Rx3'])),
                    "Rx4": float(np.mean(current_frame['Rx4']))
                }

                if len(sliding_window) == 100:
                    input_tensor = torch.tensor(np.array(sliding_window), dtype=torch.float32).unsqueeze(0).to(device)
                    
                    with torch.no_grad():
                        output = model(input_tensor)
                        probability = torch.softmax(output, dim=1)
                        pred_class = torch.argmax(probability, dim=1).item()
                        fall_prob = probability[0][1].item() * 100

                    latest_result = {
                        "status": "낙상 감지!!" if pred_class == 1 else "정상 상태",
                        "prob": round(fall_prob, 1),
                        "signals": signals
                    }
                else:
                    latest_result = {
                        "status": f"데이터 수집 중... ({len(sliding_window)}%)",
                        "prob": 0.0,
                        "signals": signals
                    }
        else:
            pass # 패킷 잘림 에러는 조용히 무시하여 로그 깔끔하게 유지

@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=udp_inference_loop, daemon=True)
    thread.start()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_json(latest_result)
            await asyncio.sleep(0.1)
    except Exception:
        pass

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)