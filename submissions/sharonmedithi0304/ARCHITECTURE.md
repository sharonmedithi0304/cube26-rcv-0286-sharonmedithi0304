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