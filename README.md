# 블루투스 거리 기반 맥 자동 잠금

핸드폰이 설정된 거리 이상 떨어지면 자동으로 맥을 잠그는 스크립트입니다.

## 사용법

### 1. 아이폰 블루투스 킨다
- 아이폰: 설정 > 블루투스 > 켜기

### 2. 라이브러리 설치 & 셋업
```bash
cd temp
pip3 install -r requirements.txt
python3 bluetooth_lock.py --setup
```

### 3. 실행한다
```bash
python3 bluetooth_lock.py
```

### 4. 백그라운드 실행 (선택)
```bash
# 백그라운드에서 계속 실행
nohup python3 bluetooth_lock.py &
```

### 5. 백그라운드 프로세스 종료
```bash
pkill -f bluetooth_lock.py
```

## 문제 해결

### 아이폰이 검색 안됨
1. 맥 블루투스 설정에서 아이폰 연결 시도 (실패해도 OK)
2. 아이폰 블루투스 껐다 켜기
3. 다시 setup 실행

### 잠금 안됨
- 시스템 환경설정 > 보안 및 개인정보 보호 > 개인정보 보호 > 접근성에서 터미널 권한 부여

## 설정 파일

```json
{
  "target_device_name": "iPhone",
  "target_device_address": "XX:XX:XX:XX:XX:XX",
  "distance_threshold": -70,
  "scan_interval": 10,
  "grace_period": 30,
  "lock_enabled": true
}
```

- `distance_threshold`: 더 작은 값 = 더 멀리 가야 잠금 (-60: 민감, -80: 둔감)
- `grace_period`: 잠금까지 대기 시간 (초)
