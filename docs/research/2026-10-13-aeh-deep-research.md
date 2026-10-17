# Deep Research: Tối ưu Agentic Engineering Hub thành framework kỹ nghệ phần mềm cho AI agents

## Kết luận điều hành

Dựa trên inventory bạn cung cấp và đối chiếu với nghiên cứu hiện tại về coding agents, agent harnesses, software engineering, prompting, evaluation, CI/security, accessibility và UX, **AEH đang có nền móng đúng hơn rất nhiều framework “agentic coding” thông thường**. Những nguyên tắc nên giữ nguyên là: Hub chỉ là control/knowledge workspace; project repo mới là source of truth; registry chỉ là index; deterministic tooling tách khỏi judgement của model; verification là explicit; không dựng daemon/scheduler/database/orchestration layer khi chưa có nhu cầu thực; không biến một agent thành “siêu orchestrator” quản lý mọi thứ. Anthropic cũng khuyến nghị bắt đầu từ các pattern đơn giản, composable và chỉ tăng độ phức tạp khi chứng minh được lợi ích đo được; họ phân biệt rõ workflow có đường đi định trước với agent tự quyết định cách dùng tool. citeturn0search29

Vấn đề của AEH hiện nay không phải là thiếu thêm một “agent framework” lớn. Nó thiếu một số **lớp chất lượng** quanh framework hiện có:

| Lỗ hổng | Mức độ | Hướng sửa |
|---|---:|---|
| UI/UX mới được bổ sung nhưng chưa trở thành phần chính thức của delivery model | Rất cao | Đưa UX thành quality dimension có trigger, evidence và CI tương ứng |
| Prompting có `prompt-assist` nhưng chưa có vòng prompt → outcome → eval → corrective | Cao | Biến prompting thành context engineering + evaluation, không phải “viết prompt thật dài” |
| Skills có nhưng governance/evaluation còn nhẹ | Cao | Trigger hẹp, negative trigger, eval fixtures, provenance, stopping rule |
| Agent dễ “pass test nhưng sai project policy” | Rất cao | Chuyển invariants quan trọng thành deterministic gates |
| Runtime evidence, historical evidence và documentation authority chưa tách thật sạch | Trung bình | Tách state tự sinh khỏi tài liệu Git-tracked |
| `hub.py` chủ yếu tối ưu cho người đọc, chưa tối ưu đủ cho agent/tool consumption | Trung bình | Stable structured output, provenance và explicit side-effect model |
| Docs tốt về nội dung nhưng taxonomy chưa rõ | Trung bình | Áp dụng Diátaxis nhẹ, không bùng nổ số file |
| Metrics thiên về token/cost hơn outcome quality | Cao | Thêm first-pass acceptance, rework, retries, escaped defects, UX findings |
| Agent autonomy có thể vượt quá evidence | Cao | Authority boundaries + privileged action policy + explicit release boundary |
| “Vibe coding” dễ trở thành code generation không kiểm soát | Rất cao | Tách prototype mode và engineering mode |

Lý do cần deterministic enforcement đặc biệt quan trọng. Nghiên cứu SWE-CC năm 2026 cho thấy các coding agents hiện đại vẫn vi phạm một phần đáng kể repository policies ngay cả khi tạo ra code có vẻ đúng chức năng; nhiều vi phạm xuất hiện trong các bước trung gian chứ không chỉ ở patch cuối. Một nghiên cứu khác về SWE-bench cho thấy test suite không đủ mạnh có thể khiến patch sai bị đánh dấu là pass. Vì vậy, “agent nói đúng + test xanh” vẫn chưa đủ nếu acceptance, policy, runtime journey và security boundary không được kiểm tra độc lập. citeturn3academia28turn3academia29

Một kết quả thực nghiệm khác cũng đáng lưu ý: nghiên cứu METR trên các developer giàu kinh nghiệm làm việc trong codebase quen thuộc cho thấy ở bối cảnh nghiên cứu đó, công cụ AI đầu năm 2025 khiến thời gian hoàn thành trung bình tăng khoảng 19%, trong khi chính developer lại dự đoán AI sẽ làm họ nhanh hơn. Không nên tổng quát con số đó sang mọi model năm 2026, nhưng nó chứng minh một điều rất phù hợp với AEH: **cảm giác nhanh không phải là productivity evidence**. Framework cần đo accepted outcome, rework và thời gian đến bằng chứng hợp lệ thay vì chỉ đếm code hoặc token. citeturn6search0turn6search2

Định hướng tối ưu phù hợp nhất do đó là:

> **AEH nên trở thành một “engineering operating system” nhỏ, repo-centric, evidence-driven cho coding agents — không trở thành một orchestration platform.**

Kiến trúc mục tiêu nên là:

**Owner intent → project brief → grounded prompt/context → coding agent → deterministic tools → runtime/user-journey evidence → conditional UX/security review → CI → durable handoff/status.**

LLM nên làm những việc cần phán đoán; tool deterministic nên làm những việc máy có thể quyết định chắc chắn; Git và CI giữ trạng thái; Hub chỉ nối chúng lại bằng conventions và evidence. Đây cũng phù hợp với hướng các agent harness hiện đại tập trung vào quản lý context, tools, evaluation và môi trường chạy đáng tin cậy thay vì chỉ viết một system prompt lớn. citeturn11search29turn19search2


## Kiến trúc AEH nên giữ gì và thay đổi gì

Theo inventory bạn cung cấp, AEH hiện đã phân chia khá đúng trách nhiệm. Nên **refactor evolutionary**, không rewrite.

### Bản đồ trách nhiệm mục tiêu

| Thành phần hiện tại | Vai trò nên giữ | Cải tiến đề xuất |
|---|---|---|
| `AGENTS.md` Hub | Bản đồ hoạt động | Ngắn hơn, chỉ invariants/routing/side effects/authority |
| `README.md` | Entry point cho người | Quick start + conceptual map; không lặp AGENTS |
| `REPORT.md` | Historical acceptance evidence | Đánh dấu rõ snapshot theo ngày; không dùng làm current truth |
| `hub.config.json` | Static Hub config | Giữ cực nhỏ, deterministic |
| `projects/registry.json` | Project index | Giữ index-only; schema validate; không chứa task state |
| `docs/*` | Operating knowledge | Phân loại rõ explanation/how-to/reference |
| `templates/*` | Artifact templates | Bổ sung authority, UX và evidence có điều kiện |
| global skills | Reusable workflows | Narrow triggers + negative triggers + eval |
| Hub-local skills | Candidate/incubation | Đây là thiết kế tốt; promotion qua eval |
| `hub.py` | Deterministic project interface | Structured output + stronger provenance; không thêm “AI logic” |
| `legacy_import.py` | Controlled migration | Quarantine/dry-run/provenance/fail-closed |
| `skill_eval.py` | Skill routing/eval | Mở rộng thành regression suite cho skill behavior |
| `evidence/` | Curated proof | Tách khỏi runtime append-only state |
| `ops/worker-isolation/` | Operator boundary | Giữ operator-only; không biến thành agent framework |

**Điều không nên làm:** đưa prompt generation, UX judgement, task prioritization hoặc architectural reasoning vào `hub.py`. Đó là các vấn đề probabilistic/judgement và thuộc skill/agent. Anthropic đặc biệt nhấn mạnh rằng framework agent hiệu quả thường đến từ các primitive đơn giản, rõ ràng và composable; thêm abstraction layer có thể che mất prompt/tool behavior và khiến debugging khó hơn. citeturn0search29

### `AGENTS.md` nên trở thành “constitution”, không phải wiki

Định dạng AGENTS.md được thiết kế như một README có vị trí dự đoán được dành cho coding agents. Điều đó phù hợp với AEH, nhưng giá trị của nó giảm mạnh nếu nó trở thành nơi chứa mọi kiến thức dự án. citeturn0search32turn11search9

Nên có ba tầng rõ ràng:

**Global AGENTS.md** chỉ chứa những invariant xuyên project:

```text
how to establish real state
evidence semantics
common safety boundaries
tool conventions
shared skill discovery
what never counts as proof
when owner approval is mandatory
```

**Hub AGENTS.md** chỉ chứa:

```text
what AEH is / is not
layout
command side-effects
project resolution
skill routing
registry invariants
authority boundaries
```

**Project AGENTS.md** chỉ chứa thông tin project-specific mà agent không thể suy ra an toàn:

```text
product purpose
repo layout
canonical verification entrypoint
architecture invariants
platform boundaries
real user journey
release/deploy restrictions
critical gotchas
project-specific skill triggers
```

Không nên để trong AGENTS:

- progress log;
- backlog;
- lịch sử dài;
- changelog;
- “current task” dễ stale;
- toàn bộ architecture document;
- hàng trăm luật stylistic mà formatter/linter có thể enforce.

Một quy tắc tốt là: **nếu một deterministic tool có thể enforce điều gì, đừng bắt model nhớ điều đó bằng prose**.

Ví dụ, thay vì:

> “Always ensure Python imports are sorted, no trailing whitespace, shell scripts lint clean…”

hãy để verification gọi formatter/linter. SWE-CC cho thấy việc kỳ vọng agent tự tuân thủ hàng loạt repository policy qua instructions là không đáng tin bằng enforcement. citeturn3academia28

### Docs nên được tổ chức theo nhu cầu sử dụng, không theo lịch sử viết

Diátaxis phân chia documentation thành bốn nhu cầu khác nhau: tutorial, how-to, reference và explanation. Khi các loại này trộn vào nhau, docs dễ phình, lặp và khó biết file nào có authority. citeturn14search0turn14search24

Không cần restructure AEH thành hàng chục thư mục. Bộ docs hiện chỉ có sáu file, nên giải pháp nhẹ hơn là thêm `docs/README.md` với classification:

| File | Type | Câu hỏi nó trả lời |
|---|---|---|
| `operating-model.md` | Explanation/reference | AEH vận hành theo nguyên tắc gì? |
| `project-onboarding.md` | How-to | Đưa một repo vào AEH thế nào? |
| `project-delivery.md` | How-to | Agent hoàn thành một thay đổi thế nào? |
| `quality-and-security.md` | Reference/explanation | Evidence và trust boundary được đánh giá thế nào? |
| `cost-and-evaluation.md` | Reference | Đo outcome/cost/rework thế nào? |
| `prompting.md` | How-to/reference | Biến intent thành agent task thế nào? |

Mỗi file nên có metadata nhỏ:

```md
Purpose:
Authority:
Applies to:
Not a source of truth for:
Last reviewed:
```

`REPORT.md` ngày 2026-10-11 là **historical acceptance evidence**, không phải operational reference. Nên có banner rất rõ hoặc chuyển về `evidence/acceptance-2026-10-11.md`; current state luôn phải đến từ `hub.py`, Git và CI. Diátaxis cũng nhấn mạnh reference cần chính xác, đáng tin và tránh nội dung diễn giải không liên quan. citeturn14search6turn14search18

### Registry và project state phải tiếp tục tách nhau

Không nên thêm architecture, task list, “percent complete”, model selection hay session data vào `registry.json`.

Registry tốt nhất chỉ cần:

```json
{
  "slug": "...",
  "path": "...",
  "state": "...",
  "remote": "...",
  "verify": "..."
}
```

Mọi project knowledge còn lại ở project repo.

Điều này đặc biệt quan trọng với OR/VCE: AEH không được trở thành một bản sao thứ hai của `PRODUCT_ROADMAP.md`, issues hoặc Git history.

Một cải tiến đáng cân nhắc cho `hub.py` là **structured output**:

```bash
python3 scripts/hub.py status vce --json
python3 scripts/hub.py report --json
python3 scripts/hub.py doctor --json
```

Human-readable output vẫn là default. JSON giúp agent/tool không phải parse bảng dành cho người. Anthropic lưu ý tool definition và interface là một phần quan trọng của agent effectiveness: tool càng rõ, input/output càng predictable thì model càng ít phải suy đoán. citeturn0search29

Không thêm REST API, database hay Hub daemon chỉ để đạt mục tiêu này.


## Prompting, context và skills cần được nâng từ “hướng dẫn” thành hệ thống có evaluation

Đây là phần AEH còn có nhiều dư địa cải thiện nhất.

### Prompt tốt không phải prompt dài

Nghiên cứu RealSWE trên các yêu cầu phần mềm thực tế cho thấy prompt ngoài đời thường ngắn, informal hơn benchmark; và việc bổ sung **desired behavior** cùng **motivation** có lợi rõ rệt hơn việc nhồi nhiều environment information hoặc reproduction detail không liên quan. Điều này rất phù hợp với việc biến `prompt-assist` thành một **context compiler** thay vì “mega-prompt generator”. citeturn3academia30

Prompt mặc định do AEH sinh ra nên có cấu trúc nhỏ:

```md
Goal / user-visible outcome

Verified context
- repo/path
- branch/HEAD if relevant
- relevant files/symbols
- real commands already verified

Scope
- what to change
- what not to change

Invariants / constraints

Acceptance evidence
- exact observable behavior
- checks that matter
- user journey where applicable

Authority
- actions allowed
- actions requiring owner approval

Stop/report
- when the task is done
- what to report
```

Không phải task nào cũng cần mọi field.

Một typo fix có thể chỉ cần vài câu. Một cross-platform networking bug cần đầy đủ evidence, hypotheses và boundaries.

OpenAI hiện cung cấp evals, graders và prompt optimization như những thành phần riêng trong developer stack, phản ánh một nguyên tắc quan trọng: prompt nên được **đo bằng outcomes**, không được đánh giá chỉ vì “đọc có vẻ chuyên nghiệp”. citeturn19search2turn19search10turn19search18

### `prompt-assist` nên có nhiều mode, chưa cần tạo hàng loạt skill

Thay vì ngay lập tức tạo:

```text
prompt-create
prompt-fix
prompt-debug
prompt-optimize
prompt-review
context-engineer
```

nên giữ **một `prompt-assist` skill**, nhưng có mode rõ:

| Mode | Khi dùng |
|---|---|
| `brief` | Ý tưởng mơ hồ → engineering brief |
| `task` | State thật → prompt implementation |
| `handoff` | Agent A → agent B |
| `corrective` | Agent đã làm sai / không convergence |
| `review` | Kiểm tra prompt hiện có |
| `compress` | Prompt/context quá lớn |

Chỉ tách thành skill mới khi `skill_eval.py` chứng minh routing hoặc quality được cải thiện đáng kể.

### Prompt corrective là mảnh rất quan trọng

Khi một agent đã sai một hoặc hai lần, prompt tiếp theo **không nên chỉ nói “try again”, “think harder”, “fix properly”**.

Corrective context nên là:

```md
Observed:
<kết quả thật>

Expected:
<hành vi đo được>

Evidence:
<command/output/file>

What was already attempted:
<attempt → outcome>

Invariant:
<cái không được phá>

Next requirement:
Diagnose before editing.
State a falsifiable hypothesis.
Run the smallest test that distinguishes likely causes.
Then make the minimal justified change.

Stop if:
<evidence unavailable / requires owner / repeated hypothesis failure>
```

Đây thực chất là evaluator–optimizer loop có bounded retries. Anthropic mô tả evaluator–optimizer là pattern hữu ích khi có tiêu chí đánh giá rõ, nhưng agent loop phải có stopping condition thay vì tự chạy vô hạn. citeturn0search29

AEH đã có tinh thần này trong `verify-debug`; nên **tích hợp**, không duplicate. `prompt-assist corrective` có thể routing người thực thi sang `verify-debug` khi task là test/build failure.

### Context engineering nên ưu tiên pointers hơn paste

Context tốt cho coding agent gồm:

- goal;
- product reason;
- source-of-truth;
- relevant current state;
- files/symbols;
- prior evidence;
- constraints;
- acceptance.

Không nên đưa:

- cả repository;
- cả lịch sử chat;
- toàn bộ docs Hub;
- mọi AGENTS/skill vào prompt;
- hàng nghìn dòng log chưa lọc;
- assumptions không gắn nhãn.

Agent có `rg`, `fd`, Git và read tools thì prompt chỉ cần chỉ đúng **điểm bắt đầu đáng tin**, rồi để agent tự retrieve phần liên quan. Các agent harness hiện đại cũng coi quản lý context và tool access là một phần cốt lõi của reliability. citeturn11search29

Các phân tích về long-context systems cũng chỉ ra context quá tải có thể trở thành nguồn distraction, conflict hoặc “poisoning”; vì vậy “thêm context” không đồng nghĩa “thêm chất lượng”. citeturn20search29

### Skill architecture nên có contract rõ

Skill tốt nên bao gồm:

```md
---
name:
description:
---

Trigger
Negative triggers

Preconditions

Procedure

Deterministic tools used

Evidence required

Stopping / escalation rule

Output contract
```

Không nhất thiết phải dùng đúng các heading đó, nhưng semantic nên hiện diện.

Skills nên **procedure-heavy, prose-light**. Skill là nơi lưu quy trình lặp lại; tài liệu product/architecture ở repo; global AGENTS chứa invariants.

Khái niệm skill của các hệ thống agent hiện đại cũng hướng tới package instructions/resources/scripts được tải khi phù hợp, thay vì nhồi mọi hướng dẫn vào mọi session. citeturn10search10

### Bộ skill đích cho AEH

Sáu global skills hiện tại nhìn chung hợp lý:

| Skill | Giữ? | Cải tiến chính |
|---|---|---|
| `code-investigate` | Có | Evidence-first; search → callers → history → read |
| `project-bootstrap` | Có | Product brief + UX requirement conditional + CI baseline |
| `project-steward` | Có | Outcome prioritization; không tạo parallel plan |
| `verify-debug` | Có | Hypothesis-driven corrective loop |
| `security-review` | Có | Threat boundary + dependency/workflow review |
| `skill-maintainer` | Có | Trigger eval + provenance + negative cases |

Hai candidate mới:

| Skill | Khuyến nghị |
|---|---|
| `ui-ux-review` | Promote thành canonical sau eval |
| `prompt-assist` | Promote sau khi thêm corrective/context/eval behavior |

**Chưa thấy lý do mạnh để thêm skill thứ chín hoặc thứ mười.** Một framework nhỏ với tám skill tốt có lợi hơn hai mươi skill chồng trigger.

### `skill_eval.py` nên trở thành regression harness thật sự

Mỗi skill cần test ít nhất bốn dạng scenario:

| Scenario | Điều cần chứng minh |
|---|---|
| Positive obvious | Skill được chọn |
| Positive subtle | Skill vẫn được chọn |
| Negative neighbor | Skill không chiếm task của skill khác |
| No-skill | Agent xử lý bình thường, không ép skill |

Ngoài routing, nên đo:

- output có required evidence không;
- có invent state không;
- có chạy tool không cần thiết không;
- có vượt authority không;
- task có converge không;
- số retry;
- accepted/not accepted.

Prompt eval nên dùng **representative tasks từ VCE, OR và một repo nhỏ**, không chỉ prompt tổng hợp. OpenAI cũng đặt evals/graders cạnh prompt optimizer thay vì coi prompt optimization là một hoạt động cảm tính. citeturn19search2


## Deterministic tooling, CI, evidence và security nên mạnh hơn model instructions

Nguyên tắc quan trọng nhất cho AEH thế hệ tiếp theo nên là:

> **Model decides what needs judgement; deterministic tools decide what can be mechanically proven.**

### Non-LLM tool stack nên theo tín hiệu, không theo số lượng

Không phải project nào cũng cần mọi tool. `project-bootstrap` nên chọn gate phù hợp với stack.

| Lớp | Tool/pattern điển hình | Mục đích |
|---|---|---|
| Repo state | `git status`, `git diff`, `git log` | Ground truth |
| Search | `rg`, `fd`, `ast-grep` | Targeted discovery |
| Semantic repo navigation | CodeGraph nếu repo có valid index | Caller/path exploration |
| Python | `ruff`, pytest/unittest, type checker nếu project dùng | Static + behavior |
| JS/TS | formatter/linter, typecheck, native test runner | Static + behavior |
| Rust | `cargo fmt --check`, `clippy`, `cargo test` | Static + behavior |
| Shell | `shellcheck` | Script correctness |
| GitHub workflows | `actionlint` | Workflow syntax/static issues |
| Secrets | `gitleaks` | Secret patterns |
| Dependencies | `osv-scanner`, ecosystem audit | Known vulnerable deps |
| Docs | link checker + Markdown lint nếu có giá trị | Broken documentation |
| Web UX | Playwright + axe + selected screenshots | Journey/a11y/visual |
| Supply chain | manifest, checksum, provenance where release risk warrants | Artifact integrity |

Không biến bảng này thành global mandatory checklist.

Một Python CLI 300 dòng không cần Playwright. Một emulator UI không nên được coi là verified chỉ vì `ruff` xanh.

### Verification nên có “test pyramid” theo rủi ro, không theo tool

Một project verification entrypoint tốt nên bao phủ:

**Mechanics → behavior → integration → user journey → release artifact**, nhưng chỉ những lớp có ý nghĩa với project.

Nghiên cứu UTBoost về benchmark patches là lời cảnh báo: test hiện tại có thể pass một implementation sai nếu suite không phủ đúng semantic behavior. citeturn3academia29

Vì vậy AEH nên đặt câu hỏi:

> “Gate này có bắt được loại lỗi mà người dùng thật sẽ thấy không?”

thay vì:

> “Chúng ta có bao nhiêu test?”

### `hub.py` nên được tối ưu có chọn lọc

Chín command hiện tại có boundary khá tốt. Nên giữ.

**Read-only**

```text
list
where
status
report
usage
doctor
```

**Mutate Hub metadata/filesystem**

```text
new
add
```

**Explicitly execute project code**

```text
verify
```

Nên thêm những thuộc tính sau mà không thay đổi triết lý:

**Structured output.** `--json` cho read-only commands.

**Stable error categories.**

```json
{
  "ok": false,
  "kind": "missing_project",
  "message": "..."
}
```

**Verification provenance.** Record nên chứa tối thiểu:

```json
{
  "slug": "...",
  "timestamp": "...",
  "result": "PASS",
  "exit_code": 0,
  "branch": "...",
  "head": "...",
  "dirty": false,
  "dirty_files": 0,
  "verify_sha256": "...",
  "duration_s": 12.4
}
```

Không cần lưu full stdout mãi mãi.

**Freshness** tiếp tục là first-class: PASS trên SHA cũ hoặc dirty tree không được biến thành current PASS.

**Fail closed** nếu registry/schema/path invalid.

**No implicit project execution** trong `status`, `report`, `doctor`.

Đây là một trong những thiết kế tốt nhất AEH hiện tại và không nên phá.

### Runtime evidence nên tách khỏi curated evidence

Hiện `evidence/verification.jsonl` có tính chất runtime append-only, trong khi `RESULTS.md`, `SECURITY.md`, skill evaluation reports là curated evidence.

Nên cân nhắc:

```text
evidence/
    acceptance/
    evaluations/
    security/
    README.md

.hub/
    verification.jsonl
    usage.jsonl
```

`.hub/` là machine/runtime state và ignored khỏi Git, trừ khi project có lý do rõ ràng để commit một snapshot.

`evidence/` chỉ chứa những artifact **được chọn để lưu bền vững**.

Điều này tránh tình trạng một lệnh `verify` bình thường làm Hub repo dirty.

### `legacy_import.py` nên fail-closed

Selective migration là trust-boundary operation.

Tool nên hỗ trợ:

```text
--dry-run
manifest
source path → destination path
size/hash
collision detection
excluded reason
apply only after explicit action
```

Các file như credentials, `.git`, agent hooks/config cũ, unknown executables nên bị quarantine hoặc loại trừ theo policy, không “copy rồi review sau”. Secure-by-design guidance nhấn mạnh việc đưa security controls vào lifecycle và làm chúng thành hành động lặp lại được thay vì dựa vào review cuối cùng. citeturn14search22

### GitHub Actions nên là expensive verification authority

Đối với VCE/OR và các project cross-platform, Debian không nên cố tái tạo mọi platform. GitHub Actions phù hợp hơn cho:

- matrix OS;
- full builds;
- packaging;
- browser matrices;
- expensive tests;
- artifact generation.

Nhưng workflow phải được harden.

GitHub khuyến nghị `GITHUB_TOKEN` theo least privilege, hạn chế privileged workflow contexts, pin third-party actions càng chặt càng tốt, bảo vệ workflow files bằng CODEOWNERS, và thận trọng đặc biệt với self-hosted runners khi chạy code không đáng tin. citeturn21view2

AEH quality/security guidance nên nêu rõ:

```text
permissions: read by default
write only per job
no secrets to untrusted PR code
avoid privileged pull_request_target checkout patterns
workflow changes require review
dependency review where relevant
secret scanning / push protection where available
CodeQL where it buys signal
```

Với môi trường Debian cá nhân của bạn, **không có lý do tốt để biến Dell thành general-purpose GitHub self-hosted runner cho code PR không tin cậy**. GitHub-hosted runners có isolation/lifecycle khác và giảm trust coupling với máy chứa workspace cá nhân. citeturn21view2

Đối với release quan trọng, SLSA định nghĩa provenance như attestation liên kết artifact đã build với build definition/platform tạo ra nó. AEH không cần ép mọi project dùng SLSA, nhưng project có binary releases như VCE có thể dùng checksum, immutable artifact manifest và provenance khi chi phí hợp lý. citeturn17search18turn17search21

### Shared AGENTS/skills writable cần version history

Nếu `agents-worker` được phép sửa canonical AGENTS.md/shared skills, đó là hợp lý cho self-maintaining framework nhưng trở thành **instruction supply chain**.

Do đó:

- canonical rules/skills nên có Git history;
- thay đổi phải rollback được;
- privileged/root services không được execute worker-writable script với privilege cao;
- imported skills phải quarantine/review;
- skill không được tự đọc credentials chỉ vì “có thể hữu ích”.

Prompt injection có thể khiến model thực hiện instruction ngoài ý định ban đầu và có thể dẫn đến disclosure hoặc privilege-related consequences khi agent có tool quyền cao, vì vậy isolation và authority phải nằm bên ngoài prompt. citeturn17search5turn16academia33

Nói cách khác: **AGENTS.md là policy guidance, không phải security boundary.** Điều này nên được ghi rõ trong `quality-and-security.md`.


## Vibe coding nên được biến thành “AI-assisted engineering” có stopping rules

“Vibe coding” hữu ích cho exploration nhanh, nhưng framework của bạn cần phân biệt rất rõ **prototype mode** và **product engineering mode**.

### Prototype mode

Có thể chấp nhận:

```text
intent → rough implementation → inspect result → throw away or promote
```

Điều kiện là artifact chưa được tuyên bố production-ready.

### Product mode

Nên là:

```text
intent
↓
real repository state
↓
brief / acceptance
↓
smallest useful task
↓
targeted investigation
↓
implementation
↓
deterministic checks
↓
runtime behavior
↓
UX/security conditional review
↓
CI
↓
evidence
↓
commit / handoff
```

Anthropic khuyến nghị tăng autonomy chỉ ở nơi task có feedback loop đủ rõ; agent loops tiêu tốn nhiều chi phí hơn và lỗi có thể tích lũy qua nhiều bước. citeturn0search29

### Những failure mode AEH nên explicitly chống

| Agent anti-pattern | Hậu quả | AEH countermeasure |
|---|---|---|
| **Mega-prompt** | Context loãng, constraints cạnh tranh | `prompt-assist` proportional |
| **Read-the-whole-repo** | Tốn context, bỏ lỡ signal | `code-investigate` targeted search |
| **Rewrite reflex** | Phá behavior đang chạy | Existing-repo rule: inspect first |
| **Framework invention** | Agent tự dựng architecture không cần thiết | Prefer existing proven structure |
| **Dependency enthusiasm** | Supply-chain/maintenance cost | New dependency requires reason |
| **Test theater** | Nhiều test nhưng không chứng minh journey | Acceptance tied to behavior |
| **String-grep tests** | Pass vì tên/comment tồn tại | Prefer behavior execution |
| **Retry loop** | Đốt token nhưng không học gì | Two-miss → hypothesis rule |
| **Happy-path UI only** | Loading/error/empty unusable | UX states required |
| **UI slop** | Feature có nhưng người bình thường không dùng được | UX review + visual evidence |
| **Scanner worship** | “gitleaks clean = secure” | Scanner result ≠ security proof |
| **Fake metrics** | “0” khi thật ra unknown | measured/estimated/unavailable |
| **Parallel plans** | Hub/agent/project tracker bất đồng | One durable project authority |
| **Stale progress docs** | Agent hành động từ trạng thái cũ | Git/CI/current commands as truth |
| **Premature completion** | “implemented” thành “done” | implemented/tested/accepted split |
| **Git destructiveness** | Mất WIP | No reset/rewrite without authority |
| **Autonomous release** | Production risk | Owner gate |
| **Over-orchestration** | Agent quản agent thay vì làm sản phẩm | Delegate only where separable |
| **Context archaeology** | Agent đọc hàng nghìn dòng lịch sử | Current summary + pointers |
| **Fix unrelated things** | Review surface bùng nổ | Smallest justified diff |

SWE-CC củng cố rất mạnh điểm “policy không nên chỉ nằm trong prose”: agent vẫn có thể vi phạm repository policy trong khi chức năng chính hoạt động. citeturn3academia28

### Project onboarding nên tạo “minimum engineering surface”

Một project mới không cần 20 file framework.

Minimum tốt là:

```text
README.md
AGENTS.md
source
tests
one verification entrypoint
CI
existing task tracker or small TASKS.md
```

Thêm khi cần:

```text
docs/
ADRs
project-local skills
UX fixtures/screenshots
release scripts
```

Không tạo:

```text
second roadmap
second issue tracker
agent progress journal
orchestration database
prompt archive
dozens of empty docs
```

### Brief cần outcome trước stack

`project-brief.md` hiện đi đúng hướng. Nên chuẩn hóa thành:

```md
Outcome
Primary users
Primary journey
In scope
Non-goals
Constraints
Primary quality risk
Acceptance
UX acceptance (conditional)
Security boundary (conditional)
How real behavior is verified
Owner-only decisions
```

Điều quan trọng là **non-goals**. Agents có xu hướng biến một yêu cầu nhỏ thành refactor/framework upgrade nếu không được ràng giới hạn.

### Handoff không phải conversation dump

Một handoff tốt chỉ cần:

```text
goal
branch + HEAD
verified evidence
files/behavior changed
open failure/blocker
next executable action
authority boundary
```

Không copy 30.000 token reasoning.

Agent tiếp theo phải có thể bắt đầu bằng Git + handoff + AGENTS, không cần đọc toàn bộ conversation cũ.


## UI/UX phải trở thành quality dimension ngang hàng correctness và security

Đây là cải tiến có tác động lớn nhất đối với loại project bạn đang làm.

Hiện tượng bạn mô tả ở VCE và OR — **feature có, code chạy, nhưng giao diện rối đến mức người bình thường khó hoàn thành task** — chính xác là loại failure mà unit test và compiler không phát hiện.

Nielsen Norman Group mô tả các heuristic nền tảng như visibility of system status, match với mental model của người dùng, user control, consistency, error prevention, recognition over recall, efficiency, minimalist design và khả năng recover khỏi lỗi. Những nguyên tắc này đặc biệt thích hợp làm review lens cho AI-generated UI vì chúng kiểm tra usability chứ không chỉ visual polish. citeturn21view0

### UX không nên là “làm cho đẹp”

AEH nên định nghĩa UX quality theo:

```text
Can the intended user discover the action?
Can they understand the current state?
Can they complete the main journey?
Can they recover from mistakes?
Does it work on the relevant screen/input modality?
Can they use it without memorizing hidden state?
Does the UI communicate failure/loading/progress?
Is the accessibility tree usable?
```

Visual beauty chỉ là một phần.

### `ui-ux-review` nên được promote sau pilot

Skill này nên có ba phase.

**Before implementation**

Xác định:

```text
primary user
primary task
platform/device
existing UI conventions
baseline screenshot/flow
critical states
```

**During implementation**

Kiểm tra:

```text
information hierarchy
discoverability
system status
consistent controls
empty state
loading/progress state
error/recovery
success state
responsive layout
keyboard/focus
touch input where applicable
copy/terminology
```

**After implementation**

Evidence:

```text
real journey executed
desktop screenshot
narrow/mobile screenshot if relevant
keyboard path
automated accessibility scan
manual review findings
unverified items
```

### WCAG nên là baseline, không phải toàn bộ UX

WCAG 2.2 là W3C Recommendation với testable success criteria dưới các nhóm Perceivable, Operable, Understandable và Robust; nó bao phủ các vấn đề như keyboard access, focus, contrast, reflow, targets, errors và status messages. citeturn21view3

Nhưng **WCAG pass không có nghĩa UI tốt**.

Một app có thể technically accessible mà vẫn:

- navigation khó hiểu;
- feature không discoverable;
- quá nhiều cards;
- action hierarchy lộn xộn;
- labels dùng internal jargon;
- flow quá dài;
- settings phân bố không hợp lý.

Do đó skill cần kết hợp:

**WCAG/ARIA + Nielsen heuristics + real user journey + platform conventions.**

### Automated UX testing chỉ là một phần

Playwright có thể chạy axe để phát hiện nhiều lỗi accessibility như contrast, unlabeled control hoặc invalid properties. Nhưng chính tài liệu Playwright nói automated accessibility testing chỉ phát hiện được một phần vấn đề và khuyến nghị kết hợp automation, manual assessment và inclusive user testing. citeturn21view1

Vì vậy project UI có thể có CI:

```text
Playwright journey
axe scan
selected screenshot regression
```

nhưng AEH không nên tuyên bố:

```text
axe = 0 violations
=> UX accepted
```

### Screenshot regression nên ít nhưng giá trị cao

Không chụp snapshot mọi component.

Chỉ giữ các journey/screen có giá trị:

```text
landing/home
primary workflow start
main working state
critical modal/settings
success/result
error state
mobile/narrow version
```

Playwright hỗ trợ visual comparisons, nhưng screenshot tests quá rộng sẽ thành brittle maintenance burden. citeturn13view2

### Chống “AI UI slop” bằng constraints, không bằng design system toàn Hub

Không nên tạo một AEH universal component library.

Thay vào đó project AGENTS/UX docs nên nói:

```text
Reuse the project's existing component system.
Reuse existing spacing/type/color tokens.
Prefer native/platform conventions.
Do not invent a new card/modal/navigation pattern without need.
Do not redesign unrelated screens.
Preserve hierarchy and terminology unless the task is explicitly UX redesign.
```

Nielsen’s consistency/minimalism principles hỗ trợ chính xác hướng này: người dùng không nên phải học convention mới không cần thiết, và các yếu tố không liên quan cạnh tranh sự chú ý với nội dung chính. citeturn21view0

### Template cần UX conditional, không compulsory bureaucracy

`project-brief.md`:

```md
## UX — when user-facing UI is in scope

Primary user:
Primary journey:
Relevant devices/input:
Critical states:
Existing visual conventions:
UX acceptance:
Evidence:
```

`review-checklist.md`:

```md
## UX & accessibility — only if UI changed

Primary journey executed:
Responsive/narrow view checked:
Keyboard/focus checked:
Loading/empty/error states checked:
Automated a11y:
Screenshot/visual evidence:
Known UX limitations:
```

`task-handoff.md`:

```md
Visual evidence:
- before:
- after:
- viewport/platform:
```

Không áp dụng các field này cho backend-only changes.


## Blueprint cụ thể để Sol 6.1 Medium tự tối ưu AEH

Sol không nên được giao “rewrite the framework”. Nên giao **refactor in place với compatibility và dogfood**.

### Trạng thái mục tiêu của repository

Cây không cần thay đổi nhiều:

```text
AGENTS.md
README.md
hub.config.json

docs/
    README.md
    operating-model.md
    project-onboarding.md
    project-delivery.md
    quality-and-security.md
    cost-and-evaluation.md
    prompting.md

templates/
    project-brief.md
    project-agents.md
    task-handoff.md
    decision-record.md
    review-checklist.md

skills/
    prompt-assist/
    ui-ux-review/
    <future candidates only>

scripts/
    hub.py
    legacy_import.py
    skill_eval.py

tests/
    ...

evidence/
    README.md
    acceptance/
    evaluations/
    security/

ops/
    worker-isolation/
```

Nếu runtime verification/usage hiện nằm trong Git tree:

```text
.hub/
    verification.jsonl
    ...
```

sẽ là vị trí logic hơn cho machine-generated local state.

### Tối ưu từng tài liệu hiện hữu

**`AGENTS.md`**

Giữ:

- Hub definition;
- registry invariant;
- project-path rule;
- command side effects;
- skill routing;
- authority;
- evidence rules.

Loại:

- explanations dài;
- duplicated command docs;
- historical notes;
- current project state.

**`README.md`**

Nên trả lời đúng bốn câu:

> AEH là gì?  
> Bắt đầu ở đâu?  
> Project ở đâu?  
> Tôi dùng natural language request thế nào?

Không cần trở thành operational specification.

**`REPORT.md`**

Đánh dấu historical hoặc move vào evidence. Không để model nhầm report ngày 11/10 với trạng thái hiện tại.

**`operating-model.md`**

Thêm một ma trận rất quan trọng:

| Loại quyết định | Owner |
|---|---|
| Git state | Git |
| CI result | CI |
| Project behavior | runtime/test evidence |
| Architecture/product intent | project docs/owner |
| Agent workflow | skills |
| Cross-project conventions | AEH |
| Secrets/privilege | OS/operator |
| UI acceptance | evidence + judgement/user |

**`project-onboarding.md`**

Thêm:

- prototype vs production classification;
- UX requirement detection;
- default CI expectation;
- minimum engineering surface;
- no duplicate tracker;
- no imported legacy agent framework by default;
- dependency/release risk questions.

**`project-delivery.md`**

Chuẩn hóa loop thành:

```text
Establish state
→ Define observable completion
→ Investigate
→ Implement minimal change
→ Run smallest relevant check
→ Repair from evidence
→ Run broader gate
→ User journey
→ Conditional UX/security review
→ Report exact evidence
```

**`quality-and-security.md`**

Thêm:

- UI/UX là quality dimension;
- AGENTS/skills không phải security boundary;
- scanner-clean ≠ safe;
- workflow security;
- dependency provenance;
- privilege boundary;
- prompt injection/trusted vs untrusted content.

**`cost-and-evaluation.md`**

Token/cost vẫn hữu ích nhưng nên thêm outcome metrics:

```text
accepted tasks
first-pass acceptance
rework events
verification retries
CI failures caused by agent
escaped defects
policy violations
UX findings reopened
time to verified outcome
```

Không tạo “agent score” tổng hợp giả tạo.

Một model rẻ tạo ba vòng sửa có thể đắt hơn model mạnh giải đúng ngay lần đầu.

METR là lời nhắc hữu ích rằng perceived productivity và measured productivity có thể khác nhau đáng kể. citeturn6search0

**`prompting.md`**

Nên trở thành tài liệu chuẩn về:

```text
outcome first
desired behavior + motivation
context budget
verified facts vs assumptions
authority
acceptance
task proportionality
handoff prompts
corrective prompts
prompt evaluation
anti-patterns
```

Không nên trở thành “100 mẹo prompt engineering”.

### Tối ưu templates

`project-agents.md` nên sinh AGENTS standalone, ngắn, project-specific.

`project-brief.md` thêm conditional UX/security fields.

`task-handoff.md` thêm `unverified` bắt buộc và visual evidence conditional.

`decision-record.md` giữ đơn giản; chỉ dùng cho durable decisions.

`review-checklist.md` nên đổi từ “checklist completion” sang **evidence table + verdict**:

```text
Correctness
User journey
UX if applicable
Security if applicable
Operations/release
Known unverified
Verdict
```

### Tối ưu global skills

Không sửa skill chỉ vì “có thể viết hay hơn”.

Mỗi change cần một reason:

```text
misfire
missing procedure
duplicate knowledge
wrong claim
missing stopping rule
weak evidence requirement
```

`skill-maintainer` nên enforce chính điều đó.

`prompt-assist` và `ui-ux-review` nên được eval rồi promote vào canonical shared library nếu thắng baseline.

### Tối ưu `skill_eval.py`

Nó nên tạo một regression corpus version-controlled, chẳng hạn:

```text
evals/
    prompt-assist.jsonl
    ui-ux-review.jsonl
    project-steward.jsonl
    cross-skill-routing.jsonl
```

Mỗi case:

```json
{
  "input": "...",
  "expected_skill": "ui-ux-review",
  "must_not_select": ["verify-debug"],
  "required_behaviors": ["inspect real UI state"],
  "forbidden_behaviors": ["full redesign"]
}
```

Không cần model benchmark phức tạp. Chỉ cần đủ để phát hiện regressions.

### Tối ưu Hub verification

`hub.py verify` không nên trở thành CI engine.

Nó chỉ cần:

```text
run project-declared gate
bound time/output
kill process group
record identity/result
report truthful freshness
```

Full platform work vẫn thuộc GitHub Actions.

### Dogfood phải là acceptance test của AEH

Sau khi refactor, Sol nên dogfood trên ba loại repo khác nhau:

**`abc-todo` hoặc `acceptance-tool`**  
Chứng minh AEH không overcomplicate project nhỏ.

**VCE**  
Chứng minh cross-platform, release, UI/UX, agent skills và expensive CI hoạt động.

**OR**  
Chứng minh existing complex repo với legacy framework có thể được quản lý mà không import/revive toàn bộ orchestration cũ.

Dogfood không có nghĩa rewrite ba project.

Nó chỉ cần chạy representative scenarios:

```text
status
next task
prompt generation
corrective prompt
UX review
verification
handoff
release-readiness judgement
```

### Acceptance criteria cho bản AEH mới

Sol chỉ nên tuyên bố framework được cải tiến khi có bằng chứng cho các điều sau:

| Acceptance | Bằng chứng |
|---|---|
| Existing Hub behavior không regression | Hub unit tests + doctor |
| Commands cũ vẫn dùng được | CLI compatibility tests |
| Read-only commands không execute project code | Safety regression test |
| Runtime state tách khỏi curated evidence | Clean-tree test |
| AGENTS không duplicate docs | Review |
| Docs có authority rõ | `docs/README.md` + metadata |
| Prompt-assist có task/corrective modes | Eval fixtures |
| Prompt output proportional | Small/medium/complex eval |
| UI/UX review có trigger đúng | Positive/negative skill eval |
| UI review không tự redesign | Pilot evidence |
| Automated UX không bị coi là complete proof | Skill/report language |
| Skill mis-routing được test | Cross-skill eval |
| Legacy import fail-closed | Adversarial fixtures |
| Registry/path handling safe | Unit tests |
| Verification provenance truthful | SHA/dirty/freshness tests |
| GitHub workflow guidance secure | Static review/actionlint where applicable |
| Metrics không bịa số | missing → `UNAVAILABLE` |
| No new daemon/database/router | Tree/process review |
| Framework vẫn nhẹ với project nhỏ | abc-todo/acceptance-tool dogfood |
| Complex repo không bị framework takeover | VCE/OR dogfood |

### Thứ tự triển khai hợp lý

Không nên làm tất cả cùng một giant commit.

**Foundation pass:** baseline, test, docs authority, AGENTS simplification.

**Prompt/skill pass:** prompt-assist corrective/context behavior, skill contract, evaluation suite.

**UX pass:** promote `ui-ux-review`, templates, delivery integration.

**Tooling pass:** structured Hub output, runtime evidence separation, legacy import hardening.

**Security/CI pass:** workflow guidance, dependency/security boundaries.

**Dogfood pass:** project nhỏ → VCE → OR.

Sau mỗi pass:

```text
diff
tests
doctor
skill eval if applicable
review
commit
```

Không cần orchestration loop để làm việc này.

### Tiêu chí cuối cùng cho “AEH tốt”

Một AEH tốt không phải framework có nhiều file nhất hay nhiều agents nhất.

Nó phải làm cho một yêu cầu kiểu:

> “OR đang rất rối UI, cải thiện editor để người bình thường dùng được”

được biến thành một chuỗi đáng tin:

```text
AEH xác định project thật
↓
đọc state thật
↓
steward xác định user outcome
↓
prompt-assist tạo bounded grounded task
↓
coding agent làm diff nhỏ
↓
deterministic gates chạy
↓
ui-ux-review kiểm tra journey + states + accessibility
↓
CI chạy phần nặng
↓
evidence cho biết implemented / tested / accepted / unverified
↓
Git giữ trạng thái
↓
agent dừng
```

Và một yêu cầu nhỏ kiểu:

> “Sửa typo trong abc-todo”

phải chỉ là:

```text
edit → targeted check → commit
```

chứ không gọi security architecture review, UX audit, five-agent workflow và 2.000 dòng prompt.

Đó là **proportionality**.

Toàn bộ nghiên cứu hiện tại đều dẫn về cùng một nguyên tắc: agent hiệu quả hơn khi framework cung cấp đúng context, tool rõ ràng, feedback có thể kiểm chứng và stopping conditions; UX cần cả heuristic/manual judgement lẫn automation; CI/security nên được enforce bằng deterministic controls; và framework nên tăng complexity chỉ khi evidence chứng minh complexity đó mua được chất lượng. citeturn0search29turn3academia28turn21view0turn21view1turn21view2

Vì vậy, mục tiêu cho Sol 6.1 Medium không nên là **“make AEH more agentic”**.

Mục tiêu đúng là:

> **Make AEH better at turning imperfect human intent into small, grounded, verifiable, usable and secure software outcomes — while remaining simpler than the projects it manages.**