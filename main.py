import torch
import torch.nn as nn
import numpy as np
import socket
import threading
import asyncio
import time
import random
from collections import deque
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ==========================================
# 0. 시뮬레이션 모드 스위치
# ==========================================
# True: ESP32 없이 가상의 파동을 만들어 UI를 테스트합니다.
# False: 실제 ESP32에서 UDP 데이터를 수신하여 AI 모델로 판독합니다.
SIMULATION_MODE = False  

# ==========================================
# 1. 모델 아키텍처 정의
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
    
    # 모델 로드
    model = BuoyCNNLSTM().to(device)
    model_path = 'C:/workspace/ICT_AI_NETWORK/csi_data/Preprocessed/buoy_cnn_lstm_model.pth'
    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.eval()
        print("✅ [백엔드] AI 모델 로드 완료!")
    except Exception as e:
        print(f"⚠️ 모델 로드 실패 (시뮬레이션 모드에서는 무시됩니다): {e}")
        if not SIMULATION_MODE:
            return

    # ----------------------------------------------------
    # [모드 A] 시뮬레이션 모드 가동 (UI 테스트용 가상 데이터)
    # ----------------------------------------------------
    if SIMULATION_MODE:
        print("⚠️ [시뮬레이션 모드] ESP32 없이 가상의 파동 데이터를 생성합니다...")
        while True:
            # 시간(초)을 기준으로 10초 중 8초는 정상, 2초는 낙상 상태 연출
            current_time = time.time()
            is_fall_event = (int(current_time) % 10) >= 8  

            if is_fall_event:
                # 낙상 시: 확률 급증 및 신호 요동
                status = "낙상 감지!!"
                prob = random.uniform(85.5, 99.9)
                signals = {
                    "Rx1": random.uniform(50, 80),
                    "Rx2": random.uniform(10, 30),
                    "Rx3": random.uniform(60, 90),
                    "Rx4": random.uniform(40, 70)
                }
            else:
                # 정상 시: 낮은 확률 및 안정적인 파동
                status = "정상 상태"
                prob = random.uniform(0.1, 12.5)
                signals = {
                    "Rx1": random.uniform(30, 35),
                    "Rx2": random.uniform(32, 36),
                    "Rx3": random.uniform(28, 33),
                    "Rx4": random.uniform(31, 35)
                }

            latest_result = {
                "status": status,
                "prob": round(prob, 1),
                "signals": signals
            }
            time.sleep(0.1) # 0.1초마다 갱신 (10Hz)

    # ----------------------------------------------------
    # [모드 B] 실제 하드웨어 통신 모드
    # ----------------------------------------------------
    else:
        UDP_IP = "192.168.0.5" 
        UDP_PORT = 8888    
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((UDP_IP, UDP_PORT))
        print(f"📡 [실제 수신 모드] 무선 수신 대기 중... (포트: {UDP_PORT})")

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
                    
                    # [수정 1] 100개가 다 차기 전까지만 '수집 중' 로그 띄우기
                    if len(sliding_window) < 100:
                        print(f"[{addr[0]}] 📊 데이터 수집 중... ({len(sliding_window)}/100)")
                    elif len(sliding_window) == 100 and (int(time.time()) % 2 == 0):
                        # 터미널 도배 방지: 100개가 차면 2초에 한 번만 '실시간 판독 중' 표시
                        print("✅ 실시간 AI 판독 진행 중...")

                    # 그래프용 신호 평균값 추출
                    signals = {
                        "Rx1": float(np.mean(current_frame['Rx1'])),
                        "Rx2": float(np.mean(current_frame['Rx2'])),
                        "Rx3": float(np.mean(current_frame['Rx3'])),
                        "Rx4": float(np.mean(current_frame['Rx4']))
                    }

                    if len(sliding_window) == 100:
                        input_tensor = torch.tensor(np.array(sliding_window), dtype=torch.float32).unsqueeze(0).to(device)
                        
                        # [수정 2] 핵심 추가: 실시간 데이터 정규화 (Z-score Normalization)
                        # 날것의 CSI 데이터를 모델이 학습했던 스케일과 비슷하게 맞춰주어 예측 폭주를 방지합니다.
                        input_mean = torch.mean(input_tensor)
                        input_std = torch.std(input_tensor) + 1e-5
                        input_tensor = (input_tensor - input_mean) / input_std

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
                # [추가] 1460 바이트로 쪼개져서 버려지는 패킷들의 정체를 터미널에 띄워줍니다.
                print(f"⚠️ 규격 미달 패킷 수신 (길이 {len(parts)}): {raw_line[:40]}...")

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