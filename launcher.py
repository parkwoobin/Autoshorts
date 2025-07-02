#!/usr/bin/env python3
"""
영상 생성 프로토타입 런처
서버와 클라이언트를 한 번에 관리할 수 있습니다.
"""

import subprocess
import time
import sys
import os
import signal
import threading
from pathlib import Path

def start_server():
    """FastAPI 서버 시작"""
    print("🚀 FastAPI 서버를 시작합니다...")
    print("📁 실행 파일: client.py (서버 코드)")
    print("🌐 서버 주소: http://localhost:8000")
    try:
        # 현재 디렉토리에서 서버 실행
        process = subprocess.Popen([sys.executable, "client.py"], 
                                 stdout=subprocess.PIPE, 
                                 stderr=subprocess.PIPE,
                                 text=True)
        
        # 서버 시작 대기
        time.sleep(3)
        
        if process.poll() is None:  # 프로세스가 살아있으면
            print("✅ 서버가 성공적으로 시작되었습니다! (http://localhost:8000)")
            return process
        else:
            stdout, stderr = process.communicate()
            print(f"❌ 서버 시작 실패:")
            print(f"stdout: {stdout}")
            print(f"stderr: {stderr}")
            return None
            
    except Exception as e:
        print(f"❌ 서버 시작 중 오류: {e}")
        return None

def start_client():
    """테스트 클라이언트 시작"""
    print("🎮 테스트 클라이언트를 시작합니다...")
    print("📁 실행 파일: test_client.py (클라이언트 코드)")
    print("🔗 서버 연결: http://localhost:8000")
    try:
        # 클라이언트 실행 (대화형 모드)
        subprocess.run([sys.executable, "test_client.py"])
    except KeyboardInterrupt:
        print("\n🛑 클라이언트가 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"❌ 클라이언트 실행 중 오류: {e}")

def check_requirements():
    """필요한 파일들이 있는지 확인"""
    required_files = ["client.py", "test_client.py", "requirements.txt"]
    missing_files = []
    
    for file in required_files:
        if not Path(file).exists():
            missing_files.append(file)
    
    if missing_files:
        print(f"❌ 필요한 파일이 없습니다: {missing_files}")
        return False
    
    return True

def install_dependencies():
    """의존성 패키지 설치"""
    print("📦 의존성 패키지를 확인합니다...")
    try:
        # requirements.txt가 있으면 설치
        if Path("requirements.txt").exists():
            result = subprocess.run([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ 의존성 패키지 설치 완료")
            else:
                print(f"⚠️ 패키지 설치 중 경고: {result.stderr}")
        return True
    except Exception as e:
        print(f"❌ 패키지 설치 실패: {e}")
        return False

def main():
    print("🎥 영상 생성 프로토타입 런처")
    print("=" * 50)
    
    # 1. 필수 파일 확인
    if not check_requirements():
        return
    
    # 2. 사용자 선택
    print("\n실행 모드를 선택하세요:")
    print("1. 서버만 실행")
    print("2. 클라이언트만 실행") 
    print("3. 서버 + 클라이언트 자동 실행")
    print("4. 의존성 패키지 설치")
    
    try:
        choice = input("\n선택 (1-4): ").strip()
        
        if choice == "1":
            # 서버만 실행
            server_process = start_server()
            if server_process:
                try:
                    print("서버가 실행 중입니다. Ctrl+C로 종료하세요.")
                    server_process.wait()
                except KeyboardInterrupt:
                    print("\n🛑 서버를 종료합니다...")
                    server_process.terminate()
                    
        elif choice == "2":
            # 클라이언트만 실행
            start_client()
            
        elif choice == "3":
            # 서버 + 클라이언트 자동 실행
            server_process = start_server()
            if server_process:
                try:
                    print("📱 3초 후 클라이언트를 시작합니다...")
                    time.sleep(3)
                    start_client()
                finally:
                    print("\n🛑 서버를 종료합니다...")
                    server_process.terminate()
                    
        elif choice == "4":
            # 의존성 설치
            install_dependencies()
            
        else:
            print("❌ 잘못된 선택입니다.")
            
    except KeyboardInterrupt:
        print("\n🛑 사용자에 의해 중단되었습니다.")
    except Exception as e:
        print(f"\n❌ 예상치 못한 오류: {e}")

if __name__ == "__main__":
    main()
