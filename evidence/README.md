# Evidence — redacted for publication

The private Hub keeps dated evidence here: incident records, quality-gate
investigations and acceptance receipts, each carrying host paths, session
identifiers and run ids.

This snapshot publishes one file from it: `incidents.jsonl`, the ledger of
failures met while building the Hub, **redacted** — home paths, private
addresses, tunnel names, model-route names and session identifiers are replaced
with placeholders. The lessons are the valuable part and they are process
lessons, not host secrets. The schema is enforced by `tests/test_incidents.py`:
every entry names the failure, its root cause, the evidence and the guard that
keeps it from recurring.

The other evidence — quality-gate investigations and acceptance receipts — stays
private, because it describes the owner's machines, branches and run ids.
