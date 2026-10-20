import socket
import csv
import time

# UDP 소켓 설정
UDP_IP = "192.168.0.3" # 노트북 IP
UDP_PORT = 8888

# ★ 1. 다운로드 폴더로 경로 절대 지정 (경로에 슬래시(/) 사용)
CSV_FILENAME = 'C:/Users/dook/Downloads/csi_fall_sync.csv'

# 소켓 열기
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))
sock.settimeout(1.0) 

print("📡 ESP32 보드 연결 대기 중...")
input("👉 시연자가 위치에 서면 [Enter] 키를 눌러 수집 시작!\n")
print(f"🔴 [수집 시작] '{CSV_FILENAME}'에 기록됩니다. (종료: Ctrl+C)")

try:
    with open(CSV_FILENAME, mode='a', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(["Timestamp", "Device_ID"] + [f"Sub_{i}" for i in range(64)])
        
        while True:
            try:
                data, addr = sock.recvfrom(4096)
                print(f"🟢 [{addr[0]}] 데이터 수신됨! (길이: {len(data)} bytes)")
            except TimeoutError: 
                print("🔴 1초 경과: 들어온 데이터 없음...")
                continue
            
            current_time = time.time() 
            line = data.decode('utf-8', errors='ignore').strip()
            raw_data = line.split(',')
            clean_data = [x for x in raw_data if x != '']
            
            if len(clean_data) > 2:
                clean_data.insert(0, current_time)
                writer.writerow(clean_data)
                
                # ★ 2. 데이터가 들어오는 즉시 하드디스크(파일)에 강제 기록
                f.flush() 

except KeyboardInterrupt:
    print("\n⏹️ [수집 종료] 파일이 안전하게 닫혔습니다.")
finally:
    sock.close()