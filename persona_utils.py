"""
페르소나 생성 및 LLM 관련 유틸리티 함수들
"""
from typing import List
from openai import OpenAI
from models import TargetCustomer, PersonaData, ExamplePrompt, UserVideoInput, FinalVideoPrompt, DetailedStoryboardScene, EnhancedStoryboard
import os
from dotenv import load_dotenv
import asyncio
# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 가져오기
OpenAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OpenAI_API_KEY)

# --- 신규 추가: 트렌드 데이터 API 호출 시뮬레이션 ---
async def fetch_trend_data_api(country: str) -> dict:
    """
    외부 API를 통해 특정 국가의 최신 트렌드 데이터를 가져옵니다. (시뮬레이션)
    실제 구현 시에는 외부 API 호출 로직으로 대체됩니다.
    """
    print(f"\n🔍 {country}의 최신 트렌드 데이터를 외부 API에서 가져오는 중...")
    await asyncio.sleep(0.5)  # 네트워크 지연 시뮬레이션
    
    if country == "한국":
        return {
            "top_keywords": ["제로 슈거", "Y2K 패션", "AI 프로필", "클라이밍"],
            "emerging_platforms": ["TikTok 숏폼", "인스타그램 릴스", "네이버 블로그"],
            "cultural_notes": "개인의 행복과 성장을 중시하는 '헬시 플레저' 문화가 확산 중입니다."
        }
    else:
        return {
            "top_keywords": ["Sustainable products", "AI tools", "DIY projects", "Wellness"],
            "emerging_platforms": ["Short-form video", "Community forums"],
            "cultural_notes": "Authenticity and social responsibility are highly valued."
        }


# 1단계: 타겟 고객 정보로 페르소나 생성
async def generate_persona_with_llm(customer: TargetCustomer) -> PersonaData:
    """LLM을 사용해 타겟 고객의 페르소나와 영상 테마를 생성합니다."""
    age_ranges_str = ", ".join(customer.age_range)
    interests_str = ", ".join(customer.interests)
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 마케팅 전문가이자 소비자 행동 분석가입니다. 제공된 타겟 고객 정보에만 기반하여, 상세한 페르소나와 그에 맞는 영상 테마 5가지를 제안해주세요."
                },
                {
                    "role": "user", 
                    "content": f"""
다음 타겟 고객 정보를 분석해주세요:
- 국가: {customer.country}
- 연령대: {age_ranges_str}
- 성별: {customer.gender}
- 언어: {customer.language}
- 관심사: {interests_str}

다음 형식으로 답변해주세요:

**1. 페르소나 프로필:**
(이 타겟의 라이프스타일, 가치관, 소비 패턴, 미디어 소비 습관 등을 상세히 설명)

**2. 추천 영상 테마 (5가지):**
(위 페르소나에게 가장 효과적일 영상 컨셉 5가지를 구체적인 제목과 함께 제안)

한국어로 작성해주세요.
"""
                }
            ]
        )
        
        llm_response = completion.choices[0].message.content
        
        # LLM 응답 파싱 (간단한 버전)
        persona_description = llm_response
        suggested_themes = [line for line in llm_response.split('\n') if line.strip().startswith(("1.", "2.", "3.", "4.", "5."))]
        if not suggested_themes:
            suggested_themes = ["내용 없음"]

        return PersonaData(
            target_customer=customer,
            persona_description=persona_description,
            suggested_video_themes=suggested_themes,
            marketing_insights=""  # 마케팅 인사이트는 다음 단계에서 생성
        )
        
    except Exception as e:
        print(f"⚠️ OpenAI API 호출 실패 (페르소나 생성): {e}")
        


# 2단계: 페르소나와 트렌드 데이터를 결합하여 마케팅 인사이트 생성
async def generate_marketing_insights_with_llm(persona: PersonaData, trend_data: dict) -> str:
    """생성된 페르소나와 트렌드 데이터를 바탕으로 LLM을 통해 마케팅 인사이트를 생성합니다."""
    print("\n🤖 생성된 페르소나와 트렌드 데이터를 결합하여 마케팅 전략을 수립합니다...")
    
    trend_keywords = ", ".join(trend_data['top_keywords'])
    trend_platforms = ", ".join(trend_data['emerging_platforms'])
    trend_notes = trend_data['cultural_notes']

    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 최고의 데이터 기반 마케팅 전략가입니다. 페르소나의 특징과 최신 트렌드 데이터를 결합하여, 즉시 실행 가능한 구체적인 마케팅 전략을 수립해주세요."
                },
                {
                    "role": "user",
                    "content": f"""
다음 두 가지 정보를 종합하여, 이 페르소나를 공략할 최적의 마케팅 전략을 제안해주세요.

**1. 타겟 페르소나 프로필:**
{persona.persona_description}

**2. 최신 트렌드 데이터:**
- 주요 키워드: {trend_keywords}
- 신흥 플랫폼: {trend_platforms}
- 문화적 노트: {trend_notes}

**결과물 형식:**

**[핵심 전략 요약]**
(페르소나와 트렌드를 관통하는 핵심 컨셉 1~2 문장)

**[구체적인 실행 방안]**
1. **콘텐츠 전략**: 어떤 콘텐츠를 만들어야 하는가? (트렌드 키워드 활용)
2. **플랫폼 전략**: 어떤 채널에 집중해야 하는가? (신흥 플랫폼 활용)
3. **메시징 전략**: 어떤 톤앤매너와 메시지로 소통해야 하는가? (문화적 노트 활용)

실무에 바로 적용할 수 있도록 구체적이고 창의적인 아이디어를 한국어로 제안해주세요.
"""
                }
            ]
        )
        return completion.choices[0].message.content

    except Exception as e:
        print(f"⚠️ OpenAI API 호출 실패 (인사이트 생성): {e}")
        return "LLM 호출에 실패하여 마케팅 인사이트를 생성할 수 없습니다."

async def generate_example_prompts_with_llm(persona: PersonaData) -> List[ExamplePrompt]:
    """LLM으로 다양한 예시 프롬프트 생성"""
    customer = persona.target_customer
    age_ranges_str = ", ".join(customer.age_range)
    interests_str = ", ".join(customer.interests)
    
    # 3가지 다른 스타일의 예시 프롬프트 생성
    examples = [
        ExamplePrompt(
            scenario_title="감성적 스토리텔링형",
            content=f"""
{age_ranges_str} {customer.gender}의 일상적 고민에서 시작하여, 
{interests_str}와 관련된 해결책을 감성적으로 풀어내는 영상.

구성: 주인공의 고민 → 우연한 발견 → 변화의 과정 → 만족스러운 결과
분위기: 따뜻하고 공감 가능한 톤
""",
            key_messages=["공감대 형성", "자연스러운 해결", "긍정적 변화"],
            tone_and_manner="따뜻하고 공감적인"
        ),
        ExamplePrompt(
            scenario_title="문제 해결형",
            content=f"""
{age_ranges_str} {customer.gender}이 겪는 구체적인 문제를 명확히 제시하고,
단계별 해결 과정을 논리적으로 보여주는 실용적 영상.

구성: 문제 상황 → 해결책 제시 → 적용 과정 → 결과 확인
분위기: 신뢰감 있고 전문적인 톤
""",
            key_messages=["명확한 문제 인식", "효과적인 해결책", "검증된 결과"],
            tone_and_manner="신뢰감 있고 전문적인"
        ),
        ExamplePrompt(
            scenario_title="라이프스타일 제안형",
            content=f"""
{interests_str}를 즐기는 {age_ranges_str} {customer.gender}의 
더 나은 라이프스타일을 제안하는 영감을 주는 영상.

구성: 현재 라이프스타일 → 개선 가능성 → 새로운 경험 → 업그레이드된 일상
분위기: 활기차고 영감을 주는 톤
""",
            key_messages=["라이프스타일 업그레이드", "새로운 경험", "더 나은 일상"],
            tone_and_manner="활기차고 영감을 주는"
        )
    ]
    
    return examples


async def optimize_user_prompt_with_llm(persona: PersonaData, user_input: UserVideoInput) -> FinalVideoPrompt:
    """사용자 입력을 LLM으로 최적화"""
    customer = persona.target_customer
    age_ranges_str = ", ".join(customer.age_range)
    
    # 사용자 입력을 분석하여 최적화된 프롬프트 생성
    optimized_prompt = f"""
타겟 페르소나: {age_ranges_str} {customer.gender} ({customer.country})
관심사: {", ".join(customer.interests)}

사용자 요청사항:
{user_input.user_description}

선택 테마: {", ".join(user_input.selected_themes)}
추가 요구사항: {user_input.additional_requirements}

최적화된 영상 컨셉:
위 페르소나의 특성과 관심사를 고려하여, 사용자가 요청한 내용을
{customer.language} 문화권에 맞게 효과적으로 전달하는 영상을 제작합니다.
"""
    
    # 영상 길이 계산 (복잡도에 따라)
    target_duration = 45 if len(user_input.user_description) > 100 else 30
    
    # 주요 장면 구성
    key_scenes = [
        "오프닝 (관심 유발)",
        "문제/니즈 제시", 
        "솔루션 소개",
        "혜택 강조",
        "행동 유도 클로징"
    ]
    
    return FinalVideoPrompt(
        persona=persona,
        user_input=user_input,
        optimized_prompt=optimized_prompt.strip(),
        target_duration=target_duration,
        key_scenes=key_scenes
    )


async def generate_detailed_storyboard_with_llm(final_prompt: FinalVideoPrompt) -> EnhancedStoryboard:
    """LLM으로 상세한 스토리보드 생성"""
    customer = final_prompt.persona.target_customer
    scenes = []
    
    scene_duration = final_prompt.target_duration // len(final_prompt.key_scenes)
    
    for i, scene_title in enumerate(final_prompt.key_scenes, 1):
        # 각 장면별 상세 정보 생성
        scene = DetailedStoryboardScene(
            scene_number=i,
            title=scene_title,
            description=f"{scene_title}: {final_prompt.user_input.user_description}의 맥락에서 {scene_title.lower()} 장면을 구성",
            visual_elements=f"{customer.country} 문화에 맞는 시각적 요소, {', '.join(customer.interests)} 관련 배경",
            audio_elements=f"{customer.language} 내레이션, 감정에 맞는 BGM, 상황별 효과음",
            camera_work="미디엄샷과 클로즈업을 적절히 혼합" if i % 2 == 1 else "와이드샷에서 점진적 줌인",
            lighting="자연스럽고 따뜻한 조명" if "감성" in final_prompt.user_input.user_description else "명확하고 밝은 조명",
            props_and_costumes=[f"{customer.age_range[0]} 연령대 적합 의상", "브랜드 관련 소품"],
            dialogue_or_narration=f"씬 {i}: {scene_title}에 맞는 {customer.language} 내레이션",
            duration_seconds=scene_duration,
            transition_to_next="자연스러운 컷" if i < len(final_prompt.key_scenes) else ""
        )
        scenes.append(scene)
    
    # 제작 노트 생성
    production_notes = f"""
제작 시 주의사항:
- 타겟: {', '.join(customer.age_range)} {customer.gender} ({customer.country})
- 문화적 고려사항: {customer.country} 현지 문화 반영 필수
- 언어: {customer.language} 사용
- 관심사 연계: {', '.join(customer.interests)} 요소 자연스럽게 포함
- 톤앤매너: 타겟 연령대에 적합한 친근하고 신뢰감 있는 분위기
"""
    
    return EnhancedStoryboard(
        final_prompt=final_prompt,
        scenes=scenes,
        total_duration=sum(scene.duration_seconds for scene in scenes),
        production_notes=production_notes.strip(),
        budget_estimate="중급 예산 (300-800만원)",
        target_platforms=["YouTube", "Instagram", "Facebook", "TikTok"]
    )


# 기존 호환성을 위한 함수들
def generate_persona(customer: TargetCustomer) -> str:
    """타겟 고객 정보를 바탕으로 페르소나 생성 (기존 호환성용)"""
    interests_str = ", ".join(customer.interests)
    age_ranges_str = ", ".join(customer.age_range)  # List[str] 처리
    
    persona = f"""
타겟 페르소나:
- 국가: {customer.country}
- 연령대: {age_ranges_str}
- 성별: {customer.gender}
- 언어: {customer.language}
- 관심사: {interests_str}

이 페르소나는 {age_ranges_str} {customer.gender}로 {customer.country}에 거주하며 {customer.language}를 사용합니다.
주요 관심사는 {interests_str}이며, 이러한 요소들을 고려한 콘텐츠에 높은 관심을 보일 것으로 예상됩니다.
"""
    return persona.strip()


def generate_example_prompt(customer: dict) -> str:
    """페르소나 기반 예시 프롬프트 생성 (기존 호환성용)"""
    interests_str = ", ".join(customer["interests"])
    age_ranges_str = ", ".join(customer["age_range"])  # List[str] 처리
    
    example = f"""
예시 광고 영상 프롬프트:

"{age_ranges_str} {customer['gender']} 타겟을 위한 {interests_str}와 관련된 제품/서비스 광고영상을 제작합니다.

영상 구성:
1. 오프닝: 타겟의 일상적인 고민이나 니즈를 보여주는 장면
2. 문제 제시: 현재 상황의 불편함이나 해결이 필요한 부분 강조
3. 솔루션 소개: 제품/서비스가 어떻게 문제를 해결하는지 시연
4. 혜택 강조: 사용 후 달라진 생활이나 얻을 수 있는 이점들
5. 클로징: 행동 유도와 함께 마무리

전체 톤앤매너: {customer['language']} 언어로 {customer['country']} 문화에 맞는 친근하고 신뢰감 있는 분위기
타겟 연령대: {age_ranges_str}에 적합한 콘텐츠 스타일
영상 길이: 30-60초 내외"

이 예시를 참고하여 원하는 광고 영상의 구체적인 내용을 작성해주세요.
"""
    return example.strip()


def combine_persona_and_prompt(persona_data: dict, user_description: str) -> str:
    """페르소나와 사용자 프롬프트를 결합 (기존 호환성용)"""
    customer = persona_data["target_customer"]
    persona_desc = persona_data["persona_description"]
    age_ranges_str = ", ".join(customer["age_range"])  # List[str] 처리
    
    final_prompt = f"""
타겟 페르소나:
{persona_desc}

광고 영상 요청사항:
{user_description}

최종 영상 제작 가이드라인:
- 타겟: {age_ranges_str} {customer['gender']} ({customer['country']})
- 언어: {customer['language']}
- 관심사 연계: {', '.join(customer['interests'])}
- 문화적 맥락: {customer['country']} 현지 문화와 트렌드 반영
- 콘텐츠 방향: 위 페르소나의 특성과 관심사를 고려한 맞춤형 접근
"""
    return final_prompt.strip()


def create_basic_storyboard(video_prompt_data: dict) -> List[dict]:
    """기본 스토리보드 생성 (추후 LLM으로 대체)"""
    description = video_prompt_data["description"]
    customer = video_prompt_data["persona"]["target_customer"]
    
    scenes = [
        {
            "scene_number": 1,
            "description": f"{customer['age_range']} {customer['gender']}의 일상적인 고민 상황을 보여주는 오프닝 장면",
            "visual_elements": "자연스러운 일상 배경, 고민하는 표정, 부드러운 조명",
            "duration_seconds": 8
        },
        {
            "scene_number": 2,
            "description": "현재 상황의 문제점이나 불편함을 강조하는 장면",
            "visual_elements": "문제 상황 클로즈업, 대비되는 색감, 긴장감 있는 구도",
            "duration_seconds": 10
        },
        {
            "scene_number": 3,
            "description": "제품/서비스 소개 및 솔루션 제시 장면",
            "visual_elements": "제품 등장, 밝은 조명, 희망적인 분위기, 브랜드 컬러",
            "duration_seconds": 15
        },
        {
            "scene_number": 4,
            "description": "사용 후 개선된 모습과 만족스러운 결과를 보여주는 장면",
            "visual_elements": "만족스러운 표정, 밝은 배경, 성과 시각화",
            "duration_seconds": 12
        },
        {
            "scene_number": 5,
            "description": f"행동 유도와 브랜드 메시지로 마무리하는 클로징 ({customer['language']})",
            "visual_elements": "브랜드 로고, CTA 텍스트, 기억에 남는 비주얼",
            "duration_seconds": 10
        }
    ]
    
    return scenes
