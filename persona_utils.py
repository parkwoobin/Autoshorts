"""
페르소나 생성 및 LLM 관련 유틸리티 함수들
"""
from typing import List
from openai import OpenAI
from models import (
    TargetCustomer, PersonaData, UserVideoInput,
    ReferenceImage, SceneImagePrompt, SceneStoryboard, VideoStoryboard,
    SceneData, VideoStoryboardData
)
import os
from dotenv import load_dotenv
import asyncio

# LangChain imports
# 출력 구조 정확하게 나오게 하기 위한 outputparser
from langchain.output_parsers import PydanticOutputParser
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI
# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 가져오기
OpenAI_API_KEY = os.getenv("OPENAI_API_KEY")
# OpenAI 클라이언트 초기화 (기존 호환성용)
client = OpenAI(api_key=OpenAI_API_KEY)
# LangChain ChatOpenAI 초기화
llm = ChatOpenAI(
    model="gpt-4.1-nano-2025-04-14",
    temperature=0.7,
    openai_api_key=OpenAI_API_KEY
)

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
    """페르소나를 기반으로 LLM이 전문적인 광고 기획을 생성 (이미지 프롬프트 제외)"""
    
    try:
        completion = client.chat.completions.create(
            model="gpt-4.1-nano-2025-04-14",
            messages=[
                {
                    "role": "system",
                    "content": """
당신은 페르소나 분석에 기반하여 광고 전략을 수립하는 '광고 기획 전문가'입니다.
주어진 타겟 페르소나 정보를 깊이 있게 분석하여, 효과적인 광고 기획안을 작성해주세요.

**[작업 목표]**
페르소나 맞춤형 광고 컨셉과 전략을 기획하는 것입니다. (이미지 생성은 제외)

**[작업 수행 단계]**

**1단계: 페르소나 분석**
- 주어진 페르소나의 라이프스타일, 가치관, 소비 패턴, 고민(Pain Point)을 파악합니다.
- 이 페르소나가 어떤 메시지와 콘텐츠에 가장 크게 반응할지 예측합니다.

**2단계: 광고 컨셉 기획**
- 1단계 분석을 바탕으로, 아래 형식에 맞춰 광고 영상 컨셉을 구체적으로 작성합니다.
    - **[핵심 메시지]**: 페르소나의 마음을 사로잡을 단 한 줄의 매력적인 문장.
    - **[광고 컨셉]**: 제품/서비스가 페르소나의 일상에 어떻게 긍정적인 변화를 주는지 구체적인 스토리라인으로 설명.
    - **[영상 분위기]**: 영상의 전체적인 색감, 조명, 음악, 편집 스타일 등을 그려지듯 묘사.
    - **[타겟 반응 전략]**: 이 페르소나가 광고를 보고 어떤 감정을 느끼고, 어떤 행동을 하기를 기대하는지 명시.
    - **[차별화 포인트]**: 경쟁사 대비 우리만의 독특한 어필 포인트.

**3단계: 콘텐츠 구성안**
- 광고 영상의 전체적인 흐름과 구성을 제안합니다.
    - **[도입부]**: 시청자의 관심을 끌 방법
    - **[전개부]**: 문제 제기와 솔루션 제시 방법  
    - **[절정부]**: 가장 임팩트 있는 메시지 전달 방법
    - **[마무리]**: 행동 유도(CTA)와 기억에 남을 엔딩

**[준수 사항]**
- 모든 결과물은 한국어로 작성해야 합니다.
- 각 단계의 결과물은 제목과 함께 명확하게 구분하여 제시해야 합니다.
- 구체적이고 실행 가능한 아이디어를 제공해야 합니다.
"""
                },
                {
                    "role": "user",
                    "content": f"""
다음 타겟 페르소나를 분석하여 광고 기획안을 생성해주세요:

{persona.persona_description}

위 형식을 사용하여 이 페르소나에게 효과적일 구체적이고 창의적인 광고 기획을 제안해주세요.
한국어로 작성해주세요.
"""
                }
            ],
            temperature=0.8,
        )
        
        return completion.choices[0].message.content
        
    except Exception as e:
        print(f"⚠️ OpenAI API 호출 실패 (광고 기획): {e}")

# ==================================================================================

# 3단계: 사용자 입력을 기반으로 장면별 이미지 생성 프롬프트 생성 (LangChain + Pydantic)
async def generate_scene_image_prompts_with_llm(user_description: str) -> VideoStoryboard:
    """사용자 입력을 기반으로 LLM이 장면을 나누고 각 장면별 이미지 생성 프롬프트를 생성 (LangChain 사용)"""
    
    try:
        # Pydantic Output Parser 설정
        parser = PydanticOutputParser(pydantic_object=VideoStoryboardData)
        
        # 프롬프트 템플릿 생성
        prompt = PromptTemplate(
            template="""당신은 광고 영상 제작 전문가이자 AI 이미지 생성 프롬프트 전문가입니다.

사용자가 제공한 광고 영상 아이디어를 분석하여:
1. 먼저 3~6개의 장면으로 나누어 스토리를 구성
2. 각 장면별로 AI 이미지 생성을 위한 효율적이고 균형잡힌 프롬프트를 작성

프롬프트 작성 원칙:
- 핵심 요소만 명확히, 부차 항목은 필요할 때만 추가
- 큰 틀부터 채우고 세부사항은 점진적으로 작성
- 과도한 상세는 피하고 재현성 높은 키워드 사용

각 장면의 이미지 프롬프트는 다음 순서로 구성:
1. Subject (주체): @user의 상태, 의상, 액션
2. Scene (배경): 구체적인 장소와 환경
3. Composition (구도): 카메라 앵글과 프레이밍 (mid-shot, close-up, wide-shot 등)
4. Lighting (조명): 광원과 분위기 (natural light, warm lighting 등)
5. Style (스타일): 화풍과 매체 (cinematic, commercial photography 등)
6. Mood (무드): 감정과 분위기 (confident, friendly, energetic 등)

예시: "Mid-shot of @user smiling confidently in modern office, natural window light, commercial photography style, professional mood"

사용자 입력: {user_input}

위 내용을 바탕으로 임팩트 있고 완성도 높은 광고 영상을 위한 장면 구성과 이미지 프롬프트를 제안해주세요.
모든 이미지 프롬프트는 영문으로 작성하되, 장면 설명은 한국어로 작성해주세요.

{format_instructions}""",
            input_variables=["user_input"],
            partial_variables={"format_instructions": parser.get_format_instructions()}
        )
        
        # 체인 생성 및 실행
        chain = prompt | llm | parser
        result = await chain.ainvoke({"user_input": user_description})
        
        # VideoStoryboardData를 VideoStoryboard로 변환
        scenes = []
        for scene_data in result.scenes:
            # 이미지 프롬프트 생성
            image_prompt = SceneImagePrompt(
                promptText=scene_data.prompt_text,
                seed=20250704 + scene_data.scene_number,  # 장면별로 다른 시드
                referenceImages=[
                    ReferenceImage(uri="https://cdn.example.com/actor_front.jpg", tag="user"),
                    ReferenceImage(uri="https://cdn.example.com/logo_flat.png", tag="brandlogo")
                ]
            )
            
            scene = SceneStoryboard(
                scene_number=scene_data.scene_number,
                scene_title=scene_data.scene_title,
                scene_description=scene_data.scene_description,
                duration_seconds=scene_data.duration_seconds,
                image_prompt=image_prompt
            )
            scenes.append(scene)
        
        # 전체 스토리보드 생성
        user_input = UserVideoInput(user_description=user_description)
        
        return VideoStoryboard(
            user_input=user_input,
            scenes=scenes,
            total_duration=result.total_duration,
            video_concept=result.video_concept
        )
            
    except Exception as e:
        print(f"⚠️ LangChain LLM 호출 실패 (장면 프롬프트 생성): {e}")
        raise e

# ==================================================================================    