#include <WiFi.h>
#include <esp_wifi.h>
#include <WiFiUdp.h>

const char* ssid = "aiNetwork";       
const char* password = "ainetwork1004!"; 

WiFiUDP udp;
const char* laptop_ip = "192.168.0.3"; 
const int udp_port = 8888;              
const char* device_id = "Rx4";          

volatile int packet_count = 0; 

void _csi_rx_cb(void *ctx, wifi_csi_info_t *info) {
  if (!info || !info->buf || info->len == 0) return;
  
  packet_count++;
  
  char udp_buf[2048];
  int pos = sprintf(udp_buf, "%s,", device_id); 
  for (int i = 0; i < info->len; i++) {
    pos += sprintf(udp_buf + pos, "%d,", info->buf[i]);
  }
  
  udp.beginPacket(laptop_ip, udp_port);
  udp.write((const uint8_t*)udp_buf, pos);
  udp.endPacket();
}

void setup() {
  Serial.begin(115200);
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  while (WiFi.status() != WL_CONNECTED) delay(500);
  Serial.println("WiFi Connected!");
  
  ESP_ERROR_CHECK(esp_wifi_set_csi_rx_cb(&_csi_rx_cb, NULL));
  wifi_csi_config_t csi_config = {
      .lltf_en           = true,
      .htltf_en          = true,
      .stbc_htltf2_en    = true,
      .ltf_merge_en      = true,
      .channel_filter_en = true,
      .manu_scale        = false,
      .shift             = false,
  };
  ESP_ERROR_CHECK(esp_wifi_set_csi_config(&csi_config));
  ESP_ERROR_CHECK(esp_wifi_set_csi(true));
}

void loop() {
  Serial.print("생성 및 전송된 CSI 패킷 수: ");
  Serial.println(packet_count);
  delay(1000); 
}