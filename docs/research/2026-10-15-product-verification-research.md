# Deep Research: tái thiết AEH, VCE, OR và H07P thành một hệ phát triển agentic có chất lượng sản phẩm thật

## Chẩn đoán cốt lõi

Hai bản inventory bạn cung cấp cho thấy hệ thống hiện tại **không thiếu engineering discipline**. Ngược lại, cả AEH, VCE, OR và H07P đã có rất nhiều thứ đúng: repository là source of truth, CI authority, trạng thái `UNVERIFIED` thay vì giả PASS, test theo blast radius, skill routing, security boundary, UX contracts, regression guards, packaged journeys và nhiều dạng evidence. Vấn đề là các cơ chế này đã phát triển không đồng đều, khiến **số lượng tooling và tài liệu tăng nhanh hơn khả năng tạo ra một vòng lặp sản phẩm đơn giản, nhất quán và đáng tin cậy**. fileciteturn0file0 fileciteturn0file1

Nói cách khác, tình trạng hiện tại không phải “agents không có đủ tools”, mà gần hơn với:

> **Có quá nhiều cách chứng minh những mảnh nhỏ của sản phẩm, nhưng chưa có một mô hình bằng chứng thống nhất trả lời câu hỏi quan trọng nhất: người dùng thật có hoàn thành được việc, trên bản native thật, với UI đủ rõ ràng và ổn định hay không?**

Điều này giải thích khá tốt hiện tượng bạn đã gặp ở VCE: code có, feature có, unit test có, thậm chí semantic contracts có, nhưng một nền tảng chưa được quan sát trực tiếp vẫn có thể xấu hoặc khó dùng hơn macOS/Android — hai nền tảng đã được thử trực tiếp bằng computer use, thiết bị và emulator.

### Ba kết luận trong audit hiện tại cần sửa lại

**Thứ nhất, `tools/inspect-ui.py` của VCE hữu ích nhưng không nên được mô tả là “accessibility tree mà user agent sẽ dựng”.** Theo chính inventory, nó không chạy JavaScript và không kiểm được layout, màu sắc, spacing, focus ring hay motion. Vì vậy nó là **static rendered-markup semantic inspector**, không phải browser accessibility implementation. Playwright thật sự tạo ARIA snapshot từ accessibility representation của trang đang chạy, gồm hierarchy, role, name, attribute, value và text, và có thể dùng snapshot đó làm assertion. fileciteturn0file1 citeturn12view0turn12view1

Điều này không làm `inspect-ui.py` vô dụng. Nó chỉ cần được đặt đúng tầng bằng chứng:

```text
inspect-ui.py
    ↓
cheap static semantic preflight

Playwright
    ↓
real browser semantics + interaction + layout + trace

native runtime / packaged runtime
    ↓
actual product acceptance
```

**Thứ hai, việc OR chỉ có `Semantics(...)` trực tiếp trong vài file không chứng minh semantics của toàn app “mỏng”.** Flutter nói rõ nhiều standard widgets tự tạo semantics; explicit `Semantics` chủ yếu cần khi custom component hoặc mặc định không đủ. Vì vậy cách đúng là dump/inspect **semantic tree thực tế**, sau đó sửa những node thiếu role/name/action — không phải grep số lần xuất hiện của `Semantics(` rồi bọc mọi widget bằng `Semantics`. citeturn13view0turn13view1

**Thứ ba, xếp H07P “yếu nhất” chỉ vì nó ít custom tooling cũng không hoàn toàn đúng.** Coverage của H07P hiện rõ ràng thiếu, nhưng test Playwright của nó chạy browser thật, kiểm `getByRole`, ARIA state, image decoding, bounding geometry, horizontal overflow và console errors. Về **độ trung thực của một assertion cụ thể**, browser runtime có thể mạnh hơn static parser của VCE; vấn đề của H07P là thiếu coverage, thiếu visual evidence và chưa chạy những flow security quan trọng, không phải thiếu thêm một parser. fileciteturn0file1 Playwright cũng khuyến nghị locators dựa trên thuộc tính hướng người dùng như role và accessible name vì chúng gần với cách người dùng và assistive technology nhận biết trang hơn selector dựa vào cấu trúc DOM. citeturn14view2

### Những pattern đang làm hệ thống phình ra

Từ state snapshot hiện tại, tôi thấy sáu pattern nên chặn trước khi thêm bất kỳ tool nào nữa. fileciteturn0file0 fileciteturn0file1

| Pattern | Hậu quả | Hướng sửa |
|---|---|---|
| Mỗi project tự phát minh vocabulary và evidence framework | Khó so sánh `GOOD`, `PASS`, `accepted`, claim JSON, ledger | Dùng một evidence ladder chung, project được giữ từ vựng local nhưng map vào ladder |
| Tool custom dần trở thành platform riêng | Agent phải hiểu tool trước khi hiểu product | Chỉ giữ custom tool khi nó mang capability product-specific |
| Static evidence bị đặt quá gần runtime acceptance | False confidence | Không cho evidence tầng thấp promote claim tầng cao |
| UX docs rất dài nhưng visual acceptance mỏng | “đúng spec” nhưng vẫn xấu | Canonical screen/state set + screenshot/native observation |
| CI có xu hướng thành monolith | Chậm → agent né CI hoặc sửa đoán mò | Fast preflight + affected CI + full canonical CI |
| Regression knowledge nằm trong prose khổng lồ | Agent phải đọc hàng trăm dòng lịch sử mỗi task | Regression thật → executable guard; prose giữ concise/history archive |

OpenAI hiện khuyến nghị agent tasks có scope rõ, development environment tốt, prompt có cấu trúc gần GitHub issue, và `AGENTS.md` dùng cho context bền vững như convention, business logic hay những quirks khó suy ra từ code; họ không khuyến nghị biến `AGENTS.md` thành một encyclopedia của toàn dự án. citeturn14view1

**Đây nên là nguyên tắc tái thiết chính:**

> **Ít framework hơn, nhiều observation thật hơn. Ít custom abstraction hơn, nhiều native tool hơn. Ít prose evidence hơn, nhiều executable evidence hơn.**

## Kiến trúc kiểm chứng mục tiêu

Tôi đề xuất cả ba sản phẩm dùng **một evidence ladder chung**, trong khi tool cụ thể vẫn do từng platform quyết định.

### Evidence ladder chung

| Tầng | Chứng minh được | Không chứng minh được | Ví dụ |
|---|---|---|---|
| **Source** | Code/config/contract tồn tại | Runtime hoạt động | static inspection, lint, CodeGraph |
| **Semantic** | Control, role, name, state, focus semantics | UI đẹp, flow hoàn tất | ARIA snapshot, Flutter semantics |
| **Behavioral** | Người/test driver thực hiện flow và outcome xảy ra | Visual quality native hoàn chỉnh | Playwright, Flutter integration, WDIO |
| **Visual** | Layout, hierarchy, clipping, spacing, theme, focus indicator | Backend correctness tổng thể | screenshot + computed style + review |
| **Native/Packaged** | Product thật hoạt động trong runtime/package thật | Tất cả hardware/perf trường hợp | packaged app journey |
| **Acceptance** | Critical user outcome trên target được định nghĩa | Nền tảng chưa chạy | CI/device/human acceptance |

Một claim chỉ được promote theo bằng chứng cao nhất thực sự đã chạy:

```text
IMPLEMENTED
    ↓
VERIFIED_SOURCE
    ↓
VERIFIED_SEMANTIC
    ↓
VERIFIED_BEHAVIORAL
    ↓
VERIFIED_VISUAL
    ↓
VERIFIED_NATIVE
    ↓
ACCEPTED
```

Không bắt mọi feature đi qua mọi tầng. Backend-only task có thể dừng ở deterministic tests. Một sửa spacing có thể cần visual nhưng không cần packaged installer. Một sửa Tauri IPC có thể cần native behavioral nhưng không nhất thiết visual. Một fix gameplay performance lại cần runtime/performance evidence chứ screenshot gần như không giúp gì.

Điều quan trọng là **tầng thấp không được giả làm tầng cao**.

### “Semantic-first” cần được định nghĩa lại

Triết lý hiện tại của `ui-ux-review` — semantic-first, deterministic-second, vision-on-demand — vẫn đúng, nhưng cần thêm một mệnh đề:

> **Runtime when the claim is runtime; visual when the claim is visual.**

Tức là:

```text
Structure question?
→ semantics

Can the user finish the task?
→ interaction/runtime

Is the layout visually correct?
→ screenshot/layout measurement

Does it feel correct on native desktop/mobile?
→ native app

Is frame pacing/input latency acceptable?
→ performance instrumentation + target runtime
```

Playwright ARIA snapshots có thể lưu và so sánh accessibility structure; Playwright role locators ưu tiên user-facing accessibility contracts. Trace còn có thể lưu DOM snapshots, screenshots và network information để điều tra failure thay vì agent đoán nguyên nhân. citeturn12view0turn14view2turn14view3

### Accessibility không nên biến thành design system

WCAG 2.2 đưa ra những baseline như target size minimum, dragging alternatives, focus behavior, name/role/value và status messages; chúng là **minimum accessibility requirements**, không phải một công thức tạo UI đẹp. citeturn12view9turn11view7

Do đó AEH nên tách rõ:

```text
Accessibility:
"Can the user perceive and operate it?"

Usability:
"Can the user discover and understand it?"

Visual design:
"Can the user scan and prioritize it without cognitive clutter?"

Product journey:
"Can the user actually achieve the intended outcome?"

Performance:
"Does it respond quickly and consistently enough?"
```

Một trang có thể pass accessibility nhưng vẫn cực kỳ xấu. Một trang đẹp có thể inaccessible. Một trang đẹp và accessible vẫn có thể có flow tệ.

### Visual acceptance set thay cho screenshot mọi thứ

Không nên snapshot toàn bộ UI, vì nó nhanh chóng biến thành một biển golden files. Mỗi sản phẩm nên có một **canonical visual acceptance set** nhỏ.

Ví dụ OR:

```text
Project library — empty
Project library — populated
Editor — media loaded
Editor — timeline selected
Editor — export
Editor — recoverable error
Compact editor
```

VCE:

```text
Library — populated
Game detail
Offline import
Player shell — GBA
Player shell — NDS
Save slots
Settings
Phone controller pairing
```

H07P:

```text
Dashboard desktop
Dashboard 360px
Permissions normal
Permissions review/apply
Files
NAS
Storage
Failure/recovery dialog
Light theme sample
```

Mỗi artifact phải ghi ít nhất:

```text
commit SHA
platform/runtime
window/viewport
theme
journey/state
evidence class
result
limitations
```

Không cần một database hay dashboard mới.

### Desktop cross-platform: consistency không có nghĩa pixel-identical

OR đã đúng khi cấm giả định Metal/Vulkan/D3D12 phải cho output pixel-identical. fileciteturn0file1 Cùng nguyên tắc nên áp dụng UI desktop: **design contract và behavior phải đồng nhất; screenshot baseline nên theo platform**, không lấy macOS golden rồi ép Windows/Linux pixel-match.

“Consistent” nên có nghĩa:

- cùng information hierarchy;
- cùng action priority;
- cùng labels và state model;
- cùng spacing/token contract trong khả năng platform;
- không mất control;
- không overflow/clipping;
- keyboard behavior tương đương;
- platform-native chrome/dialog có thể khác.

### Non-LLM tools nên là xương sống

AEH nên phân công rõ:

```text
CodeGraph / rg / AST tools
        → locate & impact analysis

Compiler / lint / typecheck
        → static correctness

Unit / component tests
        → local behavior

Playwright / Flutter tests / WDIO / Espresso
        → structured runtime interaction

Screenshots / traces / perf traces
        → observation artifacts

CI
        → independent authoritative execution

Vision / human
        → judgement where structured evidence cannot answer
```

CodeGraph không nên trở thành mandatory architecture authority. Vì tên “CodeGraph” có nhiều implementation ngoài thị trường, AEH nên pin **đúng package/version đang cài** và chỉ dựa vào behavior đã xác minh của binary đó. Mọi kết luận dependency quan trọng vẫn phải được đối chiếu với source/code graph thật của repository.

## AEH nên được tối giản thành policy, routing và evidence contract

AEH hiện có một foundation khá tốt: Hub chỉ index project; `hub.py status` không thực thi project; `verify` là explicit execution; global skills có positive/negative trigger; docs phân biệt deterministic/judgement/skill. Những phần này **không nên bị thay bằng một agent orchestrator mới**. fileciteturn0file0

### `AGENTS.md`

AEH `AGENTS.md` nên chỉ trả lời:

```text
What is AEH?
Where are projects?
What is source of truth?
What may this agent modify?
Which skill handles which class of task?
How is verification invoked?
What must never be inferred?
Where are deeper docs?
```

Không nhét:

- toàn bộ UX criteria;
- toàn bộ security threat model;
- history;
- từng command của từng project;
- toàn bộ prompt theory;
- inventory tool versions.

OpenAI khuyến nghị dùng `AGENTS.md` cho persistent context mà agent khó tự suy ra và dùng prompt có file/component/reference cụ thể khi giao task. citeturn14view1

### `ui-ux-review`

Skill này nên trở thành **router + reasoning procedure**, không chứa implementation của từng repo.

Nội dung chính nên khoảng:

```text
Trigger
Negative trigger

Read project UX/testing authority

Classify claim:
semantic / behavioral / visual / native / performance

Choose cheapest adequate evidence

Inspect:
- discoverability
- state
- recovery
- keyboard/touch
- accessibility
- layout
- feedback

Escalate when lower evidence cannot answer

Pin a regression if defect is confirmed

Report:
verified / unverified / blocked
```

Bỏ mọi reference hard-coded kiểu “VCE `tools/inspect-ui.py` là cách chung cho server-rendered web”. Đó chính là dependency ngược mà inventory đã chỉ ra: global skill phải biết VCE để giải thích một generic concept. fileciteturn0file1

Project-specific adapter map phải nằm ở project:

```text
VCE/docs/UI_TESTING.md
OR/docs/TESTING.md
H07P/docs/VALIDATION.md
```

### `prompt-assist`

Skill này đáng giữ, nhưng tôi sẽ mở rộng **corrective mode** thành first-class.

Prompt thực thi bình thường:

```text
Outcome
Grounded context
In scope
Non-goals
Constraints
Acceptance
Authority
Stop condition
```

Corrective prompt:

```text
Observed
Expected
Evidence
Already attempted
What those attempts ruled out
Next discriminating check
Forbidden shortcuts
Acceptance
Stop condition
```

Sau hai lần fix đoán mò, agent không được nhận thêm prompt kiểu:

> “vẫn lỗi, cố sửa đi”.

Nó phải nhận một artifact cho phép phân biệt giả thuyết.

Cách này phù hợp với best practice hiện tại của OpenAI: prompt nên giống issue có scope, paths/components/reference cụ thể; task lớn nên được chia thành scope mà agent có thể hoàn thành và kiểm chứng thay vì một mega-prompt mơ hồ. citeturn14view1

### Docs nên hội tụ thay vì tăng thêm

Tôi sẽ không tạo thêm mười tài liệu.

AEH chỉ cần bổ sung hoặc hội tụ vào:

```text
docs/operating-model.md
docs/project-delivery.md
docs/quality-and-security.md
docs/prompting.md
docs/ui-ux-verification.md       ← mới, nếu thực sự cần
```

`ui-ux-verification.md` mô tả evidence ladder và platform selection. Không chứa project commands.

### Templates

`project-brief.md` đã khá đúng. Chỉ cần UX project yêu cầu:

```text
Primary user
Critical journey
Target platforms
Critical states
Acceptance class required
How it will be observed
```

`review-checklist.md` không nên hỏi chung chung “UX good?”. Nó nên hỏi:

```text
Which journey was exercised?
At what evidence level?
What platforms?
What visual artifact?
What remains unverified?
```

### Không đưa `inspect-ui.py` vào AEH

Đây là một điểm tôi **không đồng ý** với nhận định “VCE là mẫu tốt nhất nên nhân bản inspector”.

Playwright đã có browser-native ARIA snapshot, accessibility-oriented locators, actual interaction và tracing. citeturn12view0turn14view2turn14view3

Copy `inspect-ui.py` lên global layer sẽ tạo:

```text
browser accessibility implementation
          +
AEH's approximation
          +
VCE copy
```

Đó chính là duplication mà Deep Research của bạn đang cố loại bỏ.

Giữ nó trong VCE như cheap static checker nếu signal/cost tốt. Có thể rename để scope rõ hơn, ví dụ:

```text
inspect-rendered-markup.py
```

hoặc giữ tên vì compatibility nhưng sửa description:

> Static server-rendered semantic preflight. Not a browser accessibility tree and not runtime UX acceptance.

## VCE: bỏ duplication ở Web, thêm native desktop evidence thật

VCE hiện có ba tầng khá mạnh nhưng bị trộn vào nhau: static inspector; `an3ctl`; và platform-specific runtime/CI. Đồng thời project có một guard ledger rất lớn và một số build/deploy infrastructure riêng. fileciteturn0file0 fileciteturn0file1

### Web VCE

Target architecture:

```text
Source/rendered markup
    ↓
inspect-ui.py
CHEAP PRECHECK ONLY

Browser UI
    ↓
Playwright
CANONICAL WEB SEMANTICS + INTERACTION

Visual
    ↓
Playwright screenshot + trace

Gameplay canvas
    ↓
VCE-specific runtime instrumentation
```

Playwright ARIA snapshots thực sự biểu diễn accessibility hierarchy của trang đang chạy; role locators gần với perception của user/assistive tech hơn structural selector. citeturn12view0turn14view2

Các browser journeys tối thiểu nên gồm:

| Journey | Evidence |
|---|---|
| Library → Search → Detail → Play | semantic + behavioral + screenshot |
| Empty library → import/recovery | behavioral |
| Offline library → relaunch | behavioral |
| Settings → per-core setting → persistence | behavioral |
| Quick save/load | behavioral + game-state evidence |
| Error state | semantic + recovery |
| 360/390/desktop shell | visual + overflow |
| Keyboard navigation | behavioral |

Không cần screenshot mỗi assertion. Playwright trace có thể giữ diagnostic data cho failure, giúp agent điều tra state/action/network thay vì retry mù. citeturn14view3

### `an3ctl`

Không nên xóa ngay. Nó có những capability VCE-specific thực sự đáng giữ: target abstraction, emulator control, deterministic headless frame capture/hash, status envelope và semantics để tránh screenshot-first automation. fileciteturn0file1

Nhưng **web adapter của nó phải được audit để xem có đang tái triển khai Playwright hay không**.

Target:

```text
an3ctl
├── targets             KEEP
├── emulator adapter    KEEP if unique
├── player runtime      KEEP if unique
└── web adapter
      ↓
   preferably delegate to Playwright
```

Không duy trì một second DOM/accessibility framework chỉ vì nó đã tồn tại.

### VCE Tauri desktop

Đây là khoảng trống quan trọng nhất.

Tauri hiện khuyến nghị WebdriverIO với `@wdio/tauri-service`; service hỗ trợ Windows, Linux và macOS, có thể drive Tauri app, access Tauri API, mock IPC và lấy frontend/backend logs. Embedded WebDriver là đường hỗ trợ macOS; browser-only mode cũng tồn tại cho renderer tests nhanh. citeturn12view2turn12view3

VCE nên có hai lane:

```text
Fast renderer lane
frontend in browser
↓
Playwright or WDIO browser mode

Actual desktop lane
real Tauri binary
↓
@wdio/tauri-service
```

Đừng dùng browser frontend pass để claim desktop app pass.

Các journey native tối thiểu:

```text
launch application
library renders
open game
native↔web IPC succeeds
open settings
save settings
keyboard interaction
window resize
error/recovery
exit/relaunch
```

Sau đó mới tới gameplay-specific acceptance.

### Debian cho VCE

Theo phạm vi mới bạn cho phép, **VCE Web và Linux desktop smoke có thể chạy trực tiếp trên Debian**, miễn là không biến Dell thành build farm.

Nên áp dụng:

```text
one native UI job at a time
bounded timeout
no Android emulator
no VM for VCE
no full cross-platform release build
no parallel Rust/C++ builds unless memory headroom verified
kill process tree after test
clean bounded temporary artifacts
```

systemd trên Linux có resource-control primitives như `MemoryMax`, `TasksMax`, runtime limits và CPU weights; AEH có thể tận dụng resource controls hiện có nếu host policy cho phép thay vì để agent tự spawn không giới hạn. citeturn15search1turn15search2

Tuy nhiên **CI vẫn là authority** cho Windows/macOS/Android/package. Local Linux pass chỉ là developer feedback.

### VCE Android

Espresso có accessibility checks tích hợp; Android UI automation có thể kiểm native UI và những interaction nằm ngoài Web runtime. citeturn14view8

Tôi sẽ không chạy AVD thường xuyên trên Dell.

Mô hình tốt hơn:

```text
Debian
    source + web + Linux desktop fast feedback

GitHub Android runner/emulator
    canonical Android integration

Mac / physical Android
    periodic high-fidelity acceptance only
```

Với performance, UI semantics không giúp đánh giá frame pacing. Android Macrobenchmark/trace là loại tool phù hợp hơn cho performance regressions vì nó cung cấp frame timing và trace thay vì model nhìn video rồi đoán. citeturn14view4

### Gameplay là một domain riêng

Không Accessibility Tree nào chứng minh:

- game render đúng;
- sound không crack;
- save state tương thích;
- NDS touch mapping đúng;
- input latency chấp nhận được;
- emulator chạy đúng tốc độ.

VCE đúng khi đã có `vce-gameplay-performance` và player-specific regression skill. fileciteturn0file1

Điều cần sửa là **không để UI tooling lấn sang gameplay acceptance**.

## OR: giữ widget tests, thêm runtime observation thay vì thêm Semantics bừa bãi

OR hiện có phần UX contract mạnh nhất: `DESIGN.md`, `UX_ACCEPTANCE.md`, widget matrix nhiều viewport, keyboard events, contrast, touch targets, focus ring, packaged journeys và cross-platform CI. fileciteturn0file0 fileciteturn0file1

Vấn đề OR không phải “thiếu unit/widget tests”.

Vấn đề là:

> **Quá nhiều confidence đang nằm ở headless presentation tests, trong khi editor thực sự là sản phẩm tương tác native với custom paint, timeline, media, preview và platform behavior.**

### Không blanket-wrap `Semantics`

Flutter standard widgets thường tự cung cấp semantics; custom component mới là nơi cần explicit semantics khi mặc định không đủ. citeturn13view0

Thay vì:

```text
grep Semantics(
→ thấy ít
→ wrap mọi widget
```

hãy:

```text
render critical state
→ dump actual semantics
→ find missing/ambiguous node
→ determine whether it should be exposed
→ add/fix semantics only there
→ pin regression
```

Một waveform decorative không cần hàng nghìn accessible nodes.

Một timeline clip có thể cần:

```text
role/actionable state
clip name
start/end or duration
selected state
available semantic actions
keyboard equivalent
```

Trim handle nên có một alternative không bắt người dùng phải drag. WCAG 2.2 có riêng tiêu chí về dragging movements và input modalities. citeturn12view9

### Bổ sung runtime integration lane

Flutter chính thức hỗ trợ integration testing trên macOS, Windows và Linux; Linux CI có thể chạy dưới Xvfb. citeturn12view5turn12view6

OR nên giữ widget tests là **component/semantic lane**, rồi thêm một tập integration journey rất nhỏ:

```text
create project
import media
media appears
place/select clip
seek
basic edit
undo
preview
export setup
recover from one known failure
```

Không cần chuyển 110 widget tests sang integration tests.

### Screenshot của OR không cần trở thành golden religion

Flutter integration binding có API screenshot cho integration tests. citeturn14view7

Hãy dùng screenshot cho:

- canonical screen artifacts;
- clipping/layout;
- state hierarchy;
- before/after một UI regression;
- CI failure artifact.

Không dùng screenshot để chứng minh domain correctness.

Không yêu cầu Linux pixel bằng macOS.

### Timeline cần hai lớp test

Timeline editor là nơi “semantic-only” thất bại rõ nhất.

```text
Semantic layer
- selected clip
- action labels
- keyboard alternatives
- focus
- current time/value

Behavioral/render layer
- drag works
- trim changes correct model
- playhead moves
- preview corresponds to state
- undo restores correct state
```

Custom paint không có nghĩa “không test được”; nó có nghĩa test phải chuyển sang **domain outcome + input + screenshot/performance trace**, thay vì cố ép canvas thành DOM.

### Performance OR

Flutter có integration-test profiling APIs để trace actions và inspect timing. citeturn14view6

Đây là nơi nên đo:

```text
scroll media library
drag timeline
seek repeatedly
zoom timeline
scrub preview
open large project
```

Không dùng GitHub hosted timing để tuyên bố device-performance tuyệt đối nếu project đã cấm điều đó; dùng runner để bắt gross regression hoặc trace structure, và giữ hardware-specific claim ở target phù hợp. Điều này phù hợp với chính policy hiện tại của OR. fileciteturn0file1

### Debian cho OR

OR là ứng viên rất tốt cho một **fast Linux UI preflight**:

```text
Flutter widget tests
        ↓
selected integration_test
        ↓
Xvfb
        ↓
small synthetic media fixture
```

Flutter chính thức tài liệu hóa Linux integration testing qua Xvfb. citeturn12view6

Nhưng chỉ:

- một integration run tại một thời điểm;
- fixture nhỏ;
- không long render;
- không Android emulator;
- không release packaging matrix;
- không concurrent OR + VCE heavy native builds;
- run bị kill khi vượt time/resource budget.

macOS/Windows/Android vẫn phải được CI xác nhận.

## H07P: browser UI bằng Playwright, security acceptance bằng disposable VM

H07P là trường hợp khác hẳn VCE/OR vì product của nó **quản lý chính trust boundary của coding agents trên host**. Inventory hiện tại thậm chí đã viết rõ live owner Debian không phải test target, và các test security phải chứng minh denial/enforcement thật chứ không chỉ mock. fileciteturn0file0 fileciteturn0file1

Tôi đồng ý với nguyên tắc cũ này:

> **Không bao giờ test H07P security enforcement bằng cách sửa policy thật của Playground đang dùng hàng ngày.**

### UI của H07P: không cần inspector riêng

Playwright là đủ.

H07P nên mở rộng E2E thành các file/flow nhỏ hơn thay vì một giant test:

```text
dashboard.spec
navigation.spec
responsive.spec
keyboard.spec
permissions.spec
files.spec
nas.spec
storage.spec
apps.spec
```

Không nhất thiết tám file đúng như trên; mục tiêu là failure localization.

Thêm:

- ARIA snapshot cho critical regions;
- keyboard-only navigation;
- dialog entry/exit focus;
- Escape;
- `aria-live`;
- async loading/error/recovery;
- screenshot desktop + 360px;
- light + dark sample;
- trace on failure;
- all critical routes;
- Rust backend version của journey khi endpoint tương ứng đã migrate.

Playwright cung cấp ARIA snapshots để kiểm structure và trace để phân tích step/screenshot/DOM/network khi failure xảy ra. citeturn12view0turn14view3

### Không copy VCE `inspect-ui.py`

Điều đó chỉ tạo một static approximation trong project vốn đã có real browser.

H07P cần **nhiều browser behavior hơn**, không cần một browser giả khác.

### H07P security cần kernel/OS boundary thật

Đây là nơi container đơn thuần không đủ làm authority vì sản phẩm cần kiểm:

- Unix DAC;
- process identity;
- systemd behavior;
- namespaces;
- descriptors;
- symlinks/hardlinks;
- process descendants;
- package install/uninstall;
- revoke/restart behavior;
- privilege boundaries.

Inventory của H07P đã tự nhận biết vấn đề này. fileciteturn0file1

### Giải pháp local nhanh: disposable QEMU/KVM lab

Thay vì test trên live Debian:

```text
Dell host
│
├── real H07P / DSH / agent-workbench
│      NEVER TOUCHED BY ACCEPTANCE
│
└── disposable VM
       synthetic owner
       synthetic worker
       synthetic secrets
       synthetic services
       synthetic policy
```

QEMU qcow2 hỗ trợ backing files/copy-on-write; snapshot mode có thể coi disk images là read-only và ghi thay đổi tạm thời, rồi discard khi VM thoát. citeturn11view0turn12view8

Đây là mô hình phù hợp hơn container cho H07P vì guest có kernel/system users/systemd riêng.

Tôi đề xuất **hai lớp H07P acceptance**:

```text
Fast local VM preflight
        ↓
trusted developer branch only
fast failure feedback
disposable
no real credentials

GitHub-hosted canonical CI
        ↓
independent clean environment
PR / accepted commit
authoritative evidence
```

GitHub nói GitHub-hosted runners chạy trong VM sạch, ephemeral; self-hosted runner thì không có bảo đảm đó và có thể bị untrusted workflow compromise lâu dài. GitHub đặc biệt cảnh báo self-hosted runners gần như không nên dùng cho public repositories. citeturn12view7

Vì vậy **không đặt một GitHub self-hosted runner trực tiếp trên Dell host**.

Nếu sau này thật sự muốn Actions syntax chạy local, an toàn hơn là JIT runner **bên trong VM disposable**, chỉ cho trusted/manual workload. Nhưng tôi chưa khuyên làm bước này ngay; một `run-acceptance-vm` script đơn giản ít moving parts hơn.

### Isolation của VM

Guest H07P test không nên có:

```text
<home> mount
/srv/agent-workbench mount
SSH agent socket
real ~/.ssh
real provider credentials
real DSH cookies
real API keys
real NAS
access to real Playground management ports
```

Fixtures nên cố tình giả:

```text
/srv/test-owner/private/fake-secret.txt
/srv/test-worker/
synthetic NAS tree
dummy API token pattern
fake services
```

VM test denial đối với **fake valuable data**, chứ không đặt real valuable data vào vùng blast radius.

### RAM/SSD

Đây là chỗ có thể giải quyết nỗi lo “emulator đốt RAM/SSD”.

Tôi sẽ không pin cố định một cấu hình vì chưa biết RAM thật còn trống bao nhiêu. Lab launcher nên:

1. đo available memory;
2. từ chối launch nếu headroom dưới ngưỡng project định nghĩa;
3. chỉ một guest;
4. dùng qcow2 backing image read-only + disposable overlay;
5. giới hạn guest CPU/RAM;
6. auto-delete overlay sau pass/fail;
7. giữ log/artifact nhỏ;
8. không chạy đồng thời VCE/OR native-heavy job.

Qcow2 copy-on-write chia sẻ phần lớn backing data, nên phù hợp với mô hình base image + throwaway delta thay vì clone một full disk mỗi run. citeturn11view0

### CI của H07P có thể nhanh hơn mà vẫn giữ independence

Không cần chọn giữa:

```text
slow public CI
OR
dangerous host testing
```

Có thể dùng:

```text
edit
 ↓
cheap local source tests

security-related?
 ↓
disposable VM preflight

push
 ↓
affected GitHub jobs

merge/release candidate
 ↓
full canonical CI
```

GitHub Actions hỗ trợ dependency caching; cache repository có giới hạn mặc định và eviction behavior riêng, vì vậy cache nên được thiết kế cho dependency/toolchain có reuse tốt, không cache build garbage không giới hạn. citeturn9search0turn9search2

Các artifact Playwright trace/screenshots có thể upload **on failure** hoặc cho canonical acceptance states thay vì mọi step, giảm storage và noise.

## Lộ trình tái cấu trúc và prompt giao cho AEH

### Kiến trúc cuối cùng tôi khuyên dùng

```text
                         AEH
       policy + skill routing + evidence model
                          │
        ┌─────────────────┼──────────────────┐
        │                 │                  │
       VCE               OR                H07P
        │                 │                  │
 repo-specific       repo-specific       repo-specific
 adapters/tests      adapters/tests      adapters/tests
        │                 │                  │
 Playwright          Flutter tests       Playwright
 Tauri WDIO          integration_test    disposable VM
 Android             screenshots         OS acceptance
 an3 emulator         perf traces
        │                 │                  │
        └─────────────────┼──────────────────┘
                          │
                    GitHub Actions
                 canonical acceptance
```

AEH **không sở hữu** Playwright wrappers của VCE, Flutter helpers của OR hay QEMU harness của H07P. Nó chỉ sở hữu nguyên tắc chọn đúng layer.

### Thứ tự triển khai

Ưu tiên tôi đề xuất là:

**AEH trước**, vì nếu routing/evidence model sai thì ba project tiếp tục divergent. Nhưng chỉ sửa policy/docs/skill nhỏ, không redesign Hub.

**H07P Web sau đó**, vì closing screenshot/360/focus/aria-live/route gaps bằng Playwright là signal cao, chi phí thấp.

**OR runtime lane**, vì widget infrastructure đã rất mạnh; giá trị tăng thêm lớn nhất đến từ real Linux integration observation.

**VCE native desktop**, vì đây là khoảng trống khó hơn nhưng giá trị cao: Tauri app thật cần được kiểm chứng thay vì frontend browser đại diện.

**H07P disposable security lab** cuối cùng vì nó đòi thiết kế isolation cẩn thận; không được “tiện tay” chạy ngay trên live host.

### Prompt dành cho AEH / Sol 6.1 Medium

Prompt dưới đây cố tình không yêu cầu agent copy y nguyên báo cáo này. Nó yêu cầu agent **inspect actual state trước**, dùng research như architectural direction chứ không như giả định bất biến. Cấu trúc outcome/context/scope/constraints/acceptance/stop cũng phù hợp với cách OpenAI hiện khuyến nghị prompt engineering task giống một issue có grounded references và scope rõ ràng. citeturn14view1

```text
You are the project steward for the existing Agentic Engineering Hub (AEH).

Workspaces:

AEH:
  <hub-root> (the former path)

Products:
  <workspace-root>/VCE
  <workspace-root>/OR
  <workspace-root>/huou07-playground (retired)

This is a framework simplification and product-verification improvement mission.

Do the work. Do not produce another audit-only report.

## Outcome

Reorganize AEH and the three product repositories so coding agents have a small,
consistent and evidence-based way to build and evaluate real product quality,
especially UI/UX, without creating another orchestration framework.

The target philosophy is:

  semantic when the question is semantic
  runtime when the claim is runtime
  visual when the claim is visual
  native when the claim is native
  CI for authoritative acceptance
  vision/human judgement only where structured evidence cannot answer

Preserve what already works.

Reduce duplicated/custom infrastructure where maintained platform-native tooling
provides the same capability more faithfully.

## Start from actual state

Before editing anything:

- Read each repository's AGENTS.md and current authoritative documentation.
- Inspect Git branch, HEAD, remotes, worktrees and all staged/unstaged/untracked work.
- Preserve all existing unrelated and unfinished work.
- Inspect the real installed versions of CodeGraph CLI, Playwright CLI, Flutter,
  Tauri, WebdriverIO-related dependencies and other relevant tooling.
- Inspect current CI rather than assuming this prompt describes it perfectly.
- Identify which current evidence is static, semantic, behavioral, visual,
  native/packaged or true acceptance.
- Treat historical reports and old framework scaffolding as evidence, not as
  architecture that must be preserved forever.

Do not reset, clean, squash, rewrite history or discard WIP.

## Shared verification model

Introduce one small conceptual evidence ladder that all projects can map to:

  IMPLEMENTED
  VERIFIED_SOURCE
  VERIFIED_SEMANTIC
  VERIFIED_BEHAVIORAL
  VERIFIED_VISUAL
  VERIFIED_NATIVE
  ACCEPTED
  BLOCKED / UNVERIFIED where applicable

Do not force repositories to rewrite all historical terminology.

Instead, document the mapping once and make new work clear about the evidence
level actually achieved.

A lower evidence level must never promote a higher-level claim.

Examples:

- source inspection cannot claim runtime behavior;
- semantics cannot claim visual quality;
- a screenshot cannot claim a journey works;
- a browser frontend pass cannot claim a packaged desktop app works;
- a mocked permission test cannot claim OS isolation;
- CI configuration existing in source does not mean CI passed.

Keep this model lightweight. Do not create a database or evidence service.

## AEH

Keep AEH as a control + knowledge workspace, not a source-code host or
orchestrator.

Preserve:

- repository as project source of truth;
- registry as index;
- explicit side effects in hub.py;
- deterministic verification;
- narrow skill triggers;
- GitHub Actions as canonical remote verification;
- honest UNVERIFIED/BLOCKED states;
- existing security boundaries.

Review and simplify AGENTS.md so it remains a navigation/operating map rather
than an encyclopedia.

Refactor the shared `ui-ux-review` guidance so it is a platform-independent
decision procedure and evidence contract.

It should:

1. Read the project's own UX/testing authority.
2. Identify the claim being evaluated:
   semantic, behavioral, visual, native or performance.
3. Select the cheapest tool capable of answering that claim.
4. Escalate when the current evidence class cannot answer it.
5. Require real user-journey outcome and recovery where applicable.
6. Require visual evidence for visual claims.
7. Require native/package evidence for native/package claims.
8. Pin a deterministic regression guard after a confirmed defect.
9. Report limitations explicitly.

Do not hard-code VCE-specific tool paths into the global skill.

Do not copy project-specific browser or UI inspectors into the canonical shared
skill library.

Update `docs/prompting.md` and `prompt-assist` only where necessary so
corrective prompting has a clear structure:

  Observed
  Expected
  Evidence
  Already attempted
  What those attempts ruled out
  Next discriminating check
  Forbidden shortcuts
  Acceptance
  Stop condition

After repeated failed guesses, agents must investigate rather than receive a
larger "try harder" prompt.

Keep project prompts grounded, proportional and similar to a good engineering
issue: outcome, relevant paths/components, constraints, evidence and completion
criteria.

Avoid mega-prompts and duplicated context.

## VCE

Do not treat `tools/inspect-ui.py` as a full browser accessibility tree.

Evaluate it as a cheap static rendered-markup semantic preflight.

If retained:
- state its limitations prominently;
- preserve compatibility where reasonable;
- do not let its PASS imply runtime accessibility or visual acceptance.

Use Playwright as the canonical Web runtime inspection layer for:
- actual browser semantics;
- user-facing locators;
- interaction;
- responsive geometry;
- keyboard/focus behavior;
- screenshots when needed;
- traces for failure investigation.

Audit `tools/an3ctl/`.

Keep VCE-specific capabilities that provide unique value, especially target
control, emulator/runtime evidence and deterministic capture.

Where its Web adapter duplicates Playwright, simplify or delegate rather than
maintaining a second browser automation framework.

Do not remove working VCE-specific capabilities merely for architectural
neatness; prove replacement parity first.

Evaluate the current official Tauri/WebDriverIO route for testing the actual
desktop application.

Create only a small representative native desktop journey initially.

The important distinction is:

  browser frontend verification != actual Tauri desktop verification.

For VCE Android, reuse Android-native accessibility/instrumentation mechanisms
where practical rather than attempting to make Playwright inspect a native app.

Keep gameplay acceptance separate from UI semantic acceptance.

A game canvas, audio, input mapping, save-state behavior or performance claim
requires appropriate runtime evidence.

### Debian permission for VCE

The owner now permits bounded VCE Web/Linux-native tests on the real Debian
development machine.

However:

- no Android emulator/AVD;
- no VM for ordinary VCE testing;
- no heavy cross-platform release builds;
- no uncontrolled parallel native compilation;
- no long-running GPU/emulator workload;
- one resource-intensive UI/native check at a time;
- use bounded timeouts and existing resource controls;
- inspect available memory before running heavier work;
- stop rather than create RAM/swap pressure.

GitHub Actions remains authoritative for cross-platform/native acceptance.

## OR

Preserve the existing domain ownership, command architecture, DESIGN.md,
UX acceptance rules, widget test suite and packaged CI journeys.

Do NOT add `Semantics(...)` wrappers everywhere based on grep counts.

Standard Flutter controls may already contribute semantics.

Instead:

- inspect the actual semantics tree of critical screens;
- identify missing/ambiguous roles, labels, states or actions;
- add explicit semantics only where the real tree needs it;
- pay special attention to custom controls and custom-painted UI.

Keep widget tests as the fast semantic/component layer.

Add or improve a small actual Flutter integration-test lane for critical editor
journeys where the current repository state supports it.

Prioritize:
- create/open project;
- import media;
- timeline selection/basic edit;
- keyboard equivalent where applicable;
- seek/preview;
- undo;
- export setup;
- one recovery/error path.

Use runtime screenshots only for critical visual states and CI evidence.
Do not create a massive pixel-golden suite.
Do not require cross-platform pixel identity.

Use platform-specific visual evidence where native rendering differs.

For timeline/waveform/preview:
- semantic exposure should describe meaningful interactive objects and actions;
- decorative pixels do not need semantic nodes;
- behavioral tests must verify the resulting project state;
- visual/runtime evidence handles rendering;
- performance traces handle jank/performance claims.

### Debian permission for OR

The owner permits bounded Linux-native OR testing on Debian.

A small Flutter Linux integration test under an appropriate headless X
environment is allowed if the required tooling already exists or can be added
proportionally.

Keep:
- concurrency low;
- fixtures small;
- execution bounded;
- no Android emulator;
- no full cross-platform packaging;
- no long media renders;
- no concurrent OR/VCE heavy jobs.

CI remains canonical for macOS, Windows, Android and packaged acceptance.

## H07P Web UI

Do not copy VCE's static inspector into H07P.

Use Playwright as the primary browser authority.

Close the currently evidenced gaps progressively:

- required 360px coverage rather than silently substituting another viewport;
- desktop visual evidence;
- dialog focus entry/restore;
- Escape behavior;
- aria-live/status feedback;
- keyboard-only navigation;
- light/dark representative visual states;
- loading/empty/partial/error/recovery states;
- critical Permissions/NAS/Storage journeys as those surfaces exist;
- console/page errors;
- trace artifacts for failures.

Use ARIA/role assertions for semantic questions and screenshots/layout
measurement for visual questions.

Do not turn every page into a brittle screenshot golden.

As the Rust migration advances, make browser acceptance exercise the actual
Rust backend for migrated slices.

A Python-only acceptance pass must not claim Rust runtime parity.

## H07P security acceptance

The live owner Debian Playground and its real permission state are NOT a
security-test fixture.

Do not mutate real agent permissions, owner credentials, live DSH state, real
NAS data or production-like policy merely to run acceptance.

Design a disposable local security lab using a real isolated guest OS when
local fast feedback is valuable.

Preferred model:

  immutable/read-only base image
       +
  disposable qcow2 overlay/snapshot
       +
  synthetic owner
       +
  synthetic worker
       +
  synthetic private files/secrets/services
       +
  destroy after run

The lab must not mount or expose:

- <home>;
- /srv/agent-workbench;
- real SSH private keys;
- SSH agent sockets;
- provider/API credentials;
- live DSH auth state;
- real NAS;
- live Playground control endpoints.

Give the guest only the resources it needs.

Before creating or launching a VM:
- inspect available RAM/CPU/storage;
- define a conservative hard resource budget;
- allow only one guest at a time;
- refuse to start when safe memory headroom is unavailable;
- keep the base image reusable and guest changes disposable.

If setting up this lab requires privileged host changes outside the agent's
authority, prepare the exact reviewed operator steps instead of bypassing the
boundary.

Containers may remain useful for cheap unit/integration work, but do not use a
container-only result as proof of the OS isolation properties H07P claims.

Do NOT configure the live Dell host itself as a general GitHub self-hosted
runner.

GitHub-hosted CI remains the independent canonical acceptance lane.

A future ephemeral/JIT runner inside the disposable guest may be evaluated
separately, but do not add that complexity unless it buys measurable value.

## CI strategy

For each product, converge toward:

  fast local affected checks
      ↓
  bounded local runtime preflight where safe
      ↓
  targeted PR CI
      ↓
  canonical platform/native jobs
      ↓
  full release/acceptance gates only when relevant

Do not weaken existing required release safeguards.

Avoid running every expensive matrix for every trivial documentation change if
the current repository architecture safely supports affected-path selection.

Cache dependencies/toolchains where they provide real reuse, but avoid
unbounded generated build caches.

Upload rich UI artifacts primarily for:
- failure diagnosis;
- canonical acceptance states;
- release/acceptance evidence.

## Tool policy

Prefer:

- repository source;
- Git;
- CodeGraph/rg/AST tooling for investigation;
- compiler/lint/typecheck;
- project test runners;
- Playwright for Web;
- official Tauri/WebDriver mechanisms for actual Tauri UI;
- Flutter semantics/widget/integration tooling for OR;
- Android-native testing tools for Android;
- QEMU/KVM only for the H07P disposable OS-security lab;
- GitHub Actions for independent canonical verification.

Use CodeGraph as an investigation aid, not as architecture authority.
Verify important findings against source.

Prefer CLI and deterministic machine-readable outputs over persistent MCP
services when both can solve the same task.

Do not add a framework merely because a tool exists.

## Documentation and regression policy

The repository remains source of truth.

Do not create parallel roadmaps, trackers or giant duplicate policy documents.

Whenever a confirmed regression can be encoded as an executable guard, prefer
the executable guard over expanding prose indefinitely.

Preserve historical regression ledgers and evidence, but archive or clearly
demote stale historical material rather than forcing every future agent to
load it.

AGENTS.md should point to authority; it should not duplicate authority.

## Work discipline

Preserve all uncommitted work.

Before editing each repository, record:
- branch;
- HEAD;
- dirty state;
- relevant current CI;
- actual existing tools.

Make changes in small logical batches.

Run the cheapest relevant check first.

After two speculative failed repair attempts on the same failure:
STOP guessing.

Write:
  Observed
  Expected
  Evidence
  Attempts
  Hypotheses
  Discriminating next check

Then investigate.

Never weaken tests, scanners, assertions or security boundaries to obtain a
green result.

Do not deploy production, publish a release, merge protected branches, change
real H07P permissions or rewrite Git history.

## Acceptance

The mission is complete only when evidence demonstrates all of the following:

AEH:
- global UI/UX guidance is platform-independent;
- evidence levels are clear;
- prompt corrective workflow is clear;
- project-specific tools no longer leak into global policy unnecessarily.

VCE:
- static semantic inspection is correctly scoped;
- real Web runtime inspection has a clear canonical path;
- duplicated Web automation is reduced or explicitly justified;
- an actual Tauri/native verification path is implemented or concretely
  proven blocked;
- gameplay/runtime evidence remains distinct from UI semantics.

OR:
- semantics coverage is assessed from the actual tree, not grep counts;
- custom controls have appropriate semantics where needed;
- at least one representative native/Linux integration journey is verified
  where feasible;
- visual evidence and behavior evidence are distinguished;
- existing cross-platform/package gates remain intact.

H07P:
- browser UX coverage closes the highest-value current gaps;
- Web tests use the appropriate runtime authority;
- no security acceptance touches the live permission environment;
- a disposable real-OS test design/harness exists for permission-boundary
  testing, or a precise evidence-supported blocker is documented;
- GitHub-hosted CI remains the independent authority.

All projects:
- no false PASS;
- limitations are explicit;
- relevant local verification is fresh;
- remote CI is used where the claim requires it;
- no uncontrolled RAM/storage growth is introduced;
- framework complexity is lower or clearly justified by additional evidence.

## Commits and handoff

Use logical commits in the appropriate repositories.

Push only to appropriate existing development/feature branches when normal
repository policy permits it.

Do not merge or release.

At completion, report only:

- architectural simplifications made;
- files/framework components changed;
- tools retained, replaced, delegated or rejected and why;
- actual UI/runtime/security evidence achieved per project;
- local resource usage constraints introduced;
- CI status;
- commits/branches;
- remaining UNVERIFIED/BLOCKED items;
- any owner-only action required.

Do not claim success from documentation changes alone.

The mission succeeds when the framework becomes smaller and the products
become easier to observe and verify in their real runtime — not when AEH gains
more files.
```

### Trạng thái đích nên trông như thế nào

Sau mission này, một agent sửa OR timeline không cần đọc VCE `an3ctl`; agent sửa VCE Web không cần hiểu Flutter semantics; agent sửa H07P Permissions không được đụng live ACL để “test”; và global `ui-ux-review` không cần biết tên bất kỳ file project nào. Project-specific infrastructure vẫn nằm trong repository sở hữu nó. fileciteturn0file0

Một agent sửa UI sẽ đi theo đường ngắn có thể chứng minh claim:

```text
"What changed?"
        ↓
"What kind of claim am I making?"
        ↓
semantic / behavioral / visual / native / performance
        ↓
cheapest adequate tool
        ↓
real observation
        ↓
regression guard
        ↓
CI when required
```

VCE sẽ không còn coi static HTML inspection là browser acceptance; OR sẽ không còn dùng số lượng explicit `Semantics` như proxy cho accessibility coverage; H07P sẽ không cần hy sinh security boundary để có feedback nhanh; và AEH sẽ không trở thành “framework để quản lý những framework”. Các native ecosystem hiện đã có đường kiểm thử phù hợp: Playwright cho web accessibility/runtime, WebdriverIO/Tauri cho desktop Tauri, Flutter integration tests cho desktop/mobile, Espresso cho Android accessibility, và QEMU qcow2/snapshot cho guest OS disposable. citeturn12view0turn12view2turn12view5turn14view8turn12view8

Kết luận quan trọng nhất là **đừng tối ưu cho việc agent “biết nhiều hơn”; hãy tối ưu cho việc agent “có thể quan sát đúng thứ nó sắp tuyên bố”**. Đây là khác biệt giữa một vibe-coded codebase có hàng trăm guard nhưng vẫn phải sửa UI nhiều lần, và một engineering system có vòng phản hồi ngắn, bằng chứng đúng tầng, native acceptance rõ ràng và đủ ít abstraction để agent không tự lạc trong chính framework của mình.