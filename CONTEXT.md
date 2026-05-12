# Agent Cluster Router — Domain Context

## Core Concepts

### Agent Cluster Router
A local routing gateway that sits in front of multiple AI agent backends. Accepts user prompt requests and dynamically routes them to the most appropriate agent backend based on intent classification.

### Router
The central decision layer (`router/routing.py`). Classifies user intent from the prompt text and selects a target backend. Exposes a FastAPI HTTP server on port 8000 (`router/server.py`).

### Intent Classifier
The component within the Router that determines what the user is asking for. Maps natural language to intent categories: CODE (programming help), CHAT (general conversation), MATH (math problems), CREATIVE (writing/art), RESEARCH (factual lookup), PLANNING (project planning). Driven by keyword lists and regex patterns.

### Backend
A downstream AI agent service that actually processes the user's prompt. The Router dispatches to one of multiple backends. Each backend may use different models, providers, or agent configurations.

### Decision Layer
The scoring/tiebreaking mechanism that picks a backend when multiple are eligible. Uses response time history, accuracy, and priority weights.

### Adapter
The interface layer that translates between the Router's internal format and each backend's specific API. Lives in `router/adapters/`. Different backends speak different protocols — the adapter normalizes them.

### Commander
A programmatic priority-override API (`commander/api.py`). Allows temporarily forcing all traffic to a specific backend (override mode), or permanently deprioritizing a failing backend. Useful for maintenance windows and incident response.

## Terminology

| Term | Definition |
|------|------------|
| Router | The main Gateway service that classifies and dispatches requests |
| Backend | A downstream AI agent service (e.g., Hermes, OpenClaw) |
| Intent | The classified purpose of a user's request (CODE, CHAT, MATH, etc.) |
| Adapter | Translation layer between Router and a specific Backend |
| Override | Commander-enforced routing rule that bypasses normal classification |
| Triage | The process of labeling and prioritizing issues (from mattpocock skills) |
| Seam | Where an interface lives — a place behavior can be altered without editing in place |
| Depth | Leverage at the interface: a lot of behavior behind a small interface |

## Architecture

```
Client → Router (:8000) ──[IntentClassifier]──→ Adapter → Backend
                                   │
                                   ├── hermes_adapter → Hermes (:8081)
                                   └── openclaw_adapter → OpenClaw (:8082)
                                                       ↑
                                               Commander API (override)
```

## Current State
- Router: FastAPI on :8000, v5.0, evaluates intents at 99.3% accuracy
- Hermes adapter: :8081, uses deepseek-v4-pro via LuckyAPI
- OpenClaw adapter: :8082, currently mock (real DeepSeek API integration pending)
- Commander API: POST /commander/override (force backend), POST /commander/release (remove override), GET /commander/status

## GitHub
- Repo: `WeneShan/agent-cluster-router`
- Issue tracker: GitHub Issues
- Triage labels: needs-triage, needs-info, ready-for-agent, ready-for-human, wontfix
