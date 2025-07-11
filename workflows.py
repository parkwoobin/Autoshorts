"""
페르소나 생성 및 LLM 관련 유틸리티 함수들 - 정리된 LangChain 통합 버전
비용 효율성과 코드 간소화에 중점을 둔 리팩토링
"""
from typing import List,Dict
from models import (
    TargetCustomer, PersonaData, ReferenceImageWithDescription,
    ReferenceImage, SceneImagePrompt, StoryboardOutput
)
import os
from dotenv import load_dotenv
import asyncio
import httpx

# LangChain imports
# 
from langchain.prompts import ChatPromptTemplate, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage

# .env 파일에서 환경 변수 로드
load_dotenv()

# OpenAI API 키 가져오기
OpenAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 비용 효율적인 LLM 설정
# 텍스트 생성용 - 사용자가 요청한 모델로 변경
text_llm = ChatOpenAI(
    model="gpt-4.1-nano-2025-04-14",  # 비용 효율적인 모델
    openai_api_key=OpenAI_API_KEY,
    temperature=0.7
)

# 이미지 분석용 모델 설정
vision_llm = ChatOpenAI(
    model="gpt-4o",  # 이미지 분석 전용
    openai_api_key=OpenAI_API_KEY,
    temperature=0.2  # 낮은 온도는 이미지처럼 객관적인 묘사에 유리 -> 온도가 높으면 창의적이지만 주관적인 해석이 섞인 답변이 나올 수 있음
)

# 외부 트렌드 데이터베이스 연동 인터페이스
# ==================================================================================
async def get_trend_data(country: str, gender: str, age_range: List[str], interests: List[str]) -> dict:
    """
    외부 트렌드 데이터베이스에서 타겟 고객에 맞는 트렌드 데이터를 가져오는 인터페이스
    
    Args:
        country: 국가 정보
        gender: 성별
        age_range: 연령대 리스트 
        interests: 관심사 리스트
        
    Returns:
        dict: 트렌드 데이터베이스에서 가져온 트렌드 데이터
        
    Note:
        현재는 빈 dict 반환. 외부 트렌드 데이터베이스 API 연동 시 이 함수 내용만 교체하면 됨.
    """
    print(f"📊 트렌드 데이터베이스 연동 대기 중... (타겟: {country} {gender} {age_range} {interests})")
    
    # TODO: 외부 트렌드 데이터베이스 API 호출 로직으로 교체
    # 예시: 
    # async with httpx.AsyncClient() as client:
    #     response = await client.post("https://trend-db-api.com/query", json={
    #         "country": country, "gender": gender, "age_range": age_range, "interests": interests
    #     })
    #     return response.json()
    
    # 현재는 빈 데이터 반환 (LLM이 자체 판단으로 페르소나 생성하도록)
    return {}

# ==================================================================================
"""
    사용자 입력 1단계 : LangChain과 트렌드 데이터를 활용한 정교한 타겟 페르소나 생성
    1. 외부 트렌드 데이터베이스에서 데이터 조회 - 추후 구현
    2. LangChain OutputParser로 구조화된 페르소나 생성
    3. 트렌드 데이터 없을 시 LLM이 자체 판단으로 페르소나 생성
"""
async def generate_persona(customer: TargetCustomer) -> PersonaData:
    # LLM에게 리스트형태로 전달하는것보다는 문자열로 전달하는 것이 더 효율적임
    age_ranges_str = ", ".join(customer.age_range)
    interests_str = ", ".join(customer.interests) if customer.interests else "없음"
    
    # 외부 트렌드 데이터베이스에서 데이터 조회
    print("📊 트렌드 데이터베이스에서 데이터를 조회합니다...") # 디버깅용
    trend_data = await get_trend_data(
        country=customer.country,
        gender=customer.gender,
        age_range=customer.age_range,
        interests=customer.interests
    )
    
    # 트렌드 데이터를 문자열로 포매팅 (빈 데이터인 경우 "데이터 없음" 표시)
    import json
    if trend_data:
        trend_data_str = json.dumps(trend_data, indent=2, ensure_ascii=False)
        print("📈 트렌드 데이터 조회 완료")
    else:
        trend_data_str = "트렌드 데이터가 없습니다. 전문 지식을 바탕으로 분석해주세요."
        print("📈 트렌드 데이터 없음 - LLM 자체 판단으로 진행")
    
    # LangChain OutputParser 설정했더니 됐다가 안됐다가 함 프롬프트 템플릿 안에 출력 구조 지침과 지시사항을 같이 입력하다보니 헷갈려서 비어있는 출력 포맷으로 답변할 때가 있음
    # OutputParser 대신 with_structured_output()사용이 권장됨
    # LLM의 응답을 PersonaData 모델 형식으로 구조화
    # parser = PydanticOutputParser(pydantic_object=PersonaData)
    
    # LLM에게 전달할 프롬프트 템플릿 정의
    # 시스템 메시지: AI의 역할과 핵심 지시사항 정의
    system_template = """
    당신은 최신 트렌드에 정통한 전문 마케터이자 소비자 심리 분석가입니다.
    주어진 타겟 고객 정보와 트렌드 데이터를 종합 분석하여, 광고 숏폼 기획에 직접 활용할 수 있는 구체적이고 살아있는 페르소나를 생성해주세요.

    ### 생성 지침
    **중요**: 트렌드 데이터가 비어있거나 부족한 경우, 당신의 전문 지식을 바탕으로 해당 타겟 고객층의 일반적인 특성을 분석하여 페르소나를 구성하세요.
    응답은 다음 세 부분으로 명확히 분리해서 작성해주세요:
    1. **target_customer**: 입력받은 타겟 고객 정보 그대로 반영
    2. **persona_description**: 구체적인 페르소나 설명 (이름, 나이, 직업, 라이프스타일, 소비 패턴 등)
    3. **marketing_insights**: 이 페르소나를 대상으로 한 마케팅 전략 (효과적인 메시지, 선호 광고 형식 등)
    """
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)

     # 변하는 실제 데이터 부분 정의
    human_template = """
    ### 타겟 고객 정보
    - 국가/문화: {country}
    - 연령대: {age_ranges}
    - 성별: {gender}
    - 언어/문화권: {language}
    - 관심사: {interests}

    ### 트렌드 데이터
    {trend_data}
    """
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    # 3. ChatPromptTemplate으로 시스템과 사용자 메시지를 조합
    prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])

    # Pydantic 모델(PersonaData)을 LLM에 직접 바인딩하여 JSON 모드 활성화 (Tool Calling 기능)
    # 체인의 최종 출력 구조는 PersonaData가 됨
    structured_llm = text_llm.with_structured_output(PersonaData)

    # LangChain 체인 재구성 
    chain = prompt | structured_llm

    print("🤖 LangChain을 통한 페르소나 생성 중...")
    # ainvoke는 비동기 호출
    result = await chain.ainvoke({
    "country": customer.country,
    "age_ranges": age_ranges_str,
    "gender": customer.gender,
    "language": customer.language,
    "interests": interests_str,
    "trend_data": trend_data_str
    })

    return result

# ==================================================================================
""" 
    페르소나, 마케팅 인사이트, 참조 이미지를 바탕으로 LLM이 광고 컨셉 생성
    이 단계의 목적 : 생성된 광고 예시 템플릿에 맞춰 사용자가 손쉽게 수정·확장할 수 있는 가이드라인을 제공
"""
async def create_ad_concept(persona: PersonaData, reference_images: List[ReferenceImage] = None) -> str:
    
    # 참조 이미지 분석 (있는 경우만)
    image_analysis = ""
    analyzed_images = []
    if reference_images:
        print(f"🔍 {len(reference_images)}개의 참조 이미지 분석 중...")
        # 참조 이미지 분석 결과는 리스트안에 딕셔너리로 담겨 있음
        analyzed_images = await analyze_reference_images(reference_images)
        print("✅ 참조 이미지 결과 디버깅")
        print(analyzed_images)  # 디버깅용 출력
        # 참조 이미지 분석 결과를 그대로 프롬프트에 넣을 수 없으므로 문자열로 변환
        image_analysis = "\n### 📸 참조 이미지 분석\n"
        for img in analyzed_images:
            # ex) product : 미니멀한 디자인의 흰색 병. 깨끗하고 고급스러운 느낌을 준다.
            image_analysis += f"**{img['tag']}**: {img['analysis']}\n"
    
    # 시스템 메시지 : AI의 역할과 출력 형식 지시
    system_template = """
    당신은 뛰어난 광고 기획 전문가입니다.
    주어진 데이터를 바탕으로, 타겟 고객을 사로잡을 효과적인 광고 컨셉을 제안해주세요.

    ### 중요 지침
    - '참조 이미지 분석' 섹션이 입력 데이터에 **있는 경우에만**, 해당 내용을 '핵심 활용 전략'에 반영하세요.
    - '참조 이미지 분석' 섹션이 **없다면**, 절대 참조 이미지에 대해 언급하지 마세요.
    
    ### 제안할 광고 컨셉 포맷
    아래 포맷을 반드시 준수하여, 각 항목에 대해 깊이 있는 내용을 제안해주세요.
    **✨ 광고 한 줄 요약 (Catchy One-liner)**
    : 광고 전체를 관통하는, 귀에 꽂히는 한 문장 캐치프레이즈.
    **🎯 핵심 메시지 (Core Message)**
    : 이 광고를 통해 타겟 고객의 어떤 감정이나 욕구를 건드릴 것인지 명확히 서술.
    **🎬 크리에이티브 컨셉 (Creative Concept)**
    : 광고의 구체적인 시나리오나 스토리. 짧지만 강력한 내러티브를 제시.
    **🎨 영상 분위기 (Visual Mood & Tone)**
    : 영상의 색감, 속도, 사운드 등 전체적인 시각적, 청각적 스타일.
    **💡 핵심 활용 전략 (Key Strategy)**
    : (만약 '참조 이미지 분석' 내용이 있다면) 타겟 고객 마케팅 인사이트와 참조 이미지의 강점을 어떻게 결합할지 서술.
    : (만약 '참조 이미지 분석' 내용이 없다면) 오직 페르소나의 특징과 마케팅 인사이트만을 활용한 창의적인 확산 전략을 제안.
    """
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)

    # 사용자 메시지: 분석할 데이터 전달
    human_template = """
    아래 데이터를 바탕으로 광고 컨셉 제안을 시작해주세요.

    ### 타겟 고객 페르소나
    {persona_description}

    ### 타겟 고객 마케팅 인사이트
    {marketing_insights}

    {image_analysis}
"""
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)

    # ChatPromptTemplate으로 조합
    concept_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
    # Pydantic 모델 정의 안하고 출력 구조를 명시하지 않아서 LLM이 자유롭게 답변할 수 있도록 함
    # 체인의 최종 출려 구조는 LLM의 답변이 됨 
    concept_chain = concept_prompt | text_llm
    
    print("💡 광고 컨셉 생성 중...")
    result = await concept_chain.ainvoke({
        "persona_description": persona.persona_description,
        "marketing_insights": persona.marketing_insights,
        "image_analysis": image_analysis
    })
    
    print("✅ 광고 컨셉 생성 완료")
    #LLM의 답변만 가져오기 위해 content 속성 사용
    return {
        "ad_concept": result.content,
        "image_analyses": analyzed_images
    }

# ==================================================================================
"""
    사용자가 앞선 단계에서 생성된 광고 컨셉 프롬프트를 기반으로 광고 제작 아이디어를 작성
    사용자의 광고 아이디어를 기반으로 LLM이 장면별 프롬프트 생성
"""
async def generate_scene_prompts(
    user_description: str, 
    enriched_images: List[ReferenceImageWithDescription], 
    persona_data: dict = None, 
    ad_concept: str = None
) -> StoryboardOutput:

    # 페르소나 정보를 문자열로 포맷팅
    persona_context = ""
    if persona_data:
        persona_context = f"""
### 🎯 Step1에서 생성된 타겟 페르소나 정보
**타겟 고객:**
- 국가: {persona_data.get('target_customer', {}).get('country', 'N/A')}
- 연령대: {persona_data.get('target_customer', {}).get('age_range', 'N/A')}
- 성별: {persona_data.get('target_customer', {}).get('gender', 'N/A')}
- 관심사: {persona_data.get('target_customer', {}).get('interests', 'N/A')}

**페르소나 설명:**
{persona_data.get('persona_description', 'N/A')}

**마케팅 인사이트:**
{persona_data.get('marketing_insights', 'N/A')}
"""

    # 광고 컨셉 정보를 문자열로 포맷팅
    concept_context = ""
    if ad_concept:
        concept_context = f"""
### 💡 Step2에서 생성된 광고 컨셉
{ad_concept}
"""

    # AI 분석 결과를 바탕으로 프롬프트에 포함시킬 문자열 준비
    reference_info = ""
    if enriched_images:
        # 유효한 참조 이미지만 필터링
        valid_images = []
        for ref_img in enriched_images:
            if (ref_img.uri and 
                ref_img.uri != "string" and 
                ref_img.uri.startswith(("http://", "https://")) and
                ref_img.tag and 
                ref_img.tag != "string"):
                valid_images.append(ref_img)
            else:
                print(f"⚠️ 유효하지 않은 참조 이미지 제외: URI='{ref_img.uri}', TAG='{ref_img.tag}'")
        
        if valid_images:
            reference_info = "\n### 📸 사용 가능한 참조 이미지 정보 (JSON 형식)\n"
            for ref_img in valid_images:
                # model_dump_json을 사용해 Pydantic 객체를 읽기 좋은 JSON 문자열로 변환
                reference_info += f"- @{ref_img.tag}: {ref_img.model_dump_json(indent=2)}\n"
            reference_info += "\n"
        else:
            print("⚠️ 모든 참조 이미지가 유효하지 않습니다. 텍스트 프롬프트만 사용합니다.")
            reference_info = ""

    # 시스템 메시지: AI의 역할과 데이터 통합 지시사항
    system_template = """
    당신은 AI 스토리보드 생성 전문가이자, AI 이미지 생성 프롬프트 엔지니어입니다.
    사용자가 Step1에서 생성한 페르소나와 Step2에서 생성한 광고 컨셉, 그리고 Step3에서 입력한 아이디어를 종합적으로 분석하여, 일관성 있고 타겟팅된 3개의 장면으로 구성된 완전한 `StoryboardOutput` JSON 객체를 생성해야 합니다.

    ### 🚨🚨🚨 최우선 원칙: 전체 워크플로우 데이터 통합 🚨🚨🚨
    - **Step1 페르소나 데이터**: 타겟 고객의 특성, 관심사, 인구통계학적 정보를 모든 장면에 반영
    - **Step2 광고 컨셉**: 생성된 광고 전략과 마케팅 인사이트를 장면 설계에 통합
    - **Step3 사용자 아이디어**: 사용자가 직접 입력한 구체적인 아이디어를 최종 실행 방향으로 적용
    - **모든 단계의 데이터가 서로 연결되고 일관성을 유지해야 합니다**

    ### ⭐ 통합 원칙: 3단계 데이터 융합
    1. **페르소나 반영**: 타겟 고객의 연령대, 성별, 관심사, 문화적 배경이 모든 장면에 자연스럽게 녹아들어야 함
    2. **광고 컨셉 활용**: Step2에서 생성된 크리에이티브 컨셉과 핵심 메시지가 시각적으로 구현되어야 함
    3. **사용자 아이디어 실현**: Step3에서 입력한 구체적인 아이디어가 장면의 핵심 요소로 구현되어야 함

    ### 🎯 장면별 설계 원칙
    **장면 1 (도입)**: 타겟 페르소나가 공감할 수 있는 상황/문제 제시
    **장면 2 (전개)**: 사용자 아이디어의 핵심 요소를 광고 컨셉에 맞게 시각화
    **장면 3 (클라이맥스)**: 페르소나의 욕구를 충족시키는 해결책/결과 제시

    ### ⭐ 작성 원칙
    - **`prompt_text`는 영어로 작성**: `scenes` 안의 모든 `prompt_text` 필드는 이미지 생성 AI가 더 잘 이해할 수 있도록 **반드시 영어로 작성**해주세요.
    - **나머지 필드는 한국어로 작성**: `video_concept`과 같은 다른 모든 텍스트 필드는 한국어로 작성합니다.

    ### 🚨 참조 이미지 처리 방법
    **1. 창의적 판단 우선 (Creative Judgment First):**
    - 참조 이미지 사용은 **선택 사항**이며, 필수가 아닙니다.
    - 오직 해당 장면의 아이디어를 **더욱 강화하거나 명확하게 전달**하는 데 도움이 된다고 판단될 때만 이미지를 사용하세요.
    - 만약 참조 이미지를 사용하는 것보다 텍스트 프롬프트만으로 장면을 묘사하는 것이 더 창의적이거나 효과적이라면, **과감하게 사용하지 마세요.** 이 경우 **`reference_images` 키를 아예 포함하지 마세요**(빈 리스트도 금지).

    **2. 참조 이미지 사용 시 준수 사항 (Rules for When You *Do* Use an Image):**
    - **두 가지 작업(`prompt_text`에 @태그 포함, `reference_images` 리스트 채우기)을 한 세트로 반드시 수행**해야 합니다.
    - 최종 `reference_images` 리스트에는 `analysis` 필드를 제외하고 `uri`와 `tag`만 포함시켜야 합니다.

    **3. 참조 이미지가 처음부터 없는 경우 (When No Images are Provided at All):**
    - '사용 가능한 참조 이미지 정보'가 비어있다면, 모든 장면에서 `reference_images` 키를 넣지 마세요.

    ### 📝 최종 출력 구조 (StoryboardOutput)
    당신은 반드시 아래 설명된 `StoryboardOutput` 전체 구조에 맞는 JSON 객체 하나만 출력해야 합니다. 다른 텍스트는 절대 추가하지 마세요.

    - `scenes` (필수): `SceneImagePrompt` 구조를 따르는 장면 객체들의 목록.
    - `total_scenes` (필수): 생성된 총 장면의 수 3.
    - `estimated_duration` (필수): 전체 영상의 예상 길이 (초 단위 정수, 장면당 5초로 계산).
    - `video_concept` (필수): 광고 영상의 핵심 컨셉을 1~2문장으로 요약.

    [최종 확인 지시]
    출력하기 전, 당신이 생성한 JSON이 다음 사항을 모두 충족하는지 반드시 확인하십시오:
    - **Step1 페르소나의 타겟 고객 특성이 모든 장면에 반영되었습니까?**
    - **Step2 광고 컨셉의 핵심 메시지가 시각적으로 구현되었습니까?**
    - **Step3 사용자 아이디어가 장면의 핵심 요소로 실현되었습니까?**
    - **3개 장면이 서로 연결되어 하나의 완전한 스토리를 구성합니까?**
    - `reference_images` 리스트에 객체가 있다면, 같은 장면의 `prompt_text`에 해당 `@태그`가 반드시 포함되어 있습니까?
    - 참조 이미지를 사용하지 않는 장면에는 `reference_images` 키가 없는지 확인했습니까?
    """
    system_message_prompt = SystemMessagePromptTemplate.from_template(system_template)

    # 사용자 메시지 템플릿
    human_template = """
    ### 🎯 Step1: 타겟 페르소나 정보 (필수 반영)
    {persona_context}
    
    ### 💡 Step2: 광고 컨셉 정보 (필수 반영)
    {concept_context}
    
    ### ✏️ Step3: 사용자 최종 아이디어 (실행 방향)
    사용자가 입력한 구체적인 아이디어: "{user_description}"
    
    ### 📸 참조 이미지 정보 (선택적 활용)
    {reference_info}
    
    ### 🚨 통합 지시사항 🚨
    위의 모든 정보를 종합하여 다음과 같이 스토리보드를 생성하세요:
    
    1. **페르소나 타겟팅**: Step1의 타겟 고객 특성(연령, 성별, 관심사)이 모든 장면에 반영되어야 합니다.
    2. **컨셉 일관성**: Step2의 광고 컨셉과 마케팅 전략이 시각적으로 구현되어야 합니다.
    3. **아이디어 실현**: Step3의 사용자 아이디어가 핵심 스토리라인으로 실행되어야 합니다.
    
    **모든 장면이 서로 연결되어 타겟 페르소나에게 어필하는 완전한 광고 스토리를 만들어주세요.**
    
    ---
    🎬 최종 확인 체크리스트:
    ✅ 페르소나의 타겟 고객 특성이 모든 장면에 반영되었습니까?
    ✅ 광고 컨셉의 핵심 메시지가 시각적으로 구현되었습니까?
    ✅ 사용자 아이디어가 스토리의 핵심으로 실현되었습니까?
    ✅ 3개 장면이 하나의 완전한 광고 스토리를 구성합니까?
    
    위 모든 항목을 확인한 후, 통합된 완전한 스토리보드 JSON 객체를 생성해주십시오.
    """
    human_message_prompt = HumanMessagePromptTemplate.from_template(human_template)
    
    # 체인 구성
    storyboard_prompt = ChatPromptTemplate.from_messages([system_message_prompt, human_message_prompt])
    structured_llm = text_llm.with_structured_output(StoryboardOutput)
    storyboard_chain = storyboard_prompt | structured_llm

    print(f"🎬 장면별 프롬프트 생성 중... 사용자 입력: '{user_description}'")
    
    # 사용자 입력을 로그로 명확히 출력
    print(f"📝 실제 전달되는 사용자 입력: {user_description}")
    print(f"📝 사용자 입력 타입: {type(user_description)}")
    print(f"📝 사용자 입력 길이: {len(user_description) if user_description else 0} 글자")
    print(f"📸 참조 이미지 개수: {len(enriched_images) if enriched_images else 0}")
    
    # 페르소나 및 컨셉 정보 로그 출력
    print(f"🎯 페르소나 데이터 존재: {bool(persona_data)}")
    if persona_data:
        print(f"   타겟 고객 정보: {persona_data.get('target_customer', {})}")
    print(f"💡 광고 컨셉 존재: {bool(ad_concept)}")
    if ad_concept:
        print(f"   광고 컨셉 미리보기: {ad_concept[:100]}...")
    
    result = await storyboard_chain.ainvoke({
        "user_description": user_description,
        "reference_info": reference_info,
        "persona_context": persona_context,
        "concept_context": concept_context,
    })

    print("✅ 장면별 프롬프트 생성 완료")
    print(f"📊 생성된 장면 수: {result.total_scenes}")
    print(f"🎯 첫 번째 장면 프롬프트: {result.scenes[0].prompt_text if result.scenes else 'None'}")
    return result

# ==================================================================================
"""스토리보드 장면 이미지를 Runway API로 생성"""
async def generate_images_sequentially(
    scenes: List[SceneImagePrompt],
    api_key: str
) -> List[Dict]:
    """여러 장면 프롬프트를 받아 '직렬'로 이미지 생성을 요청하고 모든 결과를 반환합니다."""
    
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json", "X-Runway-Version": "2024-11-06"}
    base_url = "https://api.dev.runwayml.com/v1"
    
    generated_images = []
    total_scenes = len(scenes)
    
    print(f"\n🚀 총 {total_scenes}개의 이미지 생성을 직렬로 시작합니다...")

    for i, scene in enumerate(scenes):
        print(f"\n--- [장면 {i+1}/{total_scenes}] 이미지 생성 시작 ---")
        
        payload = scene.model_dump(by_alias=True, exclude_none=True)
        
        # 🔧 Runway API 호환성을 위한 필수 값들 강제 수정
        # 1. model 필드 강제 고정 - 텍스트-이미지 생성용 모델로 변경
        payload["model"] = "gen4_image"
        print(f"🔧 API 요청 전 model 강제 설정: {payload['model']}")
        
        # 2. ratio 값 강제 수정
        if payload.get("ratio") not in ["1280:720", "720:1280", "1024:1024"]:
            old_ratio = payload.get("ratio", "unknown")
            payload["ratio"] = "1280:720"  # 기본값으로 강제 변경
            print(f"🔄 API 요청 전 ratio 수정: {old_ratio} → {payload['ratio']}")
        
        # 잘못된 참조 이미지 필터링 및 안전장치
        if payload.get("referenceImages"):
            valid_ref_images = []
            for ref_img_dict in payload["referenceImages"]:
                # 'string'이나 잘못된 URI 필터링
                if (ref_img_dict.get("uri") and 
                    ref_img_dict.get("uri") != "string" and 
                    ref_img_dict.get("uri").startswith(("http://", "https://")) and
                    ref_img_dict.get("tag") and 
                    ref_img_dict.get("tag") != "string"):
                    ref_img_dict["weight"] = 0.5
                    valid_ref_images.append(ref_img_dict)
                else:
                    print(f"⚠️ 잘못된 참조 이미지 제외: {ref_img_dict.get('uri')}")
            
            # 유효한 참조 이미지가 없으면 referenceImages 키 제거
            if valid_ref_images:
                payload["referenceImages"] = valid_ref_images
            else:
                print("🔧 모든 참조 이미지가 유효하지 않아 텍스트 프롬프트만 사용합니다.")
                payload.pop("referenceImages", None)
        else:
            # 참조 이미지가 없거나 빈 배열인 경우 키 자체를 제거
            print("🔧 참조 이미지가 없어 텍스트 프롬프트만 사용합니다.")
            payload.pop("referenceImages", None)

        async with httpx.AsyncClient(timeout=180) as client:
            try:
                # 1. 작업 요청
                print(f"📤 Runway API 요청: {scene.prompt_text[:40]}...")
                print(f"🔍 전송할 payload: {payload}")  # 디버깅용 출력
                response = await client.post(f"{base_url}/text_to_image", headers=headers, json=payload)
                
                if response.status_code != 200:
                    raise Exception(f"API 요청 실패: {response.text}")
                
                task_id = response.json()["id"]
                print(f"  -> 작업 ID: {task_id}")

                # 2. 작업 완료까지 폴링
                for attempt in range(36):
                    print(f"⏳ 이미지 생성 진행 확인 중... ({attempt + 1}/{36})")
                    status_response = await client.get(f"{base_url}/tasks/{task_id}", headers=headers)
                    status_data = status_response.json()
                    status = status_data.get("status")
                    progress = status_data.get("progress", 0)
                    print(f"   상태: {status}, 진행도: {progress}%")

                    if status == "SUCCEEDED":
                        print(f"✅ [장면 {i+1}] 이미지 생성 완료!")
                        generated_images.append({
                            "scene_index": i + 1,
                            "status": "success",
                            "url": status_data.get("output", [None])[0],  # 이미지 URL로 저장
                            "image_url": status_data.get("output", [None])[0],  # 호환성을 위한 추가 키
                            "prompt": scene.prompt_text
                        })
                        break
                    elif status == "FAILED":
                        error_msg = status_data.get("error", "알 수 없는 오류")
                        print(f"❌ [장면 {i+1}] 이미지 생성 실패: {error_msg}")
                        generated_images.append({"scene_index": i + 1, "status": "failed", "error": error_msg, "prompt": scene.prompt_text})
                        break
                    
                    await asyncio.sleep(5)
                else:
                    raise Exception("이미지 생성 시간 초과")

            except Exception as e:
                print(f"❌ [장면 {i+1}] 처리 중 오류 발생: {e}")
                generated_images.append({"scene_index": i + 1, "status": "error", "error": str(e), "prompt": scene.prompt_text})

    print("\n🎉 모든 이미지 생성 작업 완료!")
    return generated_images

# ==================================================================================
"""참조 이미지 분석 : 참조 이미지를 분석해 광고 콘셉트 및 크리에이티브 방향성을 도출"""
async def analyze_reference_images(reference_images: List[ReferenceImage]) -> List[dict]:
    if not reference_images:
        return []
    # 분석 결과 저장할 변수
    analyzed_result = []
    
    for ref_image in reference_images:
        # 유효하지 않은 URI 필터링 (string, 빈 값, 잘못된 URL 등)
        if (not ref_image.uri or 
            ref_image.uri == "string" or 
            not ref_image.uri.startswith(("http://", "https://")) or
            not ref_image.tag or 
            ref_image.tag == "string"):
            print(f"⚠️ 유효하지 않은 참조 이미지 건너뛰기: URI='{ref_image.uri}', TAG='{ref_image.tag}'")
            continue
            
        try:
            message = HumanMessage(
                content=[
                    {
                        "type": "text",
                        "text": f"""이 이미지를 {ref_image.tag}로 광고에 활용하려고 합니다.
                        주요 특징과 광고 활용 포인트를 분석해주세요"""
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": ref_image.uri,
                            "detail": "auto"  # low와 high가 있음 , 핵심은 이미지의 세부적인 부분까지 분석이 가능하냐마냐의 차이
                        }
                    }
                ]
            )
            # LLM에 이미지 분석 요청
            result = await vision_llm.ainvoke([message])
            
            analyzed_result.append({
                "tag": ref_image.tag,
                "uri": ref_image.uri,
                "analysis": result.content
            })
            print(f"✅ @{ref_image.tag} 분석 완료")
            
        except Exception as e:
            print(f"⚠️ @{ref_image.tag} 분석 실패: {e}")
            analyzed_result.append({
                "tag": ref_image.tag,
                "uri": ref_image.uri,
                "analysis": "이미지 분석을 수행할 수 없습니다."
            })
    
    return analyzed_result

# ==================================================================================
