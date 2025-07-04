"""
3단계 스토리보드 생성 테스트
"""
import asyncio
from persona_utils import generate_scene_image_prompts_with_llm

async def test_storyboard_generation():
    """3단계 스토리보드 생성 테스트"""
    
    test_description = """
    건강 보조제 광고 영상을 만들고 싶습니다.
    20대 직장인이 바쁜 일상 속에서 건강을 챙기는 모습을 보여주는 영상입니다.
    아침에 일어나서 건강 보조제를 복용하고, 활기찬 하루를 보내는 내용입니다.
    """
    
    print("🧪 3단계 스토리보드 생성 테스트 시작...")
    print(f"테스트 설명: {test_description.strip()}")
    
    try:
        result = await generate_scene_image_prompts_with_llm(test_description)
        
        print(f"\n✅ 스토리보드 생성 성공!")
        print(f"총 장면 수: {len(result.scenes)}")
        print(f"영상 컨셉: {result.video_concept}")
        print(f"예상 시간: {result.estimated_duration}초")
        
        for i, scene in enumerate(result.scenes, 1):
            print(f"\n🎬 장면 {i}:")
            print(f"   프롬프트: {scene.promptText[:100]}...")
            print(f"   비율: {scene.ratio}")
            print(f"   시드: {scene.seed}")
            
        return True
        
    except Exception as e:
        print(f"\n❌ 스토리보드 생성 실패: {e}")
        return False

if __name__ == "__main__":
    asyncio.run(test_storyboard_generation())
