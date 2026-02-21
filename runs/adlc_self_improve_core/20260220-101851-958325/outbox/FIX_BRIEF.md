# Fix Brief

- label: `DOC_FAIL`
- verify_rc: `1`
- matched_keywords: `sync_doc_links, doc index check, doc index`

## Minimal Next Actions
- Run `python scripts/sync_doc_links.py` to resync README doc index.
- Re-run `scripts/verify_repo.*` and confirm doc index gate is green.

## Related File References
- `docs/03_quality_gates.md:28-28`
- `scripts/sync_doc_links.py:43-43`
- `scripts/verify_repo.ps1:215-215`
- `scripts/verify_repo.sh:201-201`
- `scripts/workflows/adlc_self_improve_core.py:283-441`
- `simlab/_runs/20260218-222104/S00_lite_headless/sandbox/scripts/sync_doc_links.py:37-37`

## Verify stdout summary
```
[contract_checks] schema presence ok
[contract_checks] meta schema_version ok
[contract_checks] readme links ok
[contract_checks] unique Graph Spider implementation ok
[verify_repo] doc index check (sync doc links --check)
[sync_doc_links] ok
[verify_repo] lite scenario replay
{"run_dir": "C:/Users/sunom/AppData/Local/ctcp/runs/ctcp/simlab_runs/20260220-101855", "passed": 7, "failed": 1}
```

## Verify stderr summary
```
Invoke-ExternalChecked : [verify_repo] FAILED: lite scenario replay (exit=1)
At D:\.c_projects\adc\ctcp\scripts\verify_repo.ps1:230 char:7
+       Invoke-ExternalChecked -Label "lite scenario replay" -Command {
+       ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
+ CategoryInfo          : NotSpecified: (:) [Write-Error], WriteErrorException
+ FullyQualifiedErrorId : Microsoft.PowerShell.Commands.WriteErrorException,Invoke-ExternalChecked
```
