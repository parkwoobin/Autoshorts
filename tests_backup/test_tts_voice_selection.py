"""
TTS 음성 샘플 테스트 및 선택 도구
사용자가 직접 음성을 들어보고 선택할 수 있는 기능
"""
import asyncio
from tts_utils import (
    create_voice_samples_by_language,
    interactive_voice_selection,
    play_audio_sample,
    list_voice_samples_with_info,
    TTSConfig
)

async def test_korean_voices():
    """한국어 음성 샘플 테스트"""
    print("🇰🇷 한국어 음성 샘플 테스트")
    print("=" * 50)
    
    sample_text = "안녕하세요! 저는 AI 음성입니다. 오늘 기분이 어떠신가요? 이 목소리로 광고를 만들어보시겠어요?"
    
    results = await create_voice_samples_by_language(
        sample_text=sample_text,
        language="ko",
        output_dir="./static/audio",
        max_samples=6
    )
    
    if "error" in results:
        print(f"❌ 오류: {results['error'].error}")
        return
    
    list_voice_samples_with_info(results)
    
    print("\n🎧 생성된 음성을 재생해보세요:")
    successful_results = {k: v for k, v in results.items() if v.success}
    
    for i, (voice_id, result) in enumerate(successful_results.items(), 1):
        voice_name = TTSConfig.VOICES.get(voice_id, voice_id)
        print(f"   {i}. {voice_name}")
        print(f"      재생: play_audio_sample(r'{result.audio_file_path}')")
    
    return results

async def test_english_voices():
    """영어 음성 샘플 테스트"""
    print("\n🇺🇸 영어 음성 샘플 테스트")
    print("=" * 50)
    
    sample_text = "Hello! I'm an AI voice assistant. How are you feeling today? Would you like to create an advertisement with this voice?"
    
    results = await create_voice_samples_by_language(
        sample_text=sample_text,
        language="en",
        output_dir="./static/audio",
        max_samples=5
    )
    
    if "error" in results:
        print(f"❌ 오류: {results['error'].error}")
        return
    
    list_voice_samples_with_info(results)
    
    print("\n🎧 생성된 음성을 재생해보세요:")
    successful_results = {k: v for k, v in results.items() if v.success}
    
    for i, (voice_id, result) in enumerate(successful_results.items(), 1):
        voice_name = TTSConfig.VOICES.get(voice_id, voice_id)
        print(f"   {i}. {voice_name}")
        print(f"      재생: play_audio_sample(r'{result.audio_file_path}')")
    
    return results

async def test_gender_preference():
    """성별별 음성 테스트"""
    print("\n👫 성별별 음성 선호도 테스트")
    print("=" * 50)
    
    sample_text = "안녕하세요! 성별별 음성 차이를 확인해보세요. 어떤 목소리가 더 마음에 드시나요?"
    
    print("\n👩 여성 음성 샘플:")
    female_results = await create_voice_samples_by_language(
        sample_text=sample_text,
        language="ko",
        gender_preference="female",
        output_dir="./static/audio",
        max_samples=3
    )
    
    print("\n👨 남성 음성 샘플:")
    male_results = await create_voice_samples_by_language(
        sample_text=sample_text,
        language="ko",
        gender_preference="male",
        output_dir="./static/audio",
        max_samples=3
    )
    
    return {"female": female_results, "male": male_results}

async def interactive_selection_demo():
    """대화형 음성 선택 데모"""
    print("\n🎯 대화형 음성 선택 데모")
    print("=" * 50)
    
    sample_text = input("테스트할 텍스트를 입력하세요 (엔터: 기본 텍스트 사용): ").strip()
    if not sample_text:
        sample_text = "안녕하세요! 이 목소리로 광고를 만들어보시겠어요? 자연스럽고 매력적인 음성으로 여러분의 메시지를 전달해드립니다."
    
    language = input("언어를 선택하세요 (ko/en/multilingual, 엔터: ko): ").strip()
    if not language:
        language = "ko"
    
    gender = input("성별 선호도를 선택하세요 (male/female/엔터: 전체): ").strip()
    if not gender:
        gender = None
    
    selected_voice_id = await interactive_voice_selection(
        sample_text=sample_text,
        language=language,
        gender_preference=gender
    )
    
    if selected_voice_id:
        voice_name = TTSConfig.VOICES.get(selected_voice_id, selected_voice_id)
        print(f"\n🎉 최종 선택된 음성: {voice_name} ({selected_voice_id})")
        print(f"💡 이 음성 ID를 워크플로우에서 사용하세요: voice_id='{selected_voice_id}'")
    else:
        print("음성 선택이 취소되었습니다.")

async def quick_voice_comparison():
    """빠른 음성 비교"""
    print("\n⚡ 빠른 음성 비교 (상위 3개)")
    print("=" * 50)
    
    sample_text = "이것은 빠른 음성 비교 테스트입니다. 어떤 목소리가 가장 좋나요?"
    
    results = await create_voice_samples_by_language(
        sample_text=sample_text,
        language="ko",
        output_dir="./static/audio",
        max_samples=3
    )
    
    if "error" in results:
        print(f"❌ 오류: {results['error'].error}")
        return
    
    successful_results = {k: v for k, v in results.items() if v.success}
    
    print("\n🎵 자동 재생 순서:")
    for i, (voice_id, result) in enumerate(successful_results.items(), 1):
        voice_name = TTSConfig.VOICES.get(voice_id, voice_id)
        print(f"\n{i}. {voice_name} 재생 중...")
        play_audio_sample(result.audio_file_path)
        
        # 다음 재생 전 대기
        if i < len(successful_results):
            input("다음 음성을 들으려면 엔터를 누르세요...")

async def main():
    """메인 테스트 함수"""
    print("🎤 TTS 음성 샘플 테스트 도구")
    print("=" * 60)
    print("이 도구를 사용하여 다양한 TTS 음성을 직접 들어보고 선택할 수 있습니다.")
    print()
    
    while True:
        print("\n📋 테스트 메뉴:")
        print("1. 한국어 음성 샘플 테스트")
        print("2. 영어 음성 샘플 테스트") 
        print("3. 성별별 음성 테스트")
        print("4. 대화형 음성 선택")
        print("5. 빠른 음성 비교 (상위 3개)")
        print("6. 종료")
        
        try:
            choice = input("\n선택하세요 (1-6): ").strip()
            
            if choice == "1":
                await test_korean_voices()
            elif choice == "2":
                await test_english_voices()
            elif choice == "3":
                await test_gender_preference()
            elif choice == "4":
                await interactive_selection_demo()
            elif choice == "5":
                await quick_voice_comparison()
            elif choice == "6":
                print("👋 TTS 테스트 도구를 종료합니다.")
                break
            else:
                print("❌ 유효하지 않은 선택입니다.")
                
        except KeyboardInterrupt:
            print("\n👋 사용자가 종료했습니다.")
            break
        except Exception as e:
            print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    print("🎧 음성 재생을 위해 Windows Media Player나 기본 음악 플레이어가 필요합니다.")
    print("💡 생성된 샘플 파일은 ./static/audio/ 폴더에 저장됩니다.")
    print()
    
    asyncio.run(main())
