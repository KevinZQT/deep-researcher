# Introduction

**Deep Researcher** is a multi-agent framework for in-depth research. It goes beyond a single LLM response by breaking a question into focused searches, gathering evidence, and coordinating a structured research and writing process.

The framework consists of two core components:

- **Researcher** generates search queries, runs web searches in parallel, evaluates the collected information, and identifies gaps that require further investigation. It then synthesizes the findings into research material for the report.
- **ChiefAgent** orchestrates the overall workflow. It plans the report structure, coordinates parallel research across sections, and manages draft review and revision. The workflow includes checks against the collected research and is designed to accommodate human feedback, with the aim of producing detailed, well-organized reports in a formal and objective style.

Together, these components aim to produce detailed, well-structured, and evidence-based research reports.


# Architecture



## Researcher Workflow

```mermaid
flowchart TD
    T([Research topic]) --> Q(Query Generator)

    Q --> S1(Search 1)
    Q --> S2(Search 2)
    Q --> SN(Search N)

    S1 --> E1[Findings 1]
    S2 --> E2[Findings 2]
    SN --> EN[Findings N]

    E1 --> R(Reflection)
    E2 --> R
    EN --> R

    R -.->|Follow-up queries| Q
    R -->|Finish| A(Answer Synthesis)
    A --> OUT([Research Summary])

    classDef main fill:#f4f5f7,stroke:#333,color:#222,stroke-width:2px;
    classDef pink fill:#fce8ec,stroke:#d88999,color:#222,stroke-width:2px;
    classDef blue fill:#e4effc,stroke:#7da5d6,color:#222,stroke-width:2px;
    classDef green fill:#e7f5e9,stroke:#88b893,color:#222,stroke-width:2px;
    classDef output fill:#dceef9,stroke:#333,color:#222,stroke-width:2px;

    class T,Q,R,A main;
    class S1,E1 pink;
    class S2,E2 blue;
    class SN,EN green;
    class OUT output;
```

## ChiefAgent Workflow

```mermaid
flowchart TD
    T([Research topic]) --> R(Initial Research)
    R --> P(Planner)

    P --> S1(Section 1)
    P --> S2(Section 2)
    P --> SN(Section N)

    S1 --> D1[Draft 1]
    S2 --> D2[Draft 2]
    SN --> DN[Draft N]

    D1 --> W(Writer)
    D2 --> W
    DN --> W

    W --> F(Fact Checker)
    F -.->|Revise| W
    F -->|Accept| V(Visualizer)
    V --> PUB(Publisher)
    PUB --> OUT([Markdown Report])

    classDef main fill:#f4f5f7,stroke:#333,color:#222,stroke-width:2px;
    classDef pink fill:#fce8ec,stroke:#d88999,color:#222,stroke-width:2px;
    classDef blue fill:#e4effc,stroke:#7da5d6,color:#222,stroke-width:2px;
    classDef green fill:#e7f5e9,stroke:#88b893,color:#222,stroke-width:2px;
    classDef output fill:#dceef9,stroke:#333,color:#222,stroke-width:2px;

    class T,R,P,W,F,V,PUB main;
    class S1,D1 pink;
    class S2,D2 blue;
    class SN,DN green;
    class OUT output;
```

# Quick Start

Requires Python 3.12 and a Gemini API key.

Name the local project folder `deep_researcher` and run the setup commands from that directory.

## Setup

Create and activate a virtual environment, then install the dependencies:

```bash
python -m venv .venv

# Windows PowerShell
.\.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate

python -m pip install -r requirements.txt
```

Copy `.env.sample` to `.env` and set:

```dotenv
GEMINI_API_KEY=your_api_key
RESEARCH_MODEL_ID=your_model_id
```

Choose a Gemini model that supports Google Search grounding and structured output. Use the model ID without the `google_genai/` prefix.

## Run

From the parent directory:

```bash
cd ..
python -m uvicorn deep_researcher.backend.app:app --reload --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 to start a research task and download the report.

Alternatively, run the command-line example:

```bash
python -m deep_researcher.main
```

Edit the `task` dictionary in `main.py` to change the example topic and research settings. For the web app, these settings are in `backend/app.py`.
