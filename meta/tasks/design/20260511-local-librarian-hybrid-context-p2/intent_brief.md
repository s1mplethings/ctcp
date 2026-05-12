# Intent Brief

## Goal Judgment

Continue CTCP's staged redesign by making the local Librarian provide richer, auditable retrieval context before project/source generation.

## Target User

CTCP users who want fewer repeated API calls and better generation quality through local reuse of repo contracts, historical failures, recipes, and library docs.

## Main Problem

The current Librarian can build a context pack, but sparse requests do not leave enough retrieval evidence to prove which local knowledge influenced downstream agents. It also lacks a dedicated librarian context-pack artifact matching the library-first generation direction.

## Desired Outcome

The local Librarian should output a context pack with hybrid retrieval trace, selected context metadata, downstream constraints, and a companion `librarian_context_pack.json` while preserving current `context_pack.json` compatibility.
