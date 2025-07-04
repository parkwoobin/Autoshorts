"""
Runway API 단일 이미지 생성 테스트 스크립트
사용자가 제공한 프롬프트로 실제 이미지 생성을 테스트합니다.
"""
import asyncio
import os
from dotenv import load_dotenv
from persona_utils import create_image_with_runway

# 환경 변수 로드
load_dotenv()

async def test_runway_single_image():
    """사용자 제공 프롬프트로 단일 이미지 생성 테스트"""
    
    print("🧪 Runway API 단일 이미지 생성 테스트를 시작합니다...")
    
    # API 키 확인
    api_key = os.getenv("Runway_API_KEY")
    if not api_key:
        print("❌ Runway_API_KEY 환경 변수가 설정되지 않았습니다.")
        print("   .env 파일에 Runway API 키를 설정해주세요.")
        return
    
    print(f"✅ API 키 확인됨: {api_key[:20]}...")
    
    # 테스트용 프롬프트 (사용자 제공)
    test_prompt = """Subject: 건강 보조제 제품을 손에 든 직장인, 간편하게 섭취하는 모습. Background: 사무실 책상 또는 카페 테이블, 깔끔하고 현대적. Composition: close-up, 손과 제품 집중. Lighting: 부드럽고 따뜻한 조명. Style: 깨끗하고 신뢰감 있는 광고 스타일, 상업 사진. Mood: 신뢰와 기대감."""
    
    test_params = {
        "prompt_text": test_prompt,
        "ratio": "1280:720",
        "seed": 42,
        "model": "gen4_image",
        "reference_images": [],
        "public_figure_moderation": "auto",
        "api_key": api_key
    }
    
    print("\n📝 테스트 파라미터:")
    print(f"   - Model: {test_params.get('model', 'gen4_image')}")
    print(f"   - Ratio: {test_params['ratio']}")
    print(f"   - Seed: {test_params['seed']}")
    print(f"   - Prompt: {test_params['prompt_text'][:100]}...")
    
    try:
        print("\n🚀 Runway API 호출 중...")
        print("   (이미지 생성에는 30초~3분 정도 소요될 수 있습니다)")
        
        # 이미지 생성
        image_url = await create_image_with_runway(**test_params)
        
        print("\n🎉 이미지 생성 성공!")
        print(f"📸 생성된 이미지 URL: {image_url}")
        print("\n💡 브라우저에서 위 URL을 열어 이미지를 확인할 수 있습니다.")
        
        # URL 유효성 간단 확인
        if image_url and image_url.startswith('http'):
            print("✅ 유효한 이미지 URL이 반환되었습니다.")
        else:
            print("⚠️ 반환된 URL이 예상과 다릅니다.")
            
    except Exception as e:
        print(f"\n❌ 이미지 생성 실패: {e}")
        print("\n🔍 가능한 원인:")
        print("   1. API 키가 잘못되었거나 크레딧이 부족할 수 있습니다.")
        print("   2. 네트워크 연결 문제일 수 있습니다.")
        print("   3. Runway 서버에 일시적 문제가 있을 수 있습니다.")
        print("\n💡 해결 방법:")
        print("   - Runway 개발자 포털(dev.runwayml.com)에서 계정과 크레딧을 확인해주세요.")
        print("   - API 키가 올바른지 확인해주세요.")

if __name__ == "__main__":
    # 작업 디렉토리 설정
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # 비동기 실행
    asyncio.run(test_runway_single_image())
