TeamNet x ADLC Overview (v0.1)
1) TeamNet (roles & connections)
                 ┌──────────────┐
                 │ Local Librarian│  (read-only)
                 └──────┬───────┘
                        │ context_pack/file_supply
                        ▼
┌──────────────┐   ┌──────────────────────┐   ┌──────────────────┐
│ Researcher    │──▶│     Blackboard       │◀──│ Contract Guardian │
│ (web find opt)│   │ (artifacts + work)   │   │ (adversarial)     │
└──────────────┘   └──────────┬───────────┘   └──────────────────┘
                              │
                              ▼
                       ┌──────────────┐
                       │ Chair/Planner │  (only decision)
                       └───┬─────┬────┘
                           │     │ review_cost
                           │     ▼
                           │  ┌──────────────┐
                           │  │ CostController│ (adversarial)
                           │  └──────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ PatchMaker    │ (execute)
                    └──────┬───────┘
                           │ diff.patch
                           ▼
                    ┌──────────────┐
                    │ Local Verifier│ (fact judge)
                    └───┬─────┬────┘
                        │PASS │FAIL bundle
                        │     ▼
                        │  ┌──────────────┐
                        └─▶│ Fixer         │ (execute)
                           └──────────────┘

2) ADLC mainline (agents as helpers)
doc        analysis      find           plan             build⇄verify        contrast→fix        deploy/merge
│          │             │              │                │                  │                   │
│          │             │              │                │                  │                   │
Local      Chair         resolver        Chair + reviews  Verifier           Fixer               Chair
Librarian  (decision)    (+web optional) (sign plan)      (evidence/bundle)  (patch loop)        (report)


Rules:

Execution begins ONLY after PLAN is signed.

Reviews must exist and be APPROVE before signing.
