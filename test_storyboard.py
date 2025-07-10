import asyncio
from workflows import generate_scene_prompts,generate_images_sequentially
from models import ReferenceImageWithDescription
import os
from dotenv import load_dotenv
# 환경 변수 로드
load_dotenv()

async def main():
    image_analyses = [
        {'tag': 'background', 'uri': 'https://search.pstatic.net/common/?src=https%3A%2F%2Fldb-phinf.pstatic.net%2F20230821_219%2F1692626464061SMXrk_JPEG%2FKakaoTalk_20230821_211656406_24.jpg', 'analysis': '이 이미지는 깔끔하고 현대적인 카페 외관 을 보여줍니다. 광고에 활용할 수 있는 주요 특징과 포인트는 다음과 같습니다:\n\n1. **미니멀리즘 디자인**: 깔끔한 라인과 단순한 색상 조합이 돋보입니다. 미니멀리즘을 강조하는 브랜드나 제품에 적합합니다.\n\n2. **편안한 분위기**: 야외 좌석과 자연 요소(대나무)가 편안하고 여유로운 느낌을 줍니다. 휴식, 커피, 디저트와 관련된 광고에 활용하기 좋습니다.\n\n3. **현대적 감각**: 벽돌과 금속 소재가 현대적이고 세련된 느낌을 줍니다. 젊고 트렌디한 이미지를 원하는 광고에 적합합니다.\n\n4. **자연 광 활용**: 자연광이 잘 들어오는 공간으로, 밝고 긍정적인 이미지를 전달할 수 있습니다. 건강, 웰빙 관련 제품 광고에 활용할 수 있습니다.\n\n5. **브랜드 노출**: "NUKNUK"라는 브랜드명이 명확하게 보입니다. 브랜드 인지도를 높이기 위한 광고에 효과적입니다.\n\n이 이미지를 배경으로 사용할 때, 제품이나 메시지를 중앙에 배치하여 시각적 균형을 맞추는 것이 좋습니다.'},
        {'tag': 'product', 'uri': 'https://search.pstatic.net/common/?src=http%3A%2F%2Fblogfiles.naver.net%2FMjAyNDA5MTBfNjUg%2FMDAxNzI1OTYzNzE0NDMx.KX_lM-Gioqwu1g7TtZ71DNckDtOwe_GMwlDQeg9A_jYg.4sIiKQX4KW-WiPsXxnRXryN8CWPlYq8HSzXl7vd1GoQg.JPEG%2FKakaoTalk_20240910_190454483_07.jpg&type=sc960_832', 'analysis': '이 이미지는 족발 요리로 보입니다. 광고에 활용할 수 있는 주요 특징과 포인트는 다음과 같습니다:\n\n1. **비주얼의 매력**:\n   - 윤기 나는 갈색의 족발이 먹음직스럽게 보입니다. 고기의  결이 잘 드러나 있어 신선하고 부드러운 식감을 강조할 수 있습니다.\n\n2. **전통과 현대의 조화**:\n   - 족발은 전통적인 한 국 음식으로, 전통적인 맛을 강조하면서도 현대적인 프레젠테이션으로 젊은 층에게도 어필할 수 있습니다.\n\n3. **건강한 이미 지**:\n   - 족발은 콜라겐이 풍부하여 피부 건강에 좋다는 인식이 있습니다. 이러한 건강적인 측면을 강조할 수 있습니다.\n\n4. **다양한 활용**:\n   - 다양한 소스나 반찬과 함께 즐길 수 있는 점을 강조하여, 여러 가지 맛을 경험할 수 있다는 점을 부각할 수 있습니다.\n\n5. **모임과 파티 음식**:\n   - 넉넉한 양으로 보이는 족발은 가족 모임이나 친구들과의 파티에 적합한 음 식임을 강조할 수 있습니다.\n\n이러한 포인트들을 활용하여 족발의 매력을 다양한 소비자층에게 어필할 수 있습니다.'}
    ]
    user_description_example = """
    **🎯 생성된 광고 컨셉 :**
    \n✨ 광고 한 줄 요약 (Catchy One-liner)
    "내 피부도, 나의 삶도, 트렌디하게 빛나게 – 너의 아름다움에 건강을 더하다."
    \n🎯 핵심 메시지 (Core Message)
    당신이 꿈꾸는 건강하고 아름다운 라이프스타일은 자연스럽고 트렌디하며, 자신감 넘치는 일상의 핵심임을 강조합니다. 최신 유 행과 자기개발에 민감한 20대 여성들이, 자연 친화적이면서도 세련된 선택으로 자신을 더욱 빛나게 하는 제품 또는 경험을 통해 자기만족과 활력을 찾도록 유도합니다.
    \n🎬 크리에이티브 컨셉 (Creative Concept)
    현대적이고 미니멀한 카페를 배경으로, 자연광 속에서 활기차게 웃으며 자신의 아름다움과 건강을 챙기는 젊은 여성의 모습을 담아내세요. 영상은 빠른 컷으로 건강한 피부와 몸매를 가꾸는 일상 루틴, 최신 트렌드와의 조화를 보여줍니다. 마지막에는 인플루언서와 함께하는 챌린지 또는 참여형 태그를 덧붙여, 자연스럽게 소비자 참여를 유도하는 스토리로 마무리합니다.
    \n🎨 영상 분위기 (Visual Mood & Tone)
    밝고 생기 넘치는 색감, 자연광이 가득한 화사한 톤으로 구성합니다. 부드러운 배경음악과 함께 빠른 템포의 컷으로 역동성과 현대적 감각을 살리면서도, 친근하고 따뜻한 분위기를 유지합니다. 자연스럽고 세련된 영상미로, 트렌디하면서도 자연 친화적인 이미지를 강조합니다.
    \n💡 핵심 활용 전략 (Key Strategy)
    참조 이미지의 미니멀리즘과 현대적 감각을 활용하여, SNS 친화적 감각적인 비주얼을 제작합니다. 브랜드명 “NUKNUK”의 모던하고 깔끔한 디자인을 영상과 이미지 곳곳에 배치하여 인지도를 높입니다. 더불어, 건강과 아름다움, 친환경 가치 등을 강조하는  메시지를 인플루언서와 협업하는 챌린지 또는 해시태그 캠페인과 연계하여, 빠른 확산과 참여를 유도합니다. 젊은 여성들이 자신의 일상에 자연스럽게 녹아들 수 있도록, 제품 또는 경험이 일상 속에서 당연하게 느껴지도록 전략적으로 배치하세요.
    """

    print("\n🎬 STEP 3: 광고 아이디어 + 참조 이미지로 스토리보드(장면 프롬프트) 생성 테스트...")
    enriched_images = [
        ReferenceImageWithDescription(
            uri=img['uri'],
            tag=img['tag'],
            analysis=img['analysis']
        ) for img in image_analyses
    ]

    # 3. 수정된 함수에 '사용자 아이디어'와 '작업용 객체 리스트'를 전달합니다.
    storyboard = await generate_scene_prompts(
        user_description=user_description_example,
        enriched_images=enriched_images  # <- 이 부분이 변경되었습니다.
    )
    print("\n✅ 스토리보드(장면 프롬프트) 생성 성공!")
    print(storyboard)
    print("="*60)
    print("\n🎉 전체 플로우 테스트(스토리보드 생성까지) 완료!")
    if storyboard.scenes:
        print("\n🎬 STEP 3: 첫 번째 장면만 선택하여 이미지 생성을 테스트합니다...")
    # 1. 새로 만든 메인 함수를 호출하여 모든 장면 이미지 생성
    
    final_images = await generate_images_sequentially(
        scenes=storyboard.scenes,  # 첫 번째 장면만 테스트
        api_key=os.getenv("RUNWAY_API_KEY") 
    )
        
    # 2. 결과 확인
    for i, result in enumerate(final_images):
        print(f"\n--- 장면 {i+1} 결과 ---")
        if result.get("image_url"):
            print(f"  성공! URL: {result['image_url']}")
        else:
            print(f"  실패: {result.get('error')}")

if __name__ == "__main__":
    asyncio.run(main())
