# Virtus Technical Architecture - Executive Summary

**Document Version**: 1.0  
**Date**: 2026-05-14  
**Classification**: Internal / Investor

---

## Overview

Virtus is an 8-agent AI system that automates lead generation, sales, and closing for solopreneurs, coaches, and consultants. Built on Anthropic's official Orchestrator-Worker pattern, it transforms the "selling time" business model into a "selling results and systems" model.

---

## Architecture Pattern

### Orchestrator-Worker Design

```
                    ┌─────────────────────────┐
                    │   Lead Strategist       │
                    │   (Opus 4.7)            │
                    │   ── Orchestrator ──    │
                    └───────────┬─────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  Researcher   │       │   Drafter     │       │   Designer    │
│  (Sonnet 4.6) │       │  (Sonnet 4.6) │       │  (Sonnet 4.6) │
└───────────────┘       └───────────────┘       └───────────────┘
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐       ┌───────────────┐       ┌───────────────┐
│  Distributor  │       │  Connector    │       │   Analyst     │
│  (Haiku 4.5)  │       │  (Sonnet 4.6) │       │  (Sonnet 4.6) │
└───────────────┘       └───────────────┘       └───────────────┘
                                │
                    ┌───────────┴───────────┐
                    │      Guardian         │
                    │      (Opus 4.7)       │
                    │   ── Quality Gate ──  │
                    └───────────────────────┘
```

---

## 8-Agent System

| Agent | Model | Role | Key Output |
|-------|-------|------|------------|
| **Lead Strategist** | Opus 4.7 | Orchestrator, strategy, customer interface | Morning brief, monthly strategy |
| **Researcher** | Sonnet 4.6 | Market research, lead discovery | 50+ leads/week from PR Times |
| **Drafter** | Sonnet 4.6 | All content creation | Articles, social posts, proposals |
| **Designer** | Sonnet 4.6 | Visual generation | Thumbnails, infographics |
| **Distributor** | Haiku 4.5 | Publishing automation | Scheduled API-based distribution |
| **Connector** | Sonnet 4.6 | Relationship management | DM drafts, follow-up sequences |
| **Analyst** | Sonnet 4.6 | Performance analysis | KPI reports, winning patterns |
| **Guardian** | Opus 4.7 | Quality assurance | 95-point quality gate |

---

## Model Selection Strategy

| Tier | Model | Use Case | Rationale |
|------|-------|----------|-----------|
| **Strategic** | Opus 4.7 | Lead Strategist, Guardian | Complex reasoning, quality judgment |
| **Execution** | Sonnet 4.6 | 5 worker agents | Balanced cost-performance |
| **Batch** | Haiku 4.5 | Distributor | High-volume, simple tasks |

**Cost Optimization**: Strategic tasks use premium models; routine operations use cost-efficient alternatives.

---

## Technology Stack

```yaml
Core:
  Implementation: Claude Code
  Language: Python 3.11+
  LLM API: Anthropic Claude API

External Integrations (MCP):
  Required: Notion, Google Drive, Gmail, X API, Instagram Graph API
  Optional: Higgsfield (video), MakeUGC (UGC ads), LinkedIn, GA4

Deployment:
  Phase 1: Customer local environment (Claude Code)
  Phase 2: Vercel + Supabase (Web UI)
  Phase 3: Full SaaS with multi-LLM support
```

---

## Security Model: BYOK

**Bring Your Own Key** (BYOK) architecture ensures:

1. **Customer owns their API keys** - stored only in local `.env`
2. **No server-side key storage** - galaiworks never persists keys
3. **Minimal data retention** - session-only memory for LLM calls
4. **Phase 2 Web UI** - browser localStorage with encryption

```
┌─────────────────────────────────────────────────────┐
│              Customer Environment                    │
│  ┌─────────┐    ┌─────────┐    ┌─────────────────┐  │
│  │  .env   │───▶│ Virtus  │───▶│ Anthropic API   │  │
│  │ API Key │    │ Agents  │    │ (Direct calls)  │  │
│  └─────────┘    └─────────┘    └─────────────────┘  │
└─────────────────────────────────────────────────────┘
                        │
                        ▼
              ┌─────────────────┐
              │  galaiworks     │
              │  (Logic only,   │
              │   no key access)│
              └─────────────────┘
```

---

## 95-Point Quality Loop

All external outputs pass through Guardian's quality gate:

```
[Agent Output] → [Guardian Evaluation] → Score ≥ 95? 
                         │                    │
                         │                 Yes│  → Human Approval Queue
                         │                    │
                         │                 No │
                         ▼                    │
              [Specific Feedback]             │
                         │                    │
                         ▼                    │
              [Agent Revision] ───────────────┘
                         │
              (Max 3 retries, then human escalation)
```

**Evaluation Matrix (100 points)**:
- Brand DNA compliance: 25
- Legal compliance: 25
- Content quality: 20
- Target fit: 15
- Over-promise check: 10
- Hallucination detection: 5

---

## Daily Workflow

| Time | Phase | Agents |
|------|-------|--------|
| 05:00 | Information Gathering | Researcher, Analyst |
| 07:00 | Morning Brief | Lead Strategist |
| 09:00-15:00 | Content Generation | Drafter, Designer, Researcher |
| 15:00 | Distribution | Distributor |
| 18:00 | Relationship Building | Connector |
| 22:00 | Learning Loop | Analyst, Lead Strategist |

**Human Touchpoints**: Morning brief check, content approval only.

---

## Data Architecture

### Brain Layer (Persistent Memory)

```
brain/
├── customers/{id}/brand-dna.md    # Voice, tone, strategy
├── content-history/               # All generated content
├── leads/                         # Lead database with scoring
├── deals/                         # Pipeline and closed deals
└── win-patterns/                  # ML-ready success patterns
```

### Brand DNA Structure

```yaml
identity:    # Who they are
voice:       # How they speak
strategy:    # What they publish
forbidden:   # What they avoid
reference:   # Past successes
```

---

## Competitive Differentiation

| Competitor Type | Example | Virtus Advantage |
|-----------------|---------|------------------|
| SNS-focused | AI Social tools | Full funnel: content → sales → close |
| Marketing platforms | NoimosAI | Solopreneur-optimized, active prospecting |
| Enterprise AI | Agentforce | Accessible pricing, individual focus |
| Contact centers | Sierra, Decagon | Lead generation, not just support |

---

## Implementation Roadmap

| Phase | Timeline | Scope |
|-------|----------|-------|
| **Phase 1** | May-Jul 2026 | 8 agents, Claude Code, Founding Members (30) |
| **Phase 2** | Aug-Oct 2026 | BYOK Web UI, Vercel + Supabase |
| **Phase 3** | Nov 2026-Mar 2027 | Multi-LLM, full SaaS, Stripe billing |
| **Phase 4** | Q2 2027+ | Enterprise: SSO, SOC 2, white-label |

---

## Key Metrics

| Metric | Target |
|--------|--------|
| Article generation | < 5 min |
| Social post generation | < 1 min |
| Morning brief | < 3 min |
| API latency (avg) | < 30 sec |
| Test coverage | > 70% |

---

## Summary

Virtus is a production-ready multi-agent system that:

1. **Follows Anthropic's official patterns** - Orchestrator-Worker architecture
2. **Optimizes cost through model tiering** - Opus for strategy/quality, Sonnet for execution, Haiku for batch
3. **Ensures trust through BYOK** - Customer-controlled API keys
4. **Guarantees quality through the 95-point loop** - No output below threshold
5. **Integrates via standard protocols** - MCP for external services

The architecture is designed for Phase 1 delivery (Founding Members) with clear upgrade paths to full SaaS.

---

**Contact**: galaiworks  
**Repository**: galaiworks/Virtus
