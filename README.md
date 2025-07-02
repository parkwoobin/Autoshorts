# 🚀 쇼츠파일럿 (Shorts Pilot)

[cite_start]**AI 기반 숏폼 광고 영상 자동 제작 솔루션 by PuzzlePlug** [cite: 2, 3]

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen)](https://github.com)
[![License](https://img.shields.io/badge/license-MIT-blue)](https://github.com)

[cite_start]쇼츠파일럿은 생성형 AI 기술을 활용하여 소상공인과 마케터들이 겪는 영상 제작의 어려움을 해결하는 서비스입니다. [cite: 14, 29] [cite_start]사용자가 원하는 광고 컨셉과 타겟 고객을 입력하면, AI가 최신 트렌드를 반영하여 48시간 내에 맞춤형 숏폼 영상 3편을 자동으로 제작해 제공합니다. [cite: 12, 14, 16]

---

## 🎯 주요 문제점 (The Problem)

[cite_start]숏폼 콘텐츠 시장은 폭발적으로 성장하고 있지만, 많은 소상공인 및 관광 사업자들은 영상 제작에 다음과 같은 어려움을 겪고 있습니다. [cite: 25, 26, 28]

* [cite_start]**높은 제작 비용**: 외주 제작 시 상당한 비용이 발생합니다. [cite: 29]
* [cite_start]**전문성 및 시간 부족**: 영상 기획, 촬영, 편집에 대한 전문 지식이 없고 시간이 부족합니다. [cite: 29]
* **마케팅 효과의 불확실성**: 많은 노력에도 불구하고 실제 매출로 이어질지 확신하기 어렵습니다.

[cite_start]우리의 주요 타겟은 디지털 마케팅에 관심은 많지만 영상 제작 기술과 예산이 부족한 20~40대 소상공인과 관광 사업자입니다. [cite: 30]

---

## ✨ 핵심 기능 및 가치 (Core Features & Value)

쇼츠파일럿은 다음과 같은 핵심 가치를 제공하여 위 문제들을 해결합니다.

* [cite_start]**⚡ 신속성과 편의성**: 복잡한 과정 없이 단 48시간 내에 맞춤형 숏폼 영상을 받아볼 수 있습니다. [cite: 18, 19]
* [cite_start]**🤖 AI 기반 자동 최적화**: 사용자가 입력한 타겟(국가, 연령, 성별)과 관심사에 맞춰 AI가 최적화된 콘텐츠를 자동으로 생성합니다. [cite: 20, 21]
* [cite_start]**💰 실질적 매출 증대**: 제작된 영상을 자체 채널에 교차 노출하여 추가적인 홍보 및 매출 증대 효과를 기대할 수 있습니다. [cite: 22, 23]

---

## ⚙️ 기술 스택 및 아키텍처 (Tech Stack & Architecture)

[cite_start]쇼츠파일럿은 다양한 AI API와 라이브러리를 유기적으로 연결한 자동화 파이프라인을 기반으로 동작합니다. [cite: 119]

| 단계 | 기술 | 역할 |
| :--- | :--- | :--- |
| **트렌드 분석** | `Google Trends API`, `YouTube Data API` | [cite_start]타겟 시장의 최신 관심사, 인기 키워드, 콘텐츠 특징을 파악합니다. [cite: 39, 42] |
| **시나리오 생성** | `OpenAI API (GPT-4.1-mini)` | [cite_start]사용자의 입력과 트렌드 분석 결과를 바탕으로 광고 시나리오 스크립트를 생성합니다. [cite: 74] |
| **영상/이미지 생성** | `Runway AI API` | [cite_start]생성된 시나리오에 맞춰 각 장면(Scene)에 해당하는 영상과 이미지를 생성합니다. [cite: 76] |
| **음성 및 자막** | `ElevenLabs API`, `Whisper AI API` | [cite_start]광고에 맞는 음성(TTS)을 생성하고, 이를 기반으로 자막(STT)을 자동 생성합니다. [cite: 78] |
| **배경 음악** | `Lyricc2 API`, `Freesound` | [cite_start]영상 분위기에 맞는 배경 음악을 자동 생성하거나 무료 음원을 활용합니다. [cite: 80, 122] |
| **영상 병합/편집** | `FFmpeg`, `MoviePy` | [cite_start]생성된 모든 요소(영상, 자막, 음성, 음악)를 병합하고, 트랜지션 및 효과를 적용하여 최종 영상을 완성합니다. [cite: 82] |

---

## 🌊 사용자 플로우 (User Flow)

[cite_start]사용자는 단 3단계의 간단한 과정을 통해 광고 영상을 제작할 수 있습니다. [cite: 48, 52, 56]

1.  **광고 정보 입력**:
    * [cite_start]타겟 고객의 국가, 연령, 성별, 관심사 키워드를 선택합니다. [cite: 50]
    * [cite_start]제작하고 싶은 광고의 컨셉과 상품 정보를 자유롭게 입력합니다. [cite: 51]
    * ![사용자 입력 화면](https://i.imgur.com/uRjJ4Jz.png) 2.  **스토리보드 확인 및 수정**:
    * [cite_start]AI가 생성한 장면별 스토리보드를 확인합니다. [cite: 54]
    * [cite_start]드래그앤드롭으로 장면 순서를 자유롭게 변경하거나 수정할 수 있습니다. [cite: 55]
    * ![스토리보드 수정 화면](https://i.imgur.com/xI6t0zZ.png) 3.  **최종 영상 확인 및 다운로드**:
    * [cite_start]하나의 코어 영상을 기반으로 생성된 3가지 버전의 영상을 확인합니다. [cite: 58]
    * [cite_start]마음에 드는 영상을 선택하여 다운로드하거나 공유할 수 있습니다. [cite: 59]

---

## 📈 비즈니스 모델 (Business Model)

[cite_start]쇼츠파일럿의 수익 모델은 다음과 같습니다. [cite: 108]

* **영상 제작 수수료**:
    * [cite_start]**단건 패키지**: 1편당 30,000원 (1회 수정 가능) [cite: 110]
    * [cite_start]영상 1편 제작 시 API 비용은 약 14,400원으로, 수익성을 확보한 모델입니다. [cite: 120]
* **교차 광고 수수료**:
    * [cite_start]자체 채널 및 고객 채널 간 교차 홍보 진행 시 발생하는 거래액의 5~20%를 수수료로 부과합니다. [cite: 113]

---

## 🚀 시작하기 (Getting Started)

프로젝트를 로컬 환경에서 실행하려면 아래의 지침을 따라주세요.

### Prerequisites

* Python 3.8+
* pip
* FFmpeg

### Installation

1.  저장소를 클론합니다.
    ```bash
    git clone [https://github.com/your-username/shorts-pilot.git](https://github.com/your-username/shorts-pilot.git)
    cd shorts-pilot
    ```
2.  필요한 패키지를 설치합니다.
    ```bash
    pip install -r requirements.txt
    ```
3.  `.env` 파일을 생성하고 필요한 API 키를 입력합니다.
    ```env
    OPENAI_API_KEY="YOUR_API_KEY"
    RUNWAY_API_KEY="YOUR_API_KEY"
    ELEVENLABS_API_KEY="YOUR_API_KEY"
    ```

### Running the App

```bash
python main.py
