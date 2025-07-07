#!/usr/bin/env python3
"""
블루투스 거리 기반 맥 자동 잠금 스크립트
핸드폰이 설정된 거리 이상 떨어지면 자동으로 맥을 잠급니다.
"""

import asyncio
import subprocess
import logging
import json
import os

from bleak import BleakScanner
from typing import Optional, Dict

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class BluetoothLock:
    def __init__(self, config_file: str = 'bluetooth_config.json'):
        self.config_file = config_file
        self.config = self.load_config()
        self.lock_triggered = False
        
    def load_config(self) -> Dict:
        """설정 파일을 로드합니다."""
        default_config = {
            "target_device_name": "",  # 핸드폰 이름 (예: "iPhone")
            "target_device_address": "",  # MAC 주소 (옵션)
            "distance_threshold": -70,  # RSSI 임계값 (더 낮은 값 = 더 멀리)
            "scan_interval": 0,  # 스캔 간격 (초)
            "grace_period": 3,  # 잠금까지의 대기 시간 (초)
            "scan_duration": 10,  # 스캔 시간 (초)
            "lock_enabled": True  # 잠금 활성화 여부
        }
        
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                    # 기본값과 병합
                    default_config.update(config)
                    return default_config
            except Exception as e:
                logger.error(f"설정 파일 로드 실패: {e}")
                return default_config
        else:
            # 기본 설정 파일 생성
            self.save_config(default_config)
            return default_config
    
    def save_config(self, config: Dict):
        """설정을 파일에 저장합니다."""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
        except Exception as e:
            logger.error(f"설정 파일 저장 실패: {e}")
    
    async def scan_devices(self) -> Dict[str, tuple]:
        """블루투스 디바이스를 스캔합니다."""
        devices = {}
        
        def callback(device, advertisement_data):
            # RSSI 정보를 포함한 디바이스 정보 저장
            devices[device.address] = (device, advertisement_data.rssi)
        
        try:
            scanner = BleakScanner(callback)
            await scanner.start()
            await asyncio.sleep(self.config.get('scan_duration', 10))  # 10초 스캔
            await scanner.stop()
            return devices
        except Exception as e:
            logger.error(f"디바이스 스캔 실패: {e}")
            return {}
    
    def find_target_device(self, devices: Dict[str, tuple]) -> Optional[tuple]:
        """타겟 디바이스를 찾습니다."""
        target_name = self.config.get('target_device_name', '')
        target_address = self.config.get('target_device_address', '')
        
        for address, (device, rssi) in devices.items():
            # 이름으로 검색
            if target_name and device.name and target_name.lower() in device.name.lower():
                return (device, rssi)
            # MAC 주소로 검색
            if target_address and address.lower() == target_address.lower():
                return (device, rssi)
        
        return None

    def lock_mac(self):
        """맥을 잠급니다."""
        if not self.config.get('lock_enabled', True):
            logger.info("잠금이 비활성화되어 있습니다.")
            return
        
        try:
            # 화면 잠금
            subprocess.run(['pmset', 'displaysleepnow'], check=True)
            logger.info("맥이 잠겼습니다.")
            
            # 추가 보안: 키체인 잠금
            subprocess.run(['security', 'lock-keychain'], check=False)
            
        except subprocess.CalledProcessError as e:
            logger.error(f"맥 잠금 실패: {e}")
    
    async def monitor_device(self):
        """디바이스를 모니터링합니다."""
        logger.info("블루투스 모니터링 시작...")
        logger.info(f"타겟 디바이스: {self.config.get('target_device_name', '설정되지 않음')}")
        logger.info(f"RSSI 임계값: {self.config.get('distance_threshold', -70)} dBm")
        
        while True:
            try:
                devices = await self.scan_devices()
                target_result = self.find_target_device(devices)
                
                if target_result:
                    target_device, rssi = target_result
                    
                    logger.info(f"디바이스 발견: {target_device.name} (RSSI: {rssi} dBm)")
                    
                    self.lock_triggered = False
                    
                    # 임계값 체크
                    if rssi < self.config.get('distance_threshold', -70):
                        logger.warning(f"디바이스가 너무 멀어졌습니다! (RSSI: {rssi})")
                        await self.handle_device_far()
                    
                else:
                    logger.info("타겟 디바이스를 찾을 수 없습니다.")
                
                await asyncio.sleep(self.config.get('scan_interval', 1))
                
            except Exception as e:
                logger.error(f"모니터링 중 오류 발생: {e}")
                await asyncio.sleep(5)
    
    async def handle_device_far(self):
        """디바이스가 멀어졌을 때 처리합니다."""
        if not self.lock_triggered:
            grace_period = self.config.get('grace_period', 5)
            logger.warning(f"{grace_period}초 후 맥이 잠깁니다...")
            await asyncio.sleep(grace_period)
            
            # 다시 확인
            devices = await self.scan_devices()
            target_result = self.find_target_device(devices)
            
            if not target_result or target_result[1] < self.config.get('distance_threshold', -70):
                self.lock_mac()
                self.lock_triggered = True
            else:
                logger.info("디바이스가 다시 감지되었습니다. 잠금 취소.")

    async def setup_device(self):
        """초기 디바이스 설정을 도와줍니다."""
        print("=== 블루투스 디바이스 설정 ===")
        print("주변 블루투스 디바이스를 스캔합니다...")
        
        devices = await self.scan_devices()
        
        if not devices:
            print("디바이스를 찾을 수 없습니다.")
            return
        
        device_list = list(devices.values())
        print(f"\n발견된 디바이스 ({len(device_list)}개):")
        for i, (device, rssi) in enumerate(device_list):
            print(f"{i+1}. {device.name or '이름 없음'} ({device.address}) - RSSI: {rssi}")
        
        try:
            choice = int(input("\n사용할 디바이스 번호를 선택하세요: ")) - 1
            if 0 <= choice < len(device_list):
                selected_device, selected_rssi = device_list[choice]
                self.config['target_device_name'] = selected_device.name or ""
                self.config['target_device_address'] = selected_device.address
                
                print(f"\n선택된 디바이스: {selected_device.name} ({selected_device.address})")
                print(f"현재 RSSI: {selected_rssi} dBm")
                
                # RSSI 임계값 설정
                threshold = input(f"RSSI 임계값 (기본: -70, 현재: {selected_rssi}): ")
                if threshold.strip():
                    self.config['distance_threshold'] = int(threshold)
                
                self.save_config(self.config)
                print("설정이 저장되었습니다!")
                
            else:
                print("잘못된 선택입니다.")
                
        except ValueError:
            print("잘못된 입력입니다.")

def main():
    """메인 함수"""
    import argparse
    
    parser = argparse.ArgumentParser(description='블루투스 거리 기반 맥 자동 잠금')
    parser.add_argument('--setup', action='store_true', help='초기 디바이스 설정')
    parser.add_argument('--config', default='bluetooth_config.json', help='설정 파일 경로')
    
    args = parser.parse_args()
    
    lock_system = BluetoothLock(args.config)
    
    if args.setup:
        asyncio.run(lock_system.setup_device())
    else:
        try:
            asyncio.run(lock_system.monitor_device())
        except KeyboardInterrupt:
            logger.info("모니터링이 중단되었습니다.")

if __name__ == "__main__":
    main() 
