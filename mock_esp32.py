import socket
import time
import csv

# ==========================================
# 1. 파일 경로 설정 (올려주신 파일의 실제 경로로 변경하세요)
# ==========================================
CSV_FILE_PATH = 'C:/CSI_FALL_DETECTION/csi_data/csi_fall_sync.csv'

UDP_IP = "127.0.0.1"
UDP_PORT = 8888

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
print(f"🚀 [CSV 데이터 리플레이] '{CSV_FILE_PATH}' 파일의 실제 정상 데이터를 전송합니다...")

expected_devices = ['Rx1', 'Rx2', 'Rx3', 'Rx4']
valid_packets = []

# ==========================================
# 2. CSV 파일에서 실제 학습 데이터 추출
# ==========================================
try:
    with open(CSV_FILE_PATH, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0: continue # 헤더 건너뛰기
            
            row = [str(x).strip() for x in row]
            for dev in expected_devices:
                if dev in row:
                    dev_idx = row.index(dev)
                    # 기기명 뒤에 64개의 파동 데이터가 온전히 있는지 확인
                    if (len(row) - dev_idx - 1) >= 64:
                        subs = row[dev_idx + 1 : dev_idx + 65]
                        packet_string = f"{dev}," + ",".join(subs)
                        valid_packets.append(packet_string)
                    break
    print(f"✅ 총 {len(valid_packets)}개의 정상 패킷을 성공적으로 불러왔습니다.")
except FileNotFoundError:
    print("⚠️ 에러: CSV 파일을 찾을 수 없습니다. 경로를 확인해주세요.")
    exit()

# ==========================================
# 3. 추출한 데이터를 백엔드로 무한 반복 전송
# ==========================================
print("📡 전송 시작! (Ctrl+C를 누르면 종료됩니다)")
idx = 0

while True:
    packet = valid_packets[idx]
    sock.sendto(packet.encode('utf-8'), (UDP_IP, UDP_PORT))
    
    idx += 1
    if idx >= len(valid_packets):
        idx = 0 # 끝까지 다 쏘면 처음부터 다시 재생
    
    # ESP32와 동일하게 아주 빠른 속도로 전송 (0.02초 간격)
    time.sleep(0.02)