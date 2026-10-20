# 📡 Wi-Fi CSI 기반 실시간 낙상 감지 시스템 (Real-time Fall Detection)

> **"보이지 않는 Wi-Fi 파동(CSI)으로 일상의 안전을 모니터링합니다."**
> 
> 카메라나 웨어러블 기기 없이, 공간을 흐르는 무선 통신 신호의 간섭 패턴을 딥러닝으로 분석하여 실시간으로 낙상 사고를 감지하는 비전 접촉(Vision-less & Device-free) 모니터링 시스템입니다.

<br/>

## 🎓 Project Info
- **소속:** ICT폴리텍대학 AI네트워크과
- **구분:** 2026년도 졸업작품 (3조)
- **참여 인원:** [박기현 안규민 이병현 주수민]
- **개발 기간:** 2026. 08 ~ 2026. 10

### ⚠️ Disclaimer (비상업적 용도 안내)
본 프로젝트는 대학 정규 교육과정의 일환으로 기술적 구현 가능성을 검증하기 위해 개발된 학술 및 연구 목적의 졸업작품입니다.
실제 의료 현장이나 보안 시스템 등 상업적/사업적 활용 용도로 제작되지 않았으며, 어떠한 영리적 목적으로도 사용되지 않음을 명시합니다.

<br/>

## ✨ Core Features
- **다중 디바이스 동기화:** 4대의 ESP32-S3 보드(Rx1~Rx4)를 활용한 입체적 채널 상태 정보(CSI) 수집
- **경량화된 실시간 AI 추론:** CNN-LSTM 아키텍처를 적용하여 100 타임스텝 단위의 연속된 시계열 파동 데이터를 0.1초 단위로 분석
- **지연 없는 대시보드:** UDP와 WebSocket을 결합한 백엔드 아키텍처로 실시간 낙상 확률을 렌더링하는 React UI 구현

<br/>

## 👾​프로젝트 진행과정 Notion Link
https://app.notion.com/p/3fd0b7319f398093bd28fc5afafcabb9

<br/>

## 🛠️ Tech Stack
- **Hardware & IoT:** ESP32-S3, C++, Wi-Fi CSI, UDP Socket
- **AI & Data:** Python 3.11, PyTorch (CNN-LSTM), Scikit-learn, Numpy
- **Backend:** FastAPI, Uvicorn, WebSockets
- **Frontend:** React, TypeScript, Vite, Tailwind CSS
