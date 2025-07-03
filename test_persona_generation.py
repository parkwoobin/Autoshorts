import asyncio
from models import TargetCustomer
from persona_utils import generate_persona_with_llm, create_ad_example
import os

# --- 중요 ---
# 이 스크립트를 실행하려면 먼저 터미널에서 OpenAI API 키를 설정해야 합니다.
# (PowerShell):   $env:OPENAI_API_KEY="your_api_key_here"
#
# 또는, `shortpilot` 폴더에 `.env` 파일을 만들고 아래 내용을 추가하세요.
# OPENAI_API_KEY=your_api_key_here

async def main():
    """
    샘플 고객 데이터로 페르소나 생성 → 광고 컨셉 예시 생성까지 전체 플로우를 테스트합니다.
    """
    print("🧪 전체 플로우 테스트를 시작합니다: 페르소나 생성 → 광고 컨셉 예시 생성")

    # 1. 테스트용 타겟 고객 정의
    sample_customer = TargetCustomer(
        country="한국",
        age_range=["20-29"],
        gender="여성",
        language="한국어",
        interests=["헬스", "뷰티", "라이프스타일"]
    )

    print("\n🎯 테스트용 타겟 고객 정보:")
    print(f"- 국가: {sample_customer.country}")
    print(f"- 연령대: {', '.join(sample_customer.age_range)}")
    print(f"- 성별: {sample_customer.gender}")
    print(f"- 언어: {sample_customer.language}")
    print(f"- 관심사: {', '.join(sample_customer.interests)}")

    try:
        # 2. STEP 1: LLM으로 페르소나 생성
        print("\n🤖 STEP 1: LLM을 호출하여 페르소나를 생성합니다... (잠시만 기다려주세요)")
        persona_data = await generate_persona_with_llm(sample_customer)

        print("\n✅ 페르소나 생성 성공!")
        print("="*60)
        print("\n**📝 생성된 페르소나:**\n")
        print(persona_data.persona_description)
        print("\n" + "="*60)

        # 3. STEP 2: 생성된 페르소나로 광고 컨셉 예시 생성
        print("\n🎬 STEP 2: 생성된 페르소나를 기반으로 광고 컨셉 예시를 생성합니다...")
        ad_concept = await create_ad_example(persona_data)

        print("\n✅ 광고 컨셉 예시 생성 성공!")
        print("="*60)
        print("\n**🎯 생성된 광고 컨셉 예시:**\n")
        print(ad_concept)
        print("\n" + "="*60)

        print("\n🎉 전체 플로우 테스트 완료!")
        print("   1. 타겟 고객 정보 → 페르소나 생성 ✅")
        print("   2. 페르소나 → 광고 컨셉 예시 생성 ✅")

    except Exception as e:
        print(f"\n❌ 테스트 중 오류가 발생했습니다: {e}")
        print("   OpenAI API 키가 올바르게 설정되었는지, 네트워크 연결은 정상인지 확인해주세요.")

if __name__ == "__main__":
    # 임포트가 올바르게 동작하도록 스크립트의 작업 디렉토리를 설정합니다.
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    asyncio.run(main())
