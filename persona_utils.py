"""
페르소나 생성 및 LLM 관련 유틸리티 함수들
"""
from typing import List
from openai import OpenAI
from models import TargetCustomer, PersonaData, UserVideoInput, FinalVideoPrompt, DetailedStoryboardScene, EnhancedStoryboard
import os
from dotenv import load_dotenv
import asyncio
# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 가져오기
OpenAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OpenAI 클라이언트 초기화
client = OpenAI(api_key=OpenAI_API_KEY)

# 다 구현하고 나중에 수정 -> 트렌드 데이터 API 호출 부분
async def trend_data_api(country: str) -> dict:
    """
    외부 API를 통해 특정 국가,문화 등의 최신 트렌드 데이터를 가져옴
    실제 구현 시에는 외부 API 호출 로직으로 구현
    """
# ==================================================================================

# 1단계: 타겟 고객 정보로 페르소나 생성
async def generate_persona_with_llm(customer: TargetCustomer) -> PersonaData:
    """LLM을 사용해 타겟 고객의 페르소나를 생성"""
    age_ranges_str = ", ".join(customer.age_range)
    interests_str = ", ".join(customer.interests)
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": "당신은 마케팅 전문가이자 소비자 행동 분석가입니다. 제공된 타겟 고객 정보에만 기반하여, 상세한 페르소나를 제안해주세요."
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

**페르소나 프로필:**
(이 타겟의 라이프스타일, 가치관, 소비 패턴, 미디어 소비 습관 등을 상세히 설명)

한국어로 작성해주세요.
"""
                }
            ]
        )
        # LLM 응답에서 답변만 추출
        llm_response = completion.choices[0].message.content
        
        return PersonaData(
            target_customer=customer,
            persona_description=llm_response,
            marketing_insights=""  # 마케팅 인사이트는 트렌드 데이터와 결합하여 생성할 예정
        )
        
    except Exception as e:
        print(f"⚠️ OpenAI API 호출 실패 (페르소나 생성): {e}")

# ==================================================================================
# LLM 기반 광고 영상 예시 프롬프트 생성 함수
async def create_ad_example(persona: PersonaData) -> str:
    """페르소나를 기반으로 LLM이 전문적인 광고 예시를 생성"""
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": """
당신은 페르소나 분석에 기반하여 광고 전략을 수립하는 '광고 기획 전문가'이자, 광고의 비주얼을 책임지는 '크리에이티브 디렉터'입니다.
주어진 타겟 페르소나 정보를 깊이 있게 분석하여, 다음 단계에 따라 가장 효과적인 광고 캠페인 결과물을 생성해야 합니다.

**[작업 목표]**
페르소나 맞춤형 광고 컨셉 1개와, 그 컨셉의 핵심 장면을 시각화할 수 있는 AI 이미지 생성용 프롬프트 1개를 만드는 것입니다.

**[작업 수행 단계]**

**1단계: 페르소나 분석**
- 주어진 페르소나의 라이프스타일, 가치관, 소비 패턴, 고민(Pain Point)을 파악합니다.
- 이 페르소나가 어떤 메시지와 비주얼에 가장 크게 반응할지 예측합니다.

**2단계: 광고 컨셉 기획**
- 1단계 분석을 바탕으로, 아래 형식에 맞춰 광고 영상 컨셉을 구체적으로 작성합니다.
    - **[핵심 메시지]**: 페르소나의 마음을 사로잡을 단 한 줄의 매력적인 문장.
    - **[광고 컨셉]**: 제품/서비스가 페르소나의 일상에 어떻게 긍정적인 변화를 주는지 구체적인 스토리라인으로 설명.
    - **[영상 분위기]**: 영상의 전체적인 색감, 조명, 음악, 편집 스타일 등을 그려지듯 묘사.
    - **[기대 효과]**: 광고를 통해 페르소나가 무엇을 느끼고, 어떤 행동을 하기를 기대하는지 명시.

**3단계: AI 이미지 생성 프롬프트 작성**
- 2단계에서 기획한 광고 컨셉 중, 가장 임팩트 있는 핵심 장면 하나를 선택합니다.
- 선택한 장면을 AI가 시각적으로 구현할 수 있도록, 아래의  '스토리보드 6요소'를 반드시 모두 포함하여 구체적이고 상세한 프롬프트를 작성합니다.
    - **[장면 (Scene)]**: 누가, 어디서, 무엇을 하고 있는지 구체적으로 묘사.
    - **[카메라/샷 타입 (Camera/Shot Type)]**: 클로즈업, 와이드 샷, 특정 구도 등 카메라 기법 명시.
    - **[조명·분위기 (Lighting/Mood)]**: 자연광, 스튜디오 조명 등 빛의 종류와 그로 인해 연출되는 분위기 설명.
    - **[스타일 (Style)]**: 사진처럼 사실적인 스타일, 영화적인 스타일, 미니멀리즘 등 비주얼 스타일 정의.
    - **[추가 요소 (Additional Elements)]**: 강조하고 싶은 소품, 인물의 표정, 배경의 특정 요소 등 필수 포함 사항.
    - **[제외 요소 (Exclusion Elements)]**: 로고, 텍스트, 불필요한 인물 등 반드시 제외해야 할 요소.

**[준수 사항]**
- 모든 결과물은 한국어로 작성해야 합니다.
- 각 단계의 결과물은 제목과 함께 명확하게 구분하여 제시해야 합니다.
"""
},
{
    "role": "user",
    "content": f"""
다음 타겟 페르소나를 분석하여 광고 영상 예시 프롬프트를 생성해주세요:

{persona.persona_description}

위 형식을 사용하여 이 페르소나에게 효과적일 구체적이고 창의적인 광고 컨셉을 제안해주세요.
한국어로 작성해주세요.
"""
                }
            ],
            temperature=0.8,
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        print(f"⚠️ OpenAI API 호출 실패: {e}")

# ==================================================================================

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

# ==================================================================================

# 2-2단계: 예시 프롬프트와 사용자 입력을 결합하여 최적화
async def optimize_user_prompt_with_llm(persona: PersonaData, user_input: UserVideoInput, example_prompts: str) -> FinalVideoPrompt:
    """사용자가 예시를 참고해서 작성한 내용을 LLM으로 전문적으로 최적화"""
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": """당신은 광고 영상 제작 전문가입니다. 사용자가 제공한 영상 아이디어를 분석하고, 페르소나와 예시 프롬프트를 참고하여 전문적인 영상 제작 가이드라인으로 최적화해주세요.

결과는 다음 형식으로 작성해주세요:

**[최적화된 영상 컨셉]**
(사용자 아이디어를 바탕으로 전문적으로 다듬어진 영상 컨셉 설명)

**[핵심 장면 구성]**
1. 오프닝 장면: (설명)
2. 문제/니즈 제시: (설명)  
3. 솔루션 소개: (설명)
4. 혜택 강조: (설명)
5. 클로징/CTA: (설명)

**[권장 영상 길이]**
(적정 시간 제안 - 30초, 45초, 60초 중 선택)

모든 내용은 한국어로 작성해주세요."""
                },
                {
                    "role": "user",
                    "content": f"""
**타겟 페르소나:**
{persona.persona_description}

**AI 생성 예시 프롬프트:**
{example_prompts}

**사용자가 입력한 영상 아이디어:**
{user_input.user_description}

위 정보들을 종합하여 사용자의 영상 아이디어를 전문적으로 최적화하고, 구체적인 장면 구성과 제작 가이드라인을 제안해주세요.
"""
                }
            ],
            temperature=0.7,
        )
        
        llm_response = completion.choices[0].message.content
        
        # 간단한 파싱으로 핵심 장면들 추출 (실제로는 더 정교한 파싱 필요)
        key_scenes = [
            "오프닝 장면",
            "문제/니즈 제시", 
            "솔루션 소개",
            "혜택 강조",
            "클로징/CTA"
        ]
        
        # 기본 60초로 설정 (실제로는 LLM 응답에서 파싱)
        target_duration = 60
        
        return FinalVideoPrompt(
            persona=persona,
            user_input=user_input,
            optimized_prompt=llm_response,
            key_scenes=key_scenes,
            target_duration=target_duration
        )
        
    except Exception as e:
        print(f"⚠️ OpenAI API 호출 실패 (프롬프트 최적화): {e}")
        # 실패 시 기본 응답 반환
        return FinalVideoPrompt(
            persona=persona,
            user_input=user_input,
            optimized_prompt=f"사용자 아이디어: {user_input.user_description}\n\n기본 최적화가 적용되었습니다.",
            key_scenes=["오프닝", "문제 제시", "솔루션", "혜택", "클로징"],
            target_duration=60
        )
