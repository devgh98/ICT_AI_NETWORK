import socket

UDP_IP = "192.168.0.5"
UDP_PORT = 8888

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind((UDP_IP, UDP_PORT))

print(f"=== [통신 테스트] {UDP_IP}:{UDP_PORT} 수신 대기 중 ===")

while True:
    data, addr = sock.recvfrom(4096)
    print(f"[{addr[0]}] 에서 데이터 수신 성공! (크기: {len(data)} bytes)")