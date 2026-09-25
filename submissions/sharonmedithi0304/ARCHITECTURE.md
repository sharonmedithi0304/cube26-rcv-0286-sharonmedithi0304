# Receiving Manager Architecture

## 1. Purpose

The Receiving Manager verifies whether received inventory matches the expected purchase-order information and records evidence for each inspection decision.

The system must not invent evidence. When available evidence is insufficient, the inspection returns `UNCERTAIN`.

---

## 2. Inspection Flow

```text
Purchase Order
      +
Product Specification
      +
Receiving Photos
      ↓
Receiving Inspection Agent
      ↓
┌─────────────────────────────┐
│ Identity                    │
│ Carton Count                │
│ Units per Carton            │
│ Quantity                    │
│ Carton Damage               │
│ Unit Damage                 │
│ Colour                      │
│ Variant                     │
│ Components                  │
│ Quality Flags               │
└─────────────────────────────┘
      ↓
Evidence + Verdicts
      ↓
PASS / FAIL / UNCERTAIN
      ↓
Decision Trace
      ↓
Evidence Record
```

## 3. Vision Adapter Boundary

`agent/vision_adapter.py` is the only model-facing layer. For one receiving
unit it sends one request containing the expected PO/product fields, all image
references and all ten required checks. The model returns observations only:
`observed_value`, `evidence` source references, `uncertainty`, and `reason`.

The adapter validates the complete response and rejects missing fields,
unavailable image references, invalid values, and malformed JSON. It maps the
observations into the existing flat input used by `inspection_agent.py`, which
remains responsible for PASS/FAIL/UNCERTAIN comparisons and the decision trace.
The model never produces the final verdict. Missing visual evidence produces
UNCERTAIN checks. Model failures and invalid responses preserve the receiving
record and return `status: "pending"` with a `pending_review` finding.

The provider is injected as a callable receiving one payload, so provider
credentials and SDK choices remain outside this repository's decision logic.