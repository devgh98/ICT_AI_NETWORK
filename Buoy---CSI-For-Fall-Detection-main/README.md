<div align="center">

# Buoy &mdash; CSI Fall Detection

**Passive, camera-free fall detection for older adults &mdash; powered by Wi-Fi Channel State Information.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Built at HackDavis](https://img.shields.io/badge/Built%20at-HackDavis-1f6feb.svg)](https://hackdavis.io)
[![Next.js](https://img.shields.io/badge/Next.js-16-black?logo=next.js)](https://nextjs.org)
[![Express](https://img.shields.io/badge/Express-4.18-green?logo=express)](https://expressjs.com)
[![PyTorch](https://img.shields.io/badge/PyTorch-TorchScript-ee4c2c?logo=pytorch)](https://pytorch.org)
[![ESP32](https://img.shields.io/badge/Hardware-ESP32-e7352c?logo=espressif)](https://www.espressif.com)
[![GitHub stars](https://img.shields.io/github/stars/GabeMerc/Buoy---CSI-For-Fall-Detection?style=social)](https://github.com/GabeMerc/Buoy---CSI-For-Fall-Detection)

[**Live Demo Video**](https://www.youtube.com/watch?v=RHlbRHN7XGM) &nbsp;&middot;&nbsp; [**GitHub Repo**](https://github.com/GabeMerc/Buoy---CSI-For-Fall-Detection) &nbsp;&middot;&nbsp; [Frontend (apps/web)](apps/web) &nbsp;&middot;&nbsp; [Backend (apps/server)](apps/server) &nbsp;&middot;&nbsp; [ML Pipeline](fall-detection-training)

</div>

---

## Demo

[![Watch the Buoy demo on YouTube](https://img.youtube.com/vi/RHlbRHN7XGM/maxresdefault.jpg)](https://www.youtube.com/watch?v=RHlbRHN7XGM)

> Click the thumbnail to watch the full walkthrough &mdash; sensor setup, fall detection, escalation flow, and the caregiver dashboard.

---

## Why Buoy

Falls are the leading cause of injury death for adults over 65 in the United States, and most happen at home. Existing solutions force a trade-off:

- **Wearables** are forgotten, taken off, or run out of battery &mdash; and they're often refused by the people who need them most.
- **Cameras** raise serious privacy concerns, especially in bedrooms and bathrooms where many falls occur.

Buoy uses **Wi-Fi Channel State Information (CSI)** to detect falls passively, without cameras, wearables, or anything the user has to remember. Five small ESP32 boards sense the way Wi-Fi signals bend around a moving body, and an on-device ML ensemble decides whether what just happened was a fall. A response and escalation pipeline pages the resident first, then their care circle, and finally surfaces a 911 option to caregivers if no one responds.

---

## Table of Contents

- [How It Works](#how-it-works)
- [Architecture](#architecture)
- [Repository Layout](#repository-layout)
- [Applications](#applications)
- [Incident State Machine](#incident-state-machine)
- [Fall Detection Model](#fall-detection-model)
- [Hardware](#hardware)
- [Getting Started](#getting-started)
- [Deployment](#deployment)
- [Tech Stack](#tech-stack)
- [Team](#team)
- [License](#license)

---

## How It Works

1. **Sense.** One ESP32 transmitter raised above shoulder height broadcasts beacons on Wi-Fi channel 6. Four ESP32 receivers around the room measure how the channel changes packet-by-packet at ~70 Hz across 192 subcarriers.
2. **Classify.** The CSI receiver runs a TorchScript ensemble (CNN spectrogram encoder + LSTM + Transformer) over 9 stacked 6-second windows. Output: binary FALL_IMPACT vs. everything else, with calibrated probabilities.
3. **Escalate.** A fall detection posts to the Express backend, which drives an incident state machine: the resident gets paged first (T1), then the care circle (T2), and finally a 911 prompt is surfaced to caregivers (T3). All transitions stream live to both apps via Pusher.
4. **Respond.** The resident's "I'm OK" or "I need help" short-circuits or accelerates the escalation. Caregivers acknowledge from the dashboard or directly from a WhatsApp message.

---

## Architecture

```
+----------------+        Wi-Fi CSI         +-----------------+      HTTPS       +-----------------+
| ESP32 TX board |  ─────────────────────▶  | ESP32 RX boards |  ─────────────▶  | Express + SQLite|
|  (channel 6)   |    (4 receivers @ ~70Hz) |  + TorchScript  |   POST /falls    |  state machine  |
+----------------+                          +-----------------+                  +─────────────────+
                                                                                         │
                                                                                Pusher / WhatsApp
                                                                                         │
                                                              ┌──────────────────────────┴──────────────────────────┐
                                                              ▼                                                     ▼
                                                   ┌─────────────────────┐                          ┌─────────────────────┐
                                                   │  Buoy Care (PWA)    │                          │ Buoy Dashboard (PWA)│
                                                   │  resident-facing    │                          │  caregiver-facing   │
                                                   └─────────────────────┘                          └─────────────────────┘
```

---

## Repository Layout

```
.
├── apps/
│   ├── server/                      Express + SQLite backend (Railway)
│   │   └── src/
│   │       ├── state-machine.ts     Incident lifecycle + T1/T2/T3 timers
│   │       ├── routes/incidents.ts  Fall intake, respond, ack, escalate
│   │       ├── routes/households.ts Households, caregivers, pause flow
│   │       ├── routes/sensors.ts    CSI telemetry ingestion
│   │       └── sms.ts               Twilio WhatsApp integration
│   └── web/                         Next.js 16 PWA frontend (Vercel)
│       └── app/
│           └── household/[code]/
│               ├── at-risk/         Resident-facing app
│               └── contact/         Caregiver-facing dashboard
│
├── fall-detection-training/         Full ML pipeline
│   ├── firmware/                    ESP32 TX/RX firmware + flash helpers
│   ├── collection/                  Multi-RX session recorder + labeling UI
│   ├── labeling/                    Splits FALL into FALL_IMPACT / FLOORED
│   ├── training/                    LSTM, CNN, ensemble training
│   ├── evaluation/                  LOOCV + event-level evaluation
│   ├── external_data_adapter/      Adapter for the public CSI-HAR dataset
│   └── model/                       Shipped TorchScript ensemble + config
│
├── .env.example                     Environment variable template
├── package.json                     Workspace root (apps/server, apps/web)
└── README.md                        You are here.
```

---

## Applications

### Buoy Care &mdash; resident-facing PWA

Path: `apps/web/app/household/[code]/at-risk`

The Buoy Care app is what the at-risk resident sees on a phone or kiosk. It is intentionally minimal &mdash; large type, two big buttons, no menus.

- Shows live monitoring status (CSI sensor or on-device motion fallback)
- Full-screen alarm with a countdown when a fall is detected
- One-tap responses: "I'm OK" or "I need help"
- Can request a monitoring pause, which the caregiver must approve

### Buoy Dashboard &mdash; caregiver-facing PWA

Path: `apps/web/app/household/[code]/contact`

The dashboard is the care circle's view: family members, neighbors, or paid caregivers.

- Real-time sensor status and floor-plan view
- Receives alerts only after the resident's response window closes &mdash; reduces alert fatigue
- "I'm Responding" acknowledges the alert and sends a WhatsApp message to the resident
- Monitoring pause approval and resume controls
- Full incident history with timestamps and resolution

Both apps are installable PWAs with their own manifest files.

---

## Incident State Machine

The backend drives every incident through a strict, timer-bounded state machine. Timers `T1`, `T2`, `T3` are configurable via environment variables.

```
                                ┌─────────────┐
                                │  DETECTED   │
                                └──────┬──────┘
                                       ▼
                       ┌───────────────────────────────┐
                       │  AWAITING_USER_RESPONSE  (T1) │ ── "I'm OK" ──▶ RESOLVED
                       └───────────────┬───────────────┘
                                       │ T1 expired  OR  user says "help"
                                       ▼
                       ┌───────────────────────────────┐
                       │  CONTACTS_NOTIFIED       (T2) │ ── caregiver acks ──▶ CONTACT_RESPONDING ──▶ RESOLVED
                       └───────────────┬───────────────┘
                                       │ T2 expired, no caregiver responded
                                       ▼
                       ┌───────────────────────────────┐
                       │  ESCALATION_AVAILABLE    (T3) │ ── caregiver triggers ──▶ ESCALATED (911)
                       └───────────────────────────────┘
```

State transitions stream live to both apps via Pusher Channels. Every transition is journaled to SQLite for the incident history.

---

## Fall Detection Model

The shipped model lives in [`fall-detection-training/model/fall_impact_seq9_ensemble/`](fall-detection-training/model/fall_impact_seq9_ensemble) and is loaded as TorchScript at inference time.

| Property | Value |
|---|---|
| Architecture | Ensemble: CNN spectrogram + LSTM + Transformer encoder |
| Input shape | `[1, 9, 32, 49, 21]` &mdash; 9 windows × 32 channels × 49 freq × 21 time |
| Receptive field | 14 seconds (9 stacked 6-second windows, 1 s hop) |
| Classes | Binary &mdash; `FALL_IMPACT` vs. everything else |
| Calibration | Temperature 0.3 |
| Window-level macro-F1 | 0.81 |
| FALL_IMPACT recall @ 0.50 | 91% |
| Event-level F1 @ 0.50 | 0.90 (90% precision / 90% recall, held-out session) |
| Empty-room false alerts | Zero |

Training used **leave-one-session-out cross-validation** across 7 recorded sessions plus the public CSI-HAR dataset (adapted to our 4-RX, 192-subcarrier, ~70 Hz format). Full pipeline and reproduction steps are in [`fall-detection-training/README.md`](fall-detection-training/README.md).

---

## Hardware

| Item | Quantity | Notes |
|---|---|---|
| ESP32 dev board | 5 | 1 transmitter, 4 receivers |
| USB cables | 5 | 921600 baud serial to host |
| Tripod / shelf for TX | 1 | Raised above shoulder height for best coverage |

- Wi-Fi channel: **6**
- Subcarriers per packet: **192**
- Packet rate: **~70 Hz**
- Firmware source and flashing helpers: [`fall-detection-training/firmware/`](fall-detection-training/firmware)

---

## Getting Started

### Prerequisites

- **Node.js** 20 or newer
- **Python** 3.12+ (only required for training / data collection)
- A **Pusher Channels** app for real-time updates
- A **Twilio** account with WhatsApp messaging enabled

### 1. Clone and install

```bash
git clone https://github.com/GabeMerc/Buoy---CSI-For-Fall-Detection.git
cd Buoy---CSI-For-Fall-Detection
npm install
```

### 2. Configure environment

Copy the example file and fill in your credentials:

```bash
cp .env.example .env
```

```env
T1_MS=30000     # Resident response window
T2_MS=45000     # Caregiver acknowledgement window
T3_MS=60000     # 911 prompt window

PUSHER_APP_ID=
PUSHER_KEY=
PUSHER_SECRET=
PUSHER_CLUSTER=us2
NEXT_PUBLIC_PUSHER_KEY=
NEXT_PUBLIC_PUSHER_CLUSTER=us2

TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
TWILIO_FROM=
TWILIO_MODE=whatsapp

BASE_URL=http://localhost:3000
PORT=3001
```

### 3. Run locally

From the repo root, in two terminals:

```bash
# Terminal 1 — backend
cd apps/server
npm install
npm run dev

# Terminal 2 — frontend
cd apps/web
npm install
npm run dev
```

Or from the workspace root in one go:

```bash
npm run dev
```

Once both are running:

- **Dashboard (caregiver):** http://localhost:3000/household/483920/contact
- **Care app (resident):** http://localhost:3000/household/483920/at-risk

### 4. (Optional) Run the ML pipeline

```bash
cd fall-detection-training
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python evaluation/eval_seq9_ensemble.py
```

See [`fall-detection-training/README.md`](fall-detection-training/README.md) for the full training, labeling, and evaluation workflow.

---

## Deployment

| Service | Platform | Config |
|---|---|---|
| Backend | Railway | [`apps/server/railway.toml`](apps/server/railway.toml) |
| Frontend | Vercel | [`apps/web/next.config.ts`](apps/web/next.config.ts) |

Set every environment variable in each platform's dashboard. Critically, the backend's `BASE_URL` must point at the public Railway URL so that links inside outgoing WhatsApp messages resolve.

---

## Tech Stack

**Frontend**
- Next.js 16 (App Router) + React 19
- Tailwind CSS v4
- Pusher JS client
- Installable PWA (separate manifests for care vs. dashboard)

**Backend**
- Express 4
- better-sqlite3 (zero-config local persistence)
- Pusher server SDK
- Twilio (WhatsApp messaging)
- TypeScript + ts-node

**Sensing & ML**
- ESP32 CSI firmware (C, ESP-IDF)
- Python 3.12, PyTorch (TorchScript inference)
- NumPy / SciPy STFT pipeline
- Multi-port serial collection (~70 Hz × 4 RX)

**Infrastructure**
- Railway (backend)
- Vercel (frontend)
- Pusher Channels (realtime)

---

## Team

Built at HackDavis by:

- **Gabriel Mercado**
- **Mark Kozintsev**
- **Jonathan Anzalone**

The combined repo brings together hardware, ML, backend, and frontend work into one shippable submission.

If you'd like to contribute, please open an issue or PR &mdash; we'd love help on additional sensor placements, multi-room support, and broader activity-recognition use cases.

---

## License

This project is released under the [MIT License](LICENSE).

