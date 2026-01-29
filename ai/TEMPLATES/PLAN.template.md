# Migration Plan
- target: {{TARGET}}
- recipe: {{RECIPE_ID}}
- created_at: {{CREATED_AT}}

## Intended changes
{{CHANGES}}

## Tokens
{{TOKENS}}

## Apply
```bash
git apply patches/0001-*.patch
```

## Verify
{{VERIFY}}

## Rollback
```bash
git apply -R patches/0001-*.patch
```
