# Release-readiness review — <project>

Commit/branch: <identity>

Working tree: <clean/dirty>

Review date and scope: <date, outcome>

Record evidence rather than checkbox completion. Omit inapplicable rows with a
reason. A passing check establishes only what it covers.

| Dimension | Evidence: command/journey + result + artifact | Unverified / risk |
|---|---|---|
| Correctness | Relevant regression and project gate | |
| Real user journey | Actual entry → task → outcome | |
| UI behavior, if changed | Keyboard/focus, loading/empty/error/recovery/success and resulting state | |
| Semantics, if applicable | Actual platform roles/names/states/actions; manual assessment labelled separately | |
| Visual, if claimed | Target viewport/theme/state screenshots and layout/style review | |
| Native/package, if claimed | Actual named app/package and OS journey; browser frontend is separate | |
| Security, if boundary changed | Dependency/secret checks and trust review | |
| Operations/release | CI source identity, artifact, rollback, owner authorization | |

## Known unverified
<Required: remaining evidence gaps, or none. Static review is not runtime proof.>

## Verdict
**Ready / Not ready / Conditionally ready**

<Justify using IMPLEMENTED, the actual VERIFIED_* classes, ACCEPTED and
BLOCKED/UNVERIFIED. Lower evidence never promotes a higher claim. Record
follow-up work in the existing tracker. Readiness does not authorize publication,
release or production deployment.>
