# Intent Brief

## Goal Judgment

Shift CTCP source_generation from opaque complete-project dumping toward auditable, library-first, provider-authored source assembly.

## Target User

Project-generation users who want CTCP to produce a runnable MVP with less API cost, fewer fake implementations, and clearer failure evidence.

## Main Problem

The previous VN complete-project run showed that one large source_generation batch can produce many files while still failing on syntax, cross-file interfaces, and missing evidence. The runtime needs smaller file-level contracts and local verification before delivery claims.

## Desired Outcome

The first source_generation foundation should expose intent/spec/library/file-task artifacts, normalize provider file payloads robustly, default chunked API generation to one file per content batch, and block delivery when provider source or library-policy checks are missing.
