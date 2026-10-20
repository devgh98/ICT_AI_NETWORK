import pandas as pd
import numpy as np
import csv

def convert_csi_for_buoy(csv_file, window_size=100, step_size=5):
    print(f"📄 '{csv_file}' 변환 시작...")
    
    data = []
    expected_devices = ['Rx1', 'Rx2', 'Rx3', 'Rx4']
    
    with open(csv_file, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i == 0: 
                continue
            
            # 모든 칸의 앞뒤 공백 제거
            row = [str(x).strip() for x in row]
            
            # 줄 안에서 Rx1, Rx2, Rx3, Rx4 글자가 어느 칸에 있는지 필사적으로 찾기
            dev_id = None
            dev_idx = -1
            for dev in expected_devices:
                if dev in row:
                    dev_id = dev
                    dev_idx = row.index(dev)
                    break
            
            # 기기 이름을 찾았고, 그 뒤로 파동 데이터가 64개 이상 넉넉히 남아있다면 구출!
            if dev_id and (len(row) - dev_idx - 1) >= 64:
                try:
                    # 첫 번째 칸은 무조건 타임스탬프로 사용
                    timestamp = float(row[0])
                    # 기기 이름 바로 다음 칸부터 정확히 64개만 잘라냄
                    subs = row[dev_idx + 1 : dev_idx + 65]
                    data.append([timestamp, dev_id] + subs)
                except ValueError:
                    continue

    if len(data) == 0:
        print(f"⚠️ '{csv_file}'에서 정상 데이터를 찾지 못했습니다.")
        return np.empty((0, window_size, 4, 64))

    # 강제로 정렬한 데이터로 깔끔한 표(DataFrame) 생성
    col_names = ['Timestamp', 'Device_ID'] + [f'Sub_{i}' for i in range(64)]
    df = pd.DataFrame(data, columns=col_names)
    
    unique_devices = df['Device_ID'].unique()
    print(f"  - 감지된 실제 기기: {unique_devices} ✅ (Rx1~4만 나와야 정상)")
    
    for i in range(64):
        df[f'Sub_{i}'] = pd.to_numeric(df[f'Sub_{i}'], errors='coerce')
    df = df.dropna()
    
    df['Time_Group'] = df['Timestamp'].round(1)
    
    sub_cols = [f'Sub_{i}' for i in range(64)]
    pivoted = df.pivot_table(index='Time_Group', columns='Device_ID', values=sub_cols)
    pivoted.columns = pivoted.columns.swaplevel(0, 1)
    
    correct_column_order = [(dev, f'Sub_{i}') for dev in expected_devices for i in range(64)]
    pivoted = pivoted.reindex(columns=correct_column_order)
    pivoted = pivoted.ffill().bfill().dropna()
    
    if len(pivoted) == 0:
        return np.empty((0, window_size, 4, 64))
        
    time_series_data = pivoted.values.reshape(-1, 4, 64)
    
    X = []
    for i in range(0, len(time_series_data) - window_size + 1, step_size):
        X.append(time_series_data[i : i + window_size])
        
    X = np.array(X) if len(X) > 0 else np.empty((0, window_size, 4, 64))
    print(f"  -> 변환 완료! Shape: {X.shape}")
    return X

if __name__ == "__main__":
    print("🔄 Buoy 모델용 데이터 전처리를 시작합니다...\n")

    # =====================================================================
    # 📌 [경로 입력 부분] 실제 저장된 경로와 파일명을 여기에 적어주세요.
    # =====================================================================
    PATH_EMPTY  = 'C:/CSI_FALL_DETECTION/csi_data/csi_nomal_sync.csv'
    PATH_WALK   = 'C:/CSI_FALL_DETECTION/csi_data/csi_walk_sync.csv'
    PATH_SIT    = 'C:/CSI_FALL_DETECTION/csi_data/csi_sit_sync.csv'
    PATH_PICKUP = 'C:/CSI_FALL_DETECTION/csi_data/csi_pickup_sync.csv'
    PATH_FALL   = 'C:/CSI_FALL_DETECTION/csi_data/csi_fall_sync.csv'

    # 1. 일상 행동 데이터 변환 (정상 상태 = 라벨 0)
    X_empty = convert_csi_for_buoy(PATH_EMPTY)
    y_empty = np.zeros(len(X_empty))

    X_walk = convert_csi_for_buoy(PATH_WALK)
    y_walk = np.zeros(len(X_walk))

    X_sit = convert_csi_for_buoy(PATH_SIT)
    y_sit = np.zeros(len(X_sit))

    X_pickup = convert_csi_for_buoy(PATH_PICKUP)
    y_pickup = np.zeros(len(X_pickup))

    # 2. 낙상 이벤트 데이터 변환 (비정상 상태 = 라벨 1)
    X_fall = convert_csi_for_buoy(PATH_FALL)
    y_fall = np.ones(len(X_fall))

    # 3. 모든 데이터를 하나의 거대한 데이터셋으로 병합
    X_total = np.concatenate([X_empty, X_walk, X_sit, X_pickup, X_fall], axis=0)
    y_total = np.concatenate([y_empty, y_walk, y_sit, y_pickup, y_fall], axis=0)

    print(f"\n✅ 전체 데이터 병합 완료! 총 데이터 형태: X={X_total.shape}, y={y_total.shape}")

    # 4. 저장 폴더 경로 지정 (마찬가지로 다운로드 폴더에 저장)
    SAVE_PATH_X = 'C:/CSI_FALL_DETECTION/csi_data/Preprocessed/X_data_buoy.npy'
    SAVE_PATH_Y = 'C:/CSI_FALL_DETECTION/csi_data/Preprocessed/y_label_buoy.npy'

    np.save(SAVE_PATH_X, X_total)
    np.save(SAVE_PATH_Y, y_total)
    
    print(f"📁 모델 학습용 파일이 저장되었습니다!\n -> {SAVE_PATH_X}\n -> {SAVE_PATH_Y}")