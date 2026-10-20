import os
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, recall_score, precision_score, f1_score

# ==========================================
# 1. Buoy CNN-LSTM 신경망 모델 정의
# ==========================================
class BuoyCNNLSTM(nn.Module):
    def __init__(self, hidden_dim=64, num_layers=2, num_classes=2):
        super(BuoyCNNLSTM, self).__init__()
        
        # 2D CNN: 타임스텝별 (1, 4, 64) 입력을 특징 벡터로 압축
        self.feature_extractor = nn.Sequential(
            nn.Conv2d(1, 16, kernel_size=(3, 3), padding=1),
            nn.BatchNorm2d(16),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(1, 2)), # (4, 64) -> (4, 32)
            
            nn.Conv2d(16, 32, kernel_size=(3, 3), padding=1),
            nn.BatchNorm2d(32),
            nn.ReLU(),
            nn.MaxPool2d(kernel_size=(1, 2)), # (4, 32) -> (4, 16)
            nn.Flatten()
        )
        
        # CNN 추출 특징 차원 계산: 32 * 4 * 16 = 2048
        cnn_out_dim = 32 * 4 * 16
        
        # LSTM: 100 타임스텝의 시계열 동적 변화 학습
        self.lstm = nn.LSTM(
            input_size=cnn_out_dim,
            hidden_size=hidden_dim,
            num_layers=num_layers,
            batch_first=True,
            dropout=0.2 if num_layers > 1 else 0.0
        )
        
        # 분류기 (낙상 여부 판단)
        self.fc = nn.Sequential(
            nn.Linear(hidden_dim, 32),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(32, num_classes)
        )

    def forward(self, x):
        # x shape: (Batch, Timesteps=100, Devices=4, Subcarriers=64)
        batch_size, timesteps, dev, sub = x.size()
        
        # CNN 처리를 위해 (Batch * Timesteps, Channels=1, Devices=4, Subcarriers=64)로 변경
        c_in = x.view(batch_size * timesteps, 1, dev, sub)
        c_out = self.feature_extractor(c_in)
        
        # LSTM 처리를 위해 (Batch, Timesteps=100, Feature_Dim=2048)로 복원
        r_in = c_out.view(batch_size, timesteps, -1)
        r_out, (h_n, c_n) = self.lstm(r_in)
        
        # 마지막 타임스텝의 출력 사용
        last_out = r_out[:, -1, :]
        logits = self.fc(last_out)
        return logits

# ==========================================
# 2. 데이터 로드 및 전처리
# ==========================================
def main():
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"🚀 연산 장치: {device}")

    X_path = 'C:/CSI_FALL_DETECTION/csi_data/Preprocessed/X_data_buoy.npy'
    y_path = 'C:/CSI_FALL_DETECTION/csi_data/Preprocessed/y_label_buoy.npy'

    if not os.path.exists(X_path) or not os.path.exists(y_path):
        print("❌ 전처리된 .npy 파일을 찾을 수 없습니다. 경로를 확인해주세요.")
        return

    X = np.load(X_path).astype(np.float32)
    y = np.load(y_path).astype(np.int64)

    print(f"📊 로드된 데이터 형상: X={X.shape}, y={y.shape}")

    # Train / Test 분리 (8:2)
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    # PyTorch Tensor 데이터셋 변환
    train_dataset = TensorDataset(torch.from_numpy(X_train), torch.from_numpy(y_train))
    test_dataset = TensorDataset(torch.from_numpy(X_test), torch.from_numpy(y_test))

    train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
    test_loader = DataLoader(test_dataset, batch_size=16, shuffle=False)

    # ==========================================
    # 3. 모델, 손실함수, 최적화함수 설정
    # ==========================================
    model = BuoyCNNLSTM(hidden_dim=64, num_layers=2, num_classes=2).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-4)

    # ==========================================
    # 4. 모델 학습 (Training Loop)
    # ==========================================
    epochs = 30
    print("\n🏋️ Buoy CNN-LSTM 모델 학습 시작...")

    for epoch in range(1, epochs + 1):
        model.train()
        train_loss = 0.0
        
        for batch_x, batch_y in train_loader:
            batch_x, batch_y = batch_x.to(device), batch_y.to(device)
            
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item() * batch_x.size(0)
            
        train_loss = train_loss / len(train_loader.dataset)

        # 검증 평가
        model.eval()
        test_loss = 0.0
        all_preds = []
        all_targets = []

        with torch.no_grad():
            for batch_x, batch_y in test_loader:
                batch_x, batch_y = batch_x.to(device), batch_y.to(device)
                outputs = model(batch_x)
                loss = criterion(outputs, batch_y)
                
                test_loss += loss.item() * batch_x.size(0)
                preds = torch.argmax(outputs, dim=1)
                
                all_preds.extend(preds.cpu().numpy())
                all_targets.extend(batch_y.cpu().numpy())

        test_loss = test_loss / len(test_loader.dataset)
        acc = accuracy_score(all_targets, all_preds)

        if epoch % 5 == 0 or epoch == epochs:
            print(f"Epoch [{epoch:02d}/{epochs}] | Train Loss: {train_loss:.4f} | Test Loss: {test_loss:.4f} | Test Acc: {acc*100:.2f}%")

    # ==========================================
    # 5. 최종 평가 지표 출력 및 모델 저장
    # ==========================================
    rec = recall_score(all_targets, all_preds, zero_division=0)
    prec = precision_score(all_targets, all_preds, zero_division=0)
    f1 = f1_score(all_targets, all_preds, zero_division=0)

    print("\n🎯 최종 모델 평가 결과")
    print(f"  - Accuracy (정확도): {acc*100:.2f}%")
    print(f"  - Precision (정밀도): {prec*100:.2f}%")
    print(f"  - Recall (재현율):    {rec*100:.2f}%")
    print(f"  - F1-Score:         {f1:.4f}")

    save_dir = 'C:/CSI_FALL_DETECTION/csi_data/Preprocessed'
    model_save_path = os.path.join(save_dir, 'buoy_cnn_lstm_model.pth')
    torch.save(model.state_dict(), model_save_path)
    print(f"\n💾 모델 가중치가 성공적으로 저장되었습니다: {model_save_path}")

if __name__ == "__main__":
    main()