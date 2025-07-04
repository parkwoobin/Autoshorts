"""
장면별 이미지 생성 프롬프트 테스트
"""
import asyncio
from persona_utils import generate_scene_image_prompts_with_llm

# user_example_sample과 동일한 테스트 데이터
test_user_input = """
30초 분량의 건강 보조제 광고 영상을 제작하고 싶습니다.

** 광고 컨셉 **
바쁜 직장인들이 에너지 부족으로 힘들어하다가, 우리 제품을 통해 활력을 되찾는 스토리

** 원하는 분위기 **
- 따뜻하고 친근한 느낌
- 신뢰감 있는 톤
- 현실적이고 공감 가능한 상황

** 핵심 메시지 **
"매일 지쳐있던 당신, 이제 달라질 시간입니다"

** 주요 장면 구성 아이디어 **
1. 오프닝: 피곤해하는 직장인의 모습
2. 문제 상황: 업무 중 에너지 부족으로 힘들어함  
3. 제품 소개: 간편하게 섭취할 수 있는 건강 보조제
4. 변화된 모습: 활력 넘치는 일상
5. 마무리: 제품명과 구매 안내

이런 느낌으로 만들어주세요!
"""

async def test_scene_generation():
    """장면별 이미지 프롬프트 생성 테스트"""
    print("🎬 장면별 이미지 생성 프롬프트 테스트 시작...")
    print("=" * 50)
    
    try:
        # LLM을 통해 장면별 프롬프트 생성
        storyboard_output = await generate_scene_image_prompts_with_llm(test_user_input)
        
        print(f"✅ 성공! 전체 영상 컨셉: {storyboard_output.video_concept}")
        print(f"📊 총 길이: {storyboard_output.total_duration}초")
        print(f"🎭 장면 수: {len(storyboard_output.scenes)}개")
        print()
        
        # 각 장면별 결과 출력
        for i, scene in enumerate(storyboard_output.scenes, 1):
            print(f"🎬 장면 {i}")
            print(f"�️ 이미지 프롬프트:")
            print(f"   - model: {scene.model}")
            print(f"   - promptText: {scene.promptText}")
            print(f"   - ratio: {scene.ratio}")
            print(f"   - seed: {scene.seed}")
            print(f"   - referenceImages: {len(scene.referenceImages)}개")
            for ref in scene.referenceImages:
                print(f"     * {ref.tag}: {ref.uri}")
            print(f"   - publicFigureModeration: {scene.publicFigureModeration}")
            print("-" * 40)
        
        # JSON 형태로도 출력
        print("\n📋 완성된 JSON 구조 예시:")
        scene = storyboard_output.scenes[0]  # 첫 번째 장면만 출력
        scene_json = {
            "model": scene.model,
            "promptText": scene.promptText,
            "ratio": scene.ratio,
            "referenceImages": [
                {"uri": ref.uri, "tag": ref.tag} 
                for ref in scene.referenceImages
            ],
            "seed": scene.seed,
            "publicFigureModeration": scene.publicFigureModeration
        }
        import json
        print(json.dumps(scene_json, ensure_ascii=False, indent=2))
        
    except Exception as e:
        print(f"❌ 테스트 실패: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_scene_generation())
