import torch
import torch.nn as nn
import numpy as np
import socket
import time
from collections import deque

# ==========================================
# 1. 모델 아키텍처 정의 (학습된 모델과 구조 100% 동일)
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
# 2. 실시간 무선 데이터 파이프라인 (C++ 규격 완벽 대응)
# ==========================================
def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🔄 연산 장치: {device} 로드 중...")

    model = BuoyCNNLSTM().to(device)
    model_path = 'C:/CSI_FALL_DETECTION/csi_data/Preprocessed/buoy_cnn_lstm_model.pth'
    
    try:
        model.load_state_dict(torch.load(model_path, map_location=device))
        model.eval()
        print("✅ 인공지능 모델 로드 완료!")
    except Exception as e:
        print(f"❌ 모델 로드 실패: {e}")
        return

    # ★ C++ 코드에 맞춘 UDP 포트 설정 ★
    UDP_IP = "0.0.0.0" 
    UDP_PORT = 8888    
    
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.bind((UDP_IP, UDP_PORT))
        print(f"📡 무선 수신 대기 중... (포트: {UDP_PORT})")
        print("   => 4대의 ESP32 보드에 전원을 연결해주세요.")
    except Exception as e:
        print(f"⚠️ 소켓을 열 수 없습니다: {e}")
        return

    window_size = 100 
    sliding_window = deque(maxlen=window_size)
    
    current_frame = {
        'Rx1': np.zeros(64),
        'Rx2': np.zeros(64),
        'Rx3': np.zeros(64),
        'Rx4': np.zeros(64)
    }

    # 무한 루프 
    while True:
        data, addr = sock.recvfrom(4096)
        raw_line = data.decode('utf-8', errors='ignore').strip()
        parts = raw_line.split(',')
        
        # ★ C++ 코드 대응: "Rx1, 23, 45, ..." 형태이므로 최소 65칸(기기이름 1 + 파동 64) 필요
        if len(parts) >= 65:
            dev_id = parts[0].strip() # 0번째 칸이 기기 이름
            
            if dev_id in current_frame:
                try:
                    # 1번째 칸부터 64개를 잘라옴
                    subcarriers = np.array(parts[1:65], dtype=np.float32)
                    current_frame[dev_id] = subcarriers
                except ValueError:
                    continue
                    
            if dev_id == 'Rx1':
                frame_array = np.array([
                    current_frame['Rx1'],
                    current_frame['Rx2'],
                    current_frame['Rx3'],
                    current_frame['Rx4']
                ])
                sliding_window.append(frame_array)

                if len(sliding_window) == window_size:
                    input_data = np.array(sliding_window)
                    input_tensor = torch.tensor(input_data, dtype=torch.float32).unsqueeze(0).to(device)

                    with torch.no_grad():
                        output = model(input_tensor)
                        probability = torch.softmax(output, dim=1)
                        pred_class = torch.argmax(probability, dim=1).item()
                        fall_prob = probability[0][1].item() * 100

                    if pred_class == 1:
                        print(f"🚨 [경보] 낙상 감지!! (확률: {fall_prob:.1f}%) 🚨")
                    else:
                        print(f"🟢 정상 상태 (낙상 확률: {fall_prob:.1f}%)", end='\r')

if __name__ == "__main__":
    main()