# AREPO v2 implementation decisions

2026-09-20, Phase 0. These are engineering/scientific-contract decisions, not claims of validated model performance.

| ID | Decision | Basis / consequence |
|---|---|---|
| D000 | Use existing repository and fetched production e50f063 as base | Matches research audit; local production behind, not divergent. Lean branch not imported. |
| D001 | Preserve all 13 supplied research artefacts unchanged with SHA-256 manifest | Durable memory; Desktop reads stalled, original ChatGPT research-output curated copies available. Attached documents supply evidence, user's programme supplies operational authority. |
| D002 | Canonical prose + concrete field catalogue + exhaustive 140-field reconciliation | Original dictionary omits whole logical entities and uses generic types; cannot serve as DDL alone. |
| D003 | Separate FeatureStoreBase and fs2 migration ledger | v1 auto-migrates during build/startup/scheduler and check may create a ledger table. Isolation prevents accidental activation. |
| D004 | Exact decimal text on both SQL dialects; raw strings separately | SQLite Numeric affinity risks binary conversion; typed adapters/explicit analytical casts preserve precision. Derived float64 encoded explicitly, never substituted for raw source values. |
| D005 | Append-only scientific records with database and repository guards | Corrections/reorgs/late labels retain previous evidence; observed interval end derived at cutoff. |
| D006 | Split market/condition/asset/outcome and economic-event mapping | Condition != Gamma event != independent economic cause. Unknowns remain unresolved; later grouping only for conservative evaluation. |
| D007 | Add legacy_unverified provenance and retain source provenance in legacy_reference | v1 recorded clocks do not establish v2 first receipt or availability. No retrospective prospective relabelling. |
| D008 | Preservation contract precedes any retention proposal | v1 archive checks count/hash only and microstructure pruning lacks archive equivalence. No retention action authorised. |
| D009 | Phase 3 is measurement/development pilot; Phase 4 locks comparative baseline protocol | Avoid claiming a prospective confirmatory trial started before model/target/sampling decisions were locked. |
| D010 | Later phases are evidence-gated; no automatic 'complete' on code-only output | Source availability, clean independent events and confirmation outcomes cannot be replaced by fixture tests. |
| D011 | Single 305-minute same-task continuation | Active automation continue-arepo-v2-implementation, no duplicate chain; preserve checkpoint before stopping. |

Future architecture changes append here with reason, affected contracts and migration/test consequences. Do not silently alter a frozen scientific definition; create a new version and retain prior trial evidence.

## Phase 1 refinements

- D012: preserve dictionary-compatible column declarations explicitly and test them against the canonical CSV; no runtime reads from docs or v1 metadata imports.
- D013: install PostgreSQL locally only for a disposable isolated test cluster; no system service or production connection. Record actual integration evidence before phase acceptance.
- D014: keep public prospective writes closed in Phase 1. A timestamp taken before a transaction commits is not proof of durable model availability. Phase 2 must establish a durable receipt/clock boundary before opening a prospective ingestion path; no caller-supplied flag may waive it. Structural chronology is exercised with explicit synthetic fixtures now.
- D015: manifests use schema `fs2-manifest-v1`, entity-qualified roots and exact transitive closure. Book levels are constituents of a book and must be included in preservation closure; their parent FK is composition, not a scientific revision cycle. Nonempty training manifests declare an as-of cutoff and admit only mature labels available by that cutoff.
- D016: schema installation fingerprints actual columns, constraints, indexes, trigger definitions, RLS/policies and grants, including the migration ledger. A mismatch causes refusal, never an automatic repair. Database owners can defeat these controls; production privilege review remains separate.
- D017: scalar natural keys receive SQL unique constraints; nullable/JSON-list key semantics additionally require the validated deterministic non-null SHA primary key. The isolated writer checks payload identity and retries concurrent identical submissions without changing stored clocks.
- D018: local preservation codec roundtrips exact decimal tuples, timestamps, raw strings, nulls, units and keys; its verification state is `local_codec_only`. It is not the complete archive-equivalence gate and authorises no deletion or retention change.
- D019: JSON integers outside JavaScript's exact integer range require string encodings. Exact probability-sum validation retains small components rather than rounding them away; exponent spans exceeding 10,000 digits are rejected for validation budget, with raw evidence retained separately. This does not reduce the precision of accepted decimal storage.
- D020: use a disposable file for full v1 API regressions because legacy startup and route engines have separate singleton in-memory databases. Pin the old forward-backlog test to its declared synthetic time, not today's date. No production logic changes.
- D021: user's revised continuation interval is 310 minutes, with requested initial 17:30 Europe/London start on 2026-09-20. Maintain the existing automation ID. Saved configuration later showed only the interval; do not infer a successful punctual run from configuration alone.
- D022: iterative graph discovery and cycle checking replace recursive path expansion. Shared descendants are visited once per graph, book-level composition is explicit, and 1,500-node chains/diamond graphs have regression coverage. Phase 3 still has to measure and bound total graph/batch size.
- D023: outcome clock admission explicitly selects receipt/source-event/source-published time from the pinned target and source envelope. Unknown clocks are rejected for observed outcomes, not substituted. Event-driven prediction admission stays closed pending the relevant target protocol; Phase 1 supports fixed positive horizons.
- D024: v2 public source capture is isolated from v1 clients/settings. Record raw bytes before parsing in exclusive local files; fsync payload/receipt and directory before an acknowledgement clock, then separately persist parsed output and its acknowledgement. Claims refer to the durable artefact, not the later index row. Partial/crashed attempts remain preserved and ineligible; recovery cannot invent old parse availability. The generic prospective writer remains closed until the bridge is implemented and tested.
- D025: new public trade verification targets Data API v2, with snake_case, explicit taker_only and cursor lineage. v1 behavior stays unchanged. Transaction hash is not a unique fill key. Native side interpretation is source/version specific; no automatic chain namespace, collateral or historical mapping from today's defaults.
- D026: diagnostic receipt-to-store import cannot open the prospective gate. It stamps and durably preserves source-specific parsing separately from generic JSON parsing, imports real earlier diagnostics as reconstructed and mocks as synthetic, checks the installed local schema, and appends runtime registry verification after the source observation to avoid dependency cycles. Rights scope remains source verification only; runtime HTTP success is not research/model admission.
- D027: cancelled and timed-out attempts preserve partial bytes before propagating cancellation; missing fsync/acknowledgement evidence is ineligible. Receipt v2 pins the session manifest; old v1 diagnostic receipts remain readable without being upgraded. Exact book replay refuses continuation after any rejected relevant message or reconnect until a full snapshot; failed messages consume the finite replay budget. Native sequence completeness is always unproven unless separately evidenced.
- D028: diagnostic identity projection records its own computation/acknowledgement and parser implementation hashes. Gamma source-event grouping does not establish independent economic events; chain/collateral remain unresolved. Prospective admission additionally requires an immutable loaded-code build and an explicit journal-versus-index model-readable boundary; neither is waived by successful diagnostic import.
- D029: prospective source facts use the durable journal as primary authority; SQL is a materialized index with its own post-commit receipt. The dedicated writer consumes verified run directories, never caller-provided prospective payloads. Actual downstream read/computation must be recorded before origins; journal availability is not SQL or model execution time. See `../architecture/V2_PROSPECTIVE_SOURCE_ADMISSION.md` for bounded source scope, build binding, clocks and tests.
- D030: Phase 3 preserves exact rational inclusion probabilities in sampling manifests. A nonterminating rational has no exact finite DECIMAL_TEXT representation; keep its numerator/denominator and a null decimal with explicit nonrepresentability, never a silently rounded scientific weight. Sampling roles are not independent events; repeated market assignments must be deduplicated at origin/evaluation boundaries. Incomplete source frames cannot establish universe-wide representativeness.
- D031 (2026-09-21): Gamma keyset frame enumeration is a separate predeclared journal, with source plus panel build binding and unchanged `closed=false` scope. The documented last-page signal is an omitted cursor on a short/empty page; explicit null is not silently equated to omission. Preserve every duplicate/conflicting version and every failed/torn attempt. Source exhaustion is an interval enumeration claim, not atomicity, population inference or an independent-event count. First-page cost measurement must precede a separate full-frame budget; no production discovery/startup path is used.
- D032 (2026-09-21): measured first-page cost precedes an explicit finite full-frame attempt: 1,000 requests / 100 rows each / 4 MiB per response / 256 MiB raw total / 15s request / 900s admission window / 1 GiB retained stop and 2 GiB free reserve. Current disk capacity supports this nonproduction bound. Frame manifest v2 references full per-page projections and streams verification to avoid retaining every raw/parsed page in RAM. Budget stops remain incomplete; they do not justify narrowing the research population or changing production retention.
- D033 (2026-09-21): first enumeration hit its raw ceiling after 40,900 complete rows, with all partial bytes retained. A second separately frozen attempt may use 1 GiB raw / 3 GiB retained, retaining the 1,000-request/100,000-row and time limits. The additional capacity is justified by actual 202 MB process memory / 654 MB disk evidence and a fresh 5 GiB capacity preflight. No old run is extended/relabelled; no outcome or performance threshold changes. Preserve original attempt and pin its cost hashes as additional provenance before the new request.
- D034 (2026-09-21): consume an old sealed frame through its original Git-pinned decoder in an isolated child process. Verify declared file sets/hashes and let original code verify its libraries and full journal closure; never weaken the current reader's build guard. Record a separate actual read policy/receipt under the consuming build, preserving original source facts, clocks and incomplete/synthetic status. Temporary extracted code is disposable; original evidence and failed/successful read journals are retained. No retrospective origin admission or automatic dependency installation.
- D035 (2026-09-21): preserve the original 100,000-member sampling default and its byte-identical frame hashing/selection semantics. Stream canonical member encodings into the frame digest and use bounded heap selection instead of sorting each entire arm. A caller must explicitly freeze a changed finite frame ceiling (maximum 400,000); that output is version 2 and includes the ceiling in its plan hash. Larger rational denominators remain exact. A separately reported 400,000-row synthetic capacity measurement is engineering evidence only, not live population coverage or permission to increase collection limits.
- D036 (2026-09-21): a separate explicit larger frame mode permits 4,000 requests /3 GiB raw /8 GiB retained, retaining 100 rows/page, 4 MiB/page, 15s/request, 900s admission and 2 GiB free reserve. It requires a newly recorded original-code read of the intact prior 1,000-request incomplete frame, with matching source/scope, all pages and nonterminal request-ceiling status; byte-ceiling or synthetic evidence cannot authorize live expansion. Existing default and diagnostic bounds stay unchanged. Check full retained-plus-reserve capacity before and after evidence verification. Keep all old attempts and new read receipts; no population inference or origin admission follows from capacity proof.
- D037 (2026-09-21, user requested continued engineering after attempt 3): frame manifest v3 supports an explicitly frozen opt-in retry policy: one retry per failed cursor, at most eight total, one-second backoff. Only named transient transport failures and HTTP502/503/504 qualify; malformed schema, invalid cursors, rate limits/denials and exhausted budgets stop. Each failed attempt keeps its raw bytes, error and clocks; a retry references the failed attempt but uses the last successful cursor parent. All attempts consume original request/byte/time/storage budgets. Reports retain every historical error and distinguish recovered from unrecovered failures. Old v2 frames require their original code and are never upgraded. No new complete-population claim is implied.
- D038 (2026-09-22, renewed continuation): opt-in HTTP connection reuse removes per-page client/connection setup without changing source scope or any D036/D037 budget, retry, clock or completeness rule. Frame manifest v4 binds capture session v2's transport policy: one HTTP/1.1 client, one connection/keepalive slot, 30-second idle expiry, no hidden transport retries, no redirects/environment proxies and cookies cleared before each request. All requests remain serialized; the client closes on success, failure and cancellation. Default diagnostic/source/frame paths retain per-request clients and capture session v1. Injected transports stay synthetic. Real loopback socket tests must demonstrate reuse and reconnection; this does not establish a fix for the live venue. After full validation, self-review and commit, at most one fresh finite fifth attempt may measure this changed protocol; previous failed attempts remain failed. A further failure is a data gate, not permission for another automatic unchanged run.
- D039 (2026-09-22): after verified complete-frame evidence, implement a pure versioned metadata projector as a bounded prerequisite to durable selection. Explicit fields only, exact decimals, first source-ordered outcome, aware close timestamp and distinct present/missing/invalid states. No fallback from other fields, invented category/economic groups, missing-value exclusion, quote semantics or causal availability claim. Future durable consumers must bind original row/mapping hashes and record actual read/computation clocks; this helper alone cannot admit a panel or origin.
- D040 (2026-09-22): durable development selection freezes an internally generated seed and finite policy before original-frame reads; preserves a complete row inventory and actual read/projection/selection clocks. Scheduled-only draws use explicit close-time/unknown strata and exact rational weights. Historical source data remains reconstructed selection, synthetic remains synthetic; no caller provenance, timestamp, payload or seed bypass. Failed runs are retained, never resumed/reseeded or truncated. Full requirements and 400,000-row/600-second/1-GiB-output bounds are in PHASE_03_PANEL_JOURNAL_CONTRACT.md. Prospective freshness, trigger/control evidence and origins remain later gates.
- D041 (2026-09-22): extend D034's original-Git-code reader to sealed selection journals with an explicit allowlisted selection decoder. Pin the original selection report and plan, execute its original full-closure reader in the same isolated bounded child, and record a new actual read receipt. Preserve seed, assignments, exact weights, old read/selection clocks and reconstructed/synthetic status. No redraw, source recapture, dependency installation or current-parser fallback. Existing frame-reader schema/semantics stay compatible. Validate fixtures and commit before an actual local read of the D040 selection; later collector admission remains separate.
- D042 (2026-09-22): preserve legacy sampling outputs and add an explicit assessment-aware v3 mode. Unassessed/unavailable/stale trigger evidence cannot enter the matched-control pool; only fresh measured negatives qualify. Keep these markets in the scheduled population and full assessment inventory. Freeze policy/age bounds, require a single neutral legacy-trigger authority, bind assessment identities/hashes/chronology, and retain exact conditional weights and control shortages. This pure planner validates declarations, not actual source/read/computation evidence; runtime verification and origin admission remain separate. No trigger thresholds or freshness values are promoted as empirically validated.
- D043 (2026-09-22): a separate bounded input-read journal freezes its build/policy before reading a completed SourceRun, preserves all exact rows and admissions (including failed responses), and records actual read/projection/acknowledgement clocks. Source clocks/provenance never change. Re-verification requires exact source closure; appending to that run invalidates this v1 read instead of silently accepting an incomplete prefix. Same-session monotonic order supplements UTC. No payload/subset/provenance/clock override or origin admission. Use 10-request/4-MiB source bounds, 16-MiB artefacts, 32-MiB total output, 60-second boundary checks and 2-GiB reserve. Streaming prefixes, source relocation, features and origins need their own contracts.
- D044 (2026-09-22): pure receipt-time quote projection uses only Gamma token/condition mappings known before the book receipt, refusing conflicting known versions and preserving source outcome order. Explicit receipt/identity freshness bounds are development policy, not venue update age. Exact positive-size best quotes/midpoints exclude duplicate/crossed/one-sided/stale books; all source failures remain inventoried without fallback prices. Mixed provenance is refused. Runtime source verification and durable computation remain required; no feature-store/origin admission. The next writer's contract is PHASE_03_QUOTE_COMPUTATION_CONTRACT.md.

- D045 (2026-09-22): durable quote computation freezes policy/build before a fresh D043 read, uses actual computation start as D044 cutoff and preserves exact results plus a post-fsync acknowledgement. Replay verifies the whole source/child closure and original cutoff. Bound the parent recursively to 64 MiB including the 32 MiB child allowance, 16 MiB per artefact, 180 seconds checked at operation boundaries and 2 GiB free reserve. Time checks are not hard cancellation. Preserve failed/torn outputs; no caller clocks, payloads or provenance overrides. This milestone admits no origin or feature-store row.

- D046 (2026-09-22): explicit `receipt-time-selected-market-v1` source policy adds `gamma.market` at the documented fixed `/markets/{id}` endpoint. Canonical bounded decimal target strings, no query/auth/custom host, exact response-ID binding and replayed request validation. Default SourceRun policy and legacy source contract records remain unchanged. Preserve nullable lifecycle separately from identity version; unknown/closed/inactive/archived/not-accepting targeted quotes abstain. No SQL identity-import expansion or origin admission. Official basis and tests are in PHASE_03_IDENTITY_REFRESH_CONTRACT.md. The separately frozen two-request development measurement does not refresh or promote the historical draw.

- D047 (2026-09-22): extend the original-Git-code reader to durable quote computations. The original pinned decoder verifies all transitive source/read facts and exact quote result; the new read compares the unchanged complete facts and summary hash/availability, then records its own receipt. Retain original cutoff, source provenance and admission flags. Output must remain outside the computation and source trees. Frame/selection APIs remain compatible. This is read-only preservation/recovery, not a new observation or origin.

- D048 (2026-09-22): immutable panel declaration freezes explicit timing/sampling slot ceilings, internally generated seed, source policy, feature-family limitations and worst-case distinct role/target resource reservation before numerical reads. Planned quotas are not enforcement; collection stays disabled pending a guarded SourceRun writer and verified fresh selection/origin integration. Reserve full existing D045 computation bounds without assuming small future responses or role overlap. Capacity failure refuses the plan rather than truncating controls/universe. Frame age is measured from the oldest source receipt at the eventual selection cutoff; no frame verification is claimed by this declaration. The SamplingProtocol recipe remains the input to D042's assessment-aware mode, never authorization for legacy false=untriggered control inference.

- D049 (2026-09-22): opt-in SourceRun v2 freezes a 1–256 MiB retained quota and uses task-local guards for session, raw, parse and admission writes. Reserve raw response/receipt capacity before HTTP; retain raw on later parse refusal, a 64 KiB failure allowance and 2 GiB free reserve. Failed guarded attempts are terminal, never overwritten or resumed. Replays check frozen quotas and actual bytes/depth/files; old default schema unchanged. New guarded runs refuse the existing unbudgeted SQL index-receipt path before DB access. This is application accounting, not an OS reservation or protection against external file mutation; panel collection stays disabled pending full integration.

- D050 (2026-09-23): one deterministic exclusive selection per immutable panel declaration, using its frozen seed and full role/target reservation. Verify the original frame and complete row inventory, enforce source interval/age at actual cutoff and durable selection acknowledgement, and retain synthetic versus prospective selection provenance without origin admission. Until durable trigger evidence exists, freeze an explicit no-measured-assessments policy: D042 treats every member as not assessed, never a negative control. Persist the complete uniform assessment inventory losslessly by member domain/count/hash and constant state; replay expands it exactly. Slot overflow fails without truncation; old D040 draws and schemas stay unchanged. Collection remains disabled. See PHASE_03_FRESH_SELECTION_CONTRACT.md.

- D051 (2026-09-23): optional compact-v1 source-read/computation profiles enforce 4/8 MiB whole outputs and 2 MiB artefacts, keeping existing request/raw bounds, clocks, exact values, deadlines and failure/free reserves. Defaults and v1 schemas remain unchanged; compact records use v2 schemas with exact parent/child profile binding. Oversize inputs preserve raw and partial failures, never truncate or upgrade in place. Explicit compact panel declarations reserve the full 8 MiB cost for every origin/control/target computation, and fresh selection binds that choice. Collector integration must pass the declared profile; collection remains disabled. See PHASE_03_COMPACT_COMPUTATION_CONTRACT.md.

- D052 (2026-09-23): actual activation consumes/reverifies one declaration-bound selection, seals selected identity/role lineage and derives immutable per-cycle intent IDs and schedules from its durable acknowledgement plus a fixed two-second development lead. Full existing panel reservation plus 32 MiB activation and 128 KiB metadata per origin/target attempt precedes source-value reads. Check frame freshness at read completion and save; preserve failed/late activation. Writer returns already-verified facts without spending the new lead on another full-population replay; independent recovery replays all source/selection closure at original times and never reschedules. This is not an enabled collector or admitted origin. See PHASE_03_ACTIVATION_CONTRACT.md.

- D053 (2026-09-23): synthetic-only origin worker owns an exclusive deterministic run before actual activation; reserves all source/computation/metadata costs, follows immutable schedules and fixed identity→book→trade requests, and records real consumption/freeze/durability clocks. Compare selected identity/rules and recheck freshness at freeze. Derive late persistence without rewriting facts. Inventory every retained partial byte under finite bounds; successful replay verifies the full source/computation chain. Expired, failed and abstaining slots remain explicit. No resume, caller clocks or live transport; target integration remains required. See PHASE_03_ORIGIN_WORKER_CONTRACT.md.

- D054 (2026-09-23): versioned pure target adapter recomputes the exact two-request target projection, binds fixed market/token and provenance, retains the origin's mapping availability and separately records fresh identity/lifecycle consistency. Any changed identity/rules cannot supply a price or closure. Only matching, fresh known closure maps to closed; other abstentions remain explicit. Failed-book token comes from request metadata. Target availability uses the durable computation acknowledgement and freshness is rechecked there. Actual journal consumption belongs to the due worker; no caller payload authenticates an outcome. Existing selector outputs remain unchanged. See PHASE_03_TARGET_ADAPTER_CONTRACT.md.

- D055 (2026-09-23): synthetic-only due executor claims one immutable run, verifies exact durable origins and binds consumed facts/intent hashes. Preserve all fixed attempt times, including ineligible/expired slots; use guarded identity/book requests only after origin acknowledgement and before the original request deadline. Late receipts remain late. Incomplete earlier evidence blocks outcome selection. Quote-computation availability stays separate from the final target/adapter receipt used by outcome selection. Independent replay verifies sources, adaptation, schedules, original cutoff and exact midpoint change; no profit/SQL/panel-admission claim. A separate worker after a multi-cycle origin run may miss early targets; a new interleaved orchestration contract is required before a pilot. See PHASE_03_DUE_WORKER_NEXT.md.

- D056 (2026-09-23): one synthetic-only serialized runtime interleaves immutable origin schedules with each origin's due attempts immediately after its durable plan. Order is scheduled UTC, targets before origins on a tie, then immutable ID. Reserve the full panel plus bounded runtime/plan metadata before activation. Independently replay the evolving queue, origin/target source closure and actual dispatch/save clocks. Failures retain evidence and cannot resume. Original-build recovery runs only the Git-pinned decoder, emits a separate read receipt and protects every source dependency from nested output. Old APIs/schemas and synthetic provenance remain unchanged; no live collection, SQL admission or pilot acceptance. See PHASE_03_INTERLEAVED_RUNTIME_CONTRACT.md.

- D057 (2026-09-24): preserve F08/F09 snapshot components as exact reduced rationals with exact terminating decimals and explicit repeating-decimal missingness. Retain all bounded source-ordered levels, raw precision, zero sizes, formula intermediates and native timestamp/hash strings. Numerical limits quarantine unsupported values without deleting raw sources. Native age/tick/collateral remain unresolved. A separate 16-MiB computation freezes policy/build before actual compact source reads and independently replays at the original cutoff; partial failures are terminal. Original-Git recovery preserves full facts/summary and all old clocks. Existing quote/origin formats stay unchanged; no registered window feature, origin, SQL or live-panel admission. See PHASE_03_BOOK_COMPUTATION_CONTRACT.md and the next PHASE_03_DENSE_WINDOW_NEXT.md.

- D058 (2026-09-24): add a separate synthetic-only finite raw stream window, with immutable source/build/limits, actual event and durability clocks, fixed subscription-anchored duration and heartbeat schedule, ordered raw-frame/hash chain, explicit late/truncated/incomplete states and terminal failures. No live connector or caller clocks/provenance. Preserve every bounded raw/control/malformed frame before interpretation; original-Git recovery verifies full closure without changing clocks. Completed duration does not establish native sequencing, feature eligibility, origin/SQL admission or a live pilot. See PHASE_03_WINDOW_CAPTURE_CONTRACT.md; decoded coverage and causal identity/pre/post reconciliation remain next.

- D059 (2026-09-24): decode verified raw windows with exact frame/array lineage, control/unrelated/invalid/late states, snapshot-before-delta recovery and retained gaps. Weight imbalance by covered receipt duration, preserving exact rational integrals, unavailable tails and zero-denominator states. Receipt hold is an explicit engineering policy, not native update age. A new durable consumer freezes policy/build before actual full source reads and calculation, checks source hashes/closure at consumption, and recovers through original Git code. Native sequencing/identity/fill prerequisites remain unproven; no F02/F10/F27, origin or SQL admission. User scope is Phase 3 only; Phase 4 begins in a fresh conversation after a completed handover. See PHASE_03_WINDOW_COVERAGE_CONTRACT.md and PHASE_03_WINDOW_IDENTITY_NEXT.md.

- D060 (2026-09-24): consume an exact verified targeted Gamma/book computation into an exclusive durable pre-window binding. Derive child token/condition from the ordered mapping/rule version and preserve original source/computation availability. Require fresh known-active evidence at actual read completion and binding durability; reassess at subscription and retain expired state without changing earlier clocks. Synthetic provenance only; no live transport or caller identity/clock override. Reserve the whole child plus metadata and protect all transitive dependencies in original-Git recovery. Post-window primary request chronology and endpoint reconciliation remain next, never a repair of earlier gaps. See PHASE_03_BOUND_WINDOW_CONTRACT.md.

- D061 (2026-09-25): freeze a separate bounded comparison policy before actual verified reads of a D060 bound window and separately collected D057 post-source evidence. Authenticate primary request-start clocks through capture receipts; a response arriving after the bound report cannot legitimize an earlier request. Preserve original mapping/rule availability, identity/lifecycle changes, failures, staleness and expired pre-binding. Compare exact best price/size endpoints only, retaining rational differences, receipt offsets and coverage gaps; agreement never proves full depth or native continuity. Independent/original-Git replay protects all transitive dependencies, original clocks and synthetic provenance. No socket, SQL or feature admission. See PHASE_03_WINDOW_RECONCILIATION_CONTRACT.md and the next PHASE_03_SOCKET_TRANSPORT_NEXT.md. Phase 3 remains incomplete; Phase 4 is reserved for a fresh conversation.

- D062 (2026-09-25): isolate fixed market-socket connection options before integrating the durable driver. Reject redirects, proxy discovery, compression, protocol pings, retries and reconnection; pin the tested 17.0.1 API and bound connect/close. Expose only a numeric 127.0.0.1 test seam with synthetic transport provenance. Actual loopback tests preserve text/binary/control semantics and reject oversize data without fabricating raw bytes. This primitive creates no journal, origin or source admission; its future owner must enforce verified prebinding, complete operation clocks, heartbeat/window/total budgets and cleanup. No public socket was opened. See PHASE_03_SOCKET_TRANSPORT_NEXT.md.

- D063 (2026-09-25): add a separate durable socket-window version around D062. Derive identity from actual verified pre-Gamma/book reads, freeze all transport/source/budget/build facts before connect, and recheck freshness immediately before subscription after intent durability. Distinguish actual receipt from serialized record/fsync time. Preserve raw wire type/bytes, exact prefixes versus wholly unavailable socket-rejected bytes, network operation starts/results and close codes. Bound the interval from actual send completion, use ten-second PINGs and close on cancellation/disk failure. Independent/original-Git recovery preserves all prior identity/clocks and transitive roots. Public and explicit loopback paths are separate; synthetic evidence never becomes prospective through a mismatched path. No source/feature/pilot admission and no public run at this milestone. See PHASE_03_SOCKET_WINDOW_CONTRACT.md and PHASE_03_SOCKET_ANALYSIS_NEXT.md.

- D064 (2026-09-25): new durable socket diagnostics consume verified D063 raw/event/ack chains and optional separately collected post-book evidence. Reuse exact receipt and endpoint arithmetic behind a new authenticated envelope without promoting legacy synthetic journals. Preserve actual identity/read/receipt/fsync/computation clocks and original primary post-request starts; refusal has no invented interval, early termination no invented endpoint. Full facts replay and original-Git recovery protect every transitive dependency. Exact source provenance and false admission flags remain; no source request is implicit. Finite output/free/time bounds and exclusive failure-terminal roots apply. Public diagnostic protocol must be separately frozen/committed before collection; no measured panel/feature/alpha claim. See PHASE_03_SOCKET_ANALYSIS_CONTRACT.md.

- D065 (2026-09-25): compose the accepted socket/source/analysis/recovery primitives into one fixed-target diagnostic with a one-attempt CLI path. Git-hash verification and the entire storage reservation precede any request. Preserve actual declaration/stage/child/recovery clocks, unknown/failed/closed prior states and terminal partial failure. A successful prior allows one bounded socket; a sent, fresh subscription alone permits a separate post pair. No replacement target, reconnect or source request during original-code recovery. Explicit MockTransport+loopback entry stays synthetic. Bounds and source-documentation review are frozen in PHASE_03_SOCKET_DIAGNOSTIC_PROTOCOL.md. The diagnostic cannot accept the representative panel or scientific feature/edge gates.

- D066 (2026-09-25): declare an exact configurable absolute snapshot-imbalance rule before fresh Gamma/book requests, then authenticate sources and actually read/compute/persist a three-state decision. Exact signed/absolute/difference values and unavailable reasons are retained; failed or stale data is never an untriggered control. A response arriving after declaration cannot legitimize an earlier request. New exclusive computation and full original-Git recovery protect old clocks and transitive source evidence. This is development control-measurement plumbing, not a validated threshold, registered dense feature or admitted sampler/model input. See PHASE_03_TRIGGER_ASSESSMENT_CONTRACT.md.

- D067 (2026-09-27): a completed asyncio timer is not proof that its UTC boundary has arrived.
  The full regression preserved three intent clocks 751/2,551/1,084 microseconds early.
  Recheck actual UTC before origin/target intent creation, runtime dispatch and outcome cutoff;
  retain actual returned clock, do not clamp/backdate it or relax replay. A monotonic wait
  budget refuses persistent wall-clock divergence. Host pauses keep expiry/staleness semantics.
  Six deterministic timer/clock cases plus existing worker/runtime/original-recovery tests
  cover the correction. This is a causal correctness fix, not empirical Phase 3 acceptance.

- D068 (2026-09-27): reuse the existing complete selection and sampler. Freeze all sampled
  assignments, exact rule, new random second-stage seed and deterministic future decision paths
  before requests. Authenticate D066 primary journals, frame mapping/rule lineage and actual
  cutoff availability before matched-control planning. Keep measured negatives separate from
  stale/changed/failed/unknown evidence; retain unfilled slots and first-stage assignments.
  Preserve first-stage inclusion and conditional second-stage probabilities without inventing a
  global arm/union weight. Exclusive completion and original-code recovery prevent later evidence
  additions changing a sealed result. Full collector reservation and role admission remain separate;
  no source worker, origin, SQL admission, live pilot or edge claim is enabled by this boundary.

- D069 (2026-09-27): bound screening by sampling strata before markets, rather than dropping
  matching dimensions or taking a deterministic prefix. Freeze `strata_limit` before frame
  reads; worst-case limit × scheduled-per-stratum must fit declared scheduled slots. New
  declaration v3, selection v2 and sampling-plan v4 retain every stratum, full inventory,
  unknowns/exclusions and exact stratum × conditional-market inclusion. A separate ranking
  domain separates stratum and member draws; the complete plan hash binds the design as well
  as the unchanged sampling recipe. Only complete, entirely unassessed frames use this mode.
  D068 retains the resulting screening probability; later arm/matching weights stay conditional.
  Legacy default encodings/hashes are unchanged. Existing activation intentionally refuses the
  new version until verified-role integration; this is no permission for live collection.
  The cap is configurable, not a scientifically selected pilot size. Full collector reservation
  remains required before any public request.

- D070 (2026-09-27): bounded synthetic screening owns finite source paths/budgets before
  acquisition, freezes concurrency in 1–8, and enforces full screening plus existing runtime
  and recovery reservation without overlap discounts. Reuse D066/D068 for actual decisions
  and exact conditional roles; overflow is retained, never truncated. A single original-Git
  screening recovery authenticates the entire transitive evidence chain, avoiding redundant
  child recoveries. Drain durable computation threads on cancellation. No live transport or
  activation is enabled; later socket/external writers require additional reservations.

- D071 (2026-09-27): screened activation v2 authenticates the complete screening journal
  and binds its exact seed, report, availability, frozen roles and sampling weights. Check
  measured-role freshness at both actual read completion and durable acknowledgement; retain
  scheduled unknowns, deduplicate markets and refuse capacity overflow without redraw. Roles
  describe the screening occasion, not fresh signals at every cycle. Recovery preserves the
  original cutoff/schedule and all source dependencies. Legacy activation defaults remain v1.
  No live collection or synthetic-runtime admission is enabled merely by activation.

- D072 (2026-09-27): reserve one concurrent slot from origins for due targets; dispatch ready targets first, then scheduled UTC/id. Use 2–8 bounded isolated job event loops and drain durable writers on cancellation. Record/replay actual dispatch/completion and child clocks, with no early start or altered deadline. Version the screened synthetic runtime explicitly and retain legacy replay. This addresses observed queue starvation risk; it does not establish empirical timing, continuous socket state or feature admission.

- D073 (2026-09-27): use research-register XNOAA station observations for the bounded external-source prerequisite. Current Coinbase market-data terms expressly restrict AI/automated-system development absent consent, so do not promote or recollect those diagnostics. NWS documents open API data for any purpose. Add an opt-in station receipt policy, exact native quantity/unit/QC/null preservation and original actual-read recovery; no market relevance, forecast, native publication-time or daily-extreme inference. Measure one fixed KNYC request only after the committed protocol/tests/review. Failure is retained; no replacement or retry. See PHASE_03_EXTERNAL_OBSERVATION.md.

- D074 (2026-09-28): opt-in concurrent runtime v3/origin v2 attaches D057 exact snapshot components before actual origin freeze using already authenticated source reads. Preserve full numerical inputs in their existing primary journals and a compact versioned manifest with exact ratios/hash/intermediates; do not duplicate input reads or raw levels. 16 KiB manifest stays inside unchanged origin/plan reservations. Recheck eligibility at actual freeze and keep unsupported flow/native-window/related/external families unavailable. No source requests, Phase 4 or predictive admission added. Detailed contract: PHASE_03_ORIGIN_FEATURE_MANIFEST.md.

- D075 (2026-09-28): measure probability-sampled source/control availability before further window orchestration. Expose a separate public worker without transport/provenance injection; derive source provenance from actual transport and refuse synthetic/reconstructed assignment lineage before network. Retain full reservation, exact probabilities and every missing state. Frozen <=8-member/16-request protocol and executable command are in PHASE_03_SCREENING_MEASUREMENT_PROTOCOL.md. This neither admits origins nor waives empirical Phase 3 gates.

- D076a (2026-09-28): keep gamma_identity and historical mapping hashes unchanged. Compare an authenticated current hash to the validated full frame identity and, only for a nonempty old event list, the exact canonical identity with event IDs absent. Preserve both hashes and explicit membership-unavailable state. This proves equality of all other fields without inventing current event IDs. A differing hash is not diagnosed as a core change without evidence. Helper only; schema/consumer integration and prospective validation remain.

- D076b (2026-10-02): opt-in fs2-screening-identity-v2 freezes D076a before source requests and records comparison evidence in every assessed state. Original v1 defaults remain strict. Legacy activation refuses this new schema until origin/target semantics are explicitly integrated. No historical result is rewritten.

- D076c (2026-10-02): bounded worker v3 records an explicit identity_policy before acquisition and passes it to the new screening declaration. No transport/provenance injection, default-policy changes, reservation reductions or historical reinterpretation. Synthetic asymmetric-source tests establish software behavior only. Next refresh the expired frame under D077 before a separately frozen new screening attempt.


## D078 — corrected screening measured; full-population replay is off the future causal path

Frozen6cbcf4d protocol executed once under9ea4e38; numerical evidence and limitations are in PHASE_03_SCREENING_REFRESH_EVIDENCE.json. No threshold/sample retuning, changed history or missing-control imputation. Endpoint-aware core identity comparison resolved the measured D075 blocker while preserving unknown current event membership. Four missing controls remain.

The292.963009s screening-cutoff-to-original-recovery delay exceeds the frozen120s freshness limit. The next active execution must authenticate frame/selection before sources, own immutable bounded verified context, and perform full original-code audit after collection. Actual input/freeze/save clocks and cutoffs are never reset by verification. Any changed dependency fails final acceptance. This is justified by measured timing, not speculative infrastructure. New active version and asymmetric-identity origin contract remain required; see PHASE_03_PILOT_EXECUTION_NEXT.md.


D079 — owned pre-source screening context: screening v3/worker v4 retain an immutable bounded context minted by the actual complete selection read. Source completion no longer repeats population replay; cold/original audit still verifies all dependencies before worker return. Default legacy paths remain unchanged. Four new ownership/tamper/cold-recovery tests passed81.15s;39 existing screening/worker regressions passed500.62s. Ruff/backend, canonical and whitespace checks pass. Initial instrumentation replaced a protected function and correctly triggered build-integrity refusal; the test now observes real calls via profiling without replacing code. No public requests or new empirical claims. Activation/runtime wiring remains next; Phase3 incomplete.


D080 — owned activation v3: the private screening finish operation can transition directly to activation using its authenticated bounded state. It retains full original frame identity, the explicit comparison policy, report hashes, exact roles and actual read/save clocks. Cold/original activation recovery still verifies the full frame/selection/screening chain. Legacy activation remains unchanged; existing origin workers explicitly refuse v3 until versioned origin identity handling is implemented.64 affected tests passed839.55s: owned_activation, owned_screening, activation, screened_activation and origin_worker. Initial new test expected the wrong original-reader envelope; corrected to compare report.summary, with no implementation/guard change. Ruff/backend, canonical and whitespace checks pass. No public collection or Phase3 acceptance.


D081 — owned causal pilot execution: origin v3, due v2, concurrent runtime v4 and pilot worker v5 now compose authenticated screening, activation, causal origins and targets before full original-code audit. Public entry points accept no source payload, clock, transport or provenance override. Full frame identity and current event-membership missingness remain distinct; targets compare exactly against actual frozen origin identity. Legacy versions remain strict. No production or SQL change.

Validation: six new owned-pilot cases passed across development logs (a wrong test-result key was corrected without changing safeguards); 87 affected regressions passed in1334.27s (/tmp/arepo_d081_regression.log). Self-review found runtime_concurrency=None could select the internal screening-only path; public/synthetic wrappers now reject it explicitly. Eight focused invalid-input cases passed0.63s after that guard; no redundant broad rerun. Ruff/backend, canonical contract and whitespace checks pass. Review covered authenticated private context, actual provenance/clock ordering, strict target identity, bounded due capacity, cancellation drainage, immutable dependencies and original-code replay. Synthetic success is not empirical panel acceptance.

Next: freeze PHASE_03_OWNED_PILOT_PROTOCOL.md and execute D082 once under the committed implementation. Preserve all failures/missing controls/windows/related/external values. Phase3 remains incomplete; no Phase4.


D082 executed once under c881288d80dbeddfc195c6eacceeb63b78f58e20 and passed its frozen execution gates: eight observed origins/eight valid targets, six triggered roles/two observed matched controls over eight distinct markets; four unfilled controls retained. All56 requests returned200 (24 Gamma/24 book/8 taker-trade),183036 raw bytes. Origin freeze delay8.084763–29.097624s within60s; freeze-to-save1.463–17.300ms within5s; target durable availability5.477850–8.155644s after due within15s. Exact probabilities and raw numerics/clocks preserved. Full original-code audit passed; independent evidence check verified107 artifact hashes/sizes, all eight timing pairs, both matched pairs and exact counts. No code tests repeated for evidence-only changes.

Evidence: PHASE_03_OWNED_PILOT_EVIDENCE.json. Run completed2026-10-03T19:49:41.661088UTC, exit0, elapsed1003342292167ns including selection/audits; no collector remains active. D082 is a successful execution pilot, not predictive evidence or full Phase3 acceptance. PHASE_03_ACCEPTANCE_STATUS.md maps remaining pre-origin windows/history, related/external eligibility and baseline plumbing to the exact D083 next action. Do not rerun D077/D078/D082 or retrofit richer inputs into those origins. No Phase4.


## D083 — authenticated pre-origin window component (2026-10-04)

Owned origin v4/manifestv2 bind a verified pre-origin socket analysis and exact irregular
prior/current price primitives. Strict actual identity/provenance and cutoff/freeze age
checks preserve missingness; late eligibility never erases raw numbers. Sparse receipt
coverage never becomes venue continuity or a registered window feature. Legacy defaults
remain strict. See PHASE_03_PRE_ORIGIN_WINDOW_CONTRACT.md.

Validation:21 new input/origin cases passed255.10s; after final frozen16KiB quota guard,
53 affected window_origin/origin_worker/origin_features/window_reconciliation cases passed
611.89s (/tmp/arepo_d083_regression.log). Explicit isolated SQLite, disabled email; no source
edits during validation. Ruff/backend, canonical contract and whitespace pass. Self-review
covered actual clocks/freshness, identity/provenance, hash/raw tampering, negative/zero/missing
history, silence/disconnection, byte ceilings and legacy replay. Cold per-origin recovery
passes; full original-runtime dependency recovery is not yet wired. No public requests.

This accepts a software component, not Phase3. Next bind selected observers internally in
a bounded owned batch/runtime, reserve all dependencies before reads, retain failed members,
and test cancellation/original-runtime recovery before a separately frozen public measurement.
D082 remains immutable; related/external eligibility and full empirical scope remain open.


## D084 — owned bounded windows and runtime (2026-10-04)

Worker v6 starts one bounded observer per actual selected pre-book in independent event
loops, before activation/origins. Whole socket40MiB+analysis64MiB costs per possible member
are reserved before requests with no overlap discount. Runtime v5 binds exact worker/member
hashes and routes actual dependencies to origin v4. Unavailable pre-books retain their
sampled member and explicit missingness; local integrity failures terminate without erasure.
Original-Git recovery authenticates window, analysis, pre-book and raw source dependencies.

Nine new integration cases pass across targeted runs: concurrent success/original replay/
dependency tamper; eight remaining cases127.20s. Final affected legacy regression49 passed
722.18s (/tmp/arepo_d084_regression.log): owned_pilot, concurrent_runtime, screening_worker,
original_runtime. Explicit isolated SQLite/email disabled; source remained fixed throughout.
Ruff/backend, canonical and whitespace checks pass. No full-backend or empirical claim.
Development fixture errors (timing bounds, streaming404 response, string-encoded duration)
were corrected; canonical selected metadata comparison handles saved versus in-memory types.
No causal guard, quota or deadline was weakened.

Self-review covered owned selection/provenance, actual pre-t0 clocks, strict dependency/root
binding, whole reservation, unavailable and disconnected members, terminal failure retention,
cancellation drainage, immutable numerical/gap evidence, original recovery and legacy defaults.
Next: separately committed PHASE_03_WINDOW_PILOT_PROTOCOL.md, execute once and preserve all
results. D082 is unchanged; receipt diagnostics never establish native venue continuity.
Phase3 incomplete; Phase4 remains reserved for a fresh conversation.


## D085 — failed integrated window pilot (2026-10-04)

Executed once under1c27f31d6c526758d4b27cff4def7d2275de26b5; completed18:38:34.217034UTC,
exit0 with full original-code audit. Forty-six HTTP responses:19Gamma200,11book200,8book404,
8taker-trade200;128019 raw bytes. Eight sampled members retained;3observed origins/3valid
targets, one observed matched trigger/control pair,2unfilled controls. Four completed socket
intervals, but zero histories passed frozen freshness. Source unavailability and replay delay
are distinct limitations. Execution gates fail; Phase3 is NOT accepted.

Evidence PHASE_03_WINDOW_PILOT_EVIDENCE.json preserves raw-linked clocks, exact probabilities,
all failure states, windows and target results;276 artifact hashes/sizes independently verified.
Window ages at read67.367183–103.429699s exceed60s. Prior quote ages at freeze121.217612–
155.643060s exceed120s. Three windows cover1s/10s, one4.196189209s/10s under the original
receipt hold rule; no native continuity claim. No relevant selected external information;
economic grouping remains unresolved. No rerun, redraw, retrospective limit change or Phase4.

Next: PHASE_03_WINDOW_LATENCY_NEXT.md. Remove measured redundant cold replay through bounded
process-owned writer outputs, retain full cold/original checks, then reassess availability and
freeze a separate protocol. The latency fix cannot erase unavailable books or manufacture edge.

## D086 — owned window reuse (2026-10-05)

Removed redundant pre-activation replay using actual collector-owned results with immutable
assignment copies, one-shot slots and bounded byte seals. Seal pre/source before verification;
seal socket before analysis; bind analysis and entry results to returned writer hashes and
check all bytes/closure before activation. Cold/original readers still replay original facts.
Read/freeze ages, missingness, sampling, receipt gaps and native-continuity refusals unchanged.
21 scoped tests pass:19 in338.88s plus2 mutation-boundary cases in38.92s. Ruff/canonical/diff
checks pass. Full runtime test observes no owned-window cold read before14 source calls, and
original recovery agrees. No new empirical acceptance. Next: eight-member synthetic timing.
Self-review covered source substitution, private state, closure/bounds/symlinks, post-verification
mutation and cancellation drainage; no production/database/API changes.
Retained D085 lifecycle review:8 raw Gamma hashes verified;4 unavailable pre-books correspond
to closed/non-accepting current state. Future lifecycle freshness must be declared before a
new draw. Preserve D085 as failed; no posthoc selection, denominator substitution or threshold
change. See PHASE_03_WINDOW_AVAILABILITY_REVIEW.json and PHASE_03_WINDOW_LATENCY_NEXT.md.

D086 implementation531c3c3 passes21 scoped tests, but its eight-member synthetic measurement
failed stale-role activation before any origins. Owned/cold contexts agree; handoff0.622521s
versus later cold replay29.326286833s. First-batch windows already~81s old (60s limit).
Next D087: bounded local CPU/call profile and acquisition/analysis repair per
PHASE_03_WINDOW_LATENCY_NEXT.md. Preserve failed runs and original freshness; Phase3 incomplete.

## D087 — measured compilation overhead and bounded expectation cache

Read-only cProfile of retained D086 member000: pre-book487130500ns, with162 compilations
consuming363913126ns; socket analysis2013804375ns, with666 compilations consuming1541182456ns.
Profiling overhead included; not an end-to-end or empirical market measurement. Full script/
results: PHASE_03_VERIFICATION_PROFILE.json. Evidence supports a small verifier optimization
before new observer infrastructure.

Cache at most256 immutable expected-code tuples keyed by exact source bytes AND filename,
with a lock for concurrent first use and LRU eviction. Do not cache successful verification:
every call still hashes current package files, checks the import-time build, checks actual
loaded functions and reads dependency versions. Changed bytes/paths never reuse expectations;
warm function replacement still fails. Output schema, numerical/source recovery and all causal
clocks/freshness remain unchanged. This is not an owner-tamper security boundary.

76 targeted tests passed119.88s: research_build_cache, feature_store_source_run,
research_panel_frame, research_panel_owned_windows, research_panel_window_context. Includes
cold/warm compile counts, mutation after warmup, source byte changes, key separation, threads,
eviction, public override refusals, missingness, cancellation and original-code recovery.
Ruff/backend, canonical and whitespace checks pass. Self-review covered cache mutability/
bounds/concurrency, freshness and unchanged per-call code/file checks. No public request.
Next: one fresh eight-member synthetic measurement at fs2_synthetic_latency_20261005_2,
script /tmp/arepo_d087_benchmark.py, after commit. Same4 workers,10s windows,60s window/120s
history freshness; preserve timing even on failure. Failed D086 roots remain untouched.


D087 measurement completed under5678b10:8/8 observed origins,8/8 histories eligible at freeze,
8/8 observed targets and complete original-code recovery;56 synthetic HTTP calls, no public
requests. Elapsed149.854142709s; owned finish0.177550291s and post-target cold read6.686687208s.
Synthetic diagnostic, not alpha or full Phase3 acceptance. Full clocks, code, script and1270
artifact hashes: PHASE_03_VERIFIER_CACHE_TIMING_EVIDENCE.json. The old failed D086 is unchanged.
Next D088: freeze/execute one complete lifecycle-fresh frame per
PHASE_03_LIFECYCLE_FRAME_PROTOCOL.md, then a separately frozen public pilot. No new observer
infrastructure or freshness relaxation is justified by this successful scoped measurement.

## D088 complete frame; D089 unattended fresh-frame/pilot boundary

D088 finished2026-10-05 04:58:57UTC underf5eee00, exit0. Rootfs2_capture_0da49550169349f9adc9947dcaecc76f:
235224 distinct rows,235180 mapped,44 unresolved;2353 requests, zero retries/errors/conflicts.
Source interval04:46:15–04:53:20UTC (425.282097s), raw1524579122/retained3739809659bytes,
peak583254016bytes. Full CLI verification passed; report/metadata/wrapper hashes preserved in
PHASE_03_LIFECYCLE_FRAME_EVIDENCE.json. No collector remains. The next assistant continuation
arrived09:47UTC, outside the prospective1h rule. Do not re-age or use this frame for that pilot.

D089 freezes one end-to-end process so verified fresh frame immediately feeds selection and
pilot without an assistant-turn boundary. Existing APIs only; no production/scheduler change.
New frame allocation7GiB (~2x observed retained cost), same4000 requests/3GiB raw/900s/limits,
universe and retries. Full combined reserve13308526592bytes includes frame, all panel/selection/
window/target/original-recovery budgets,2GiB free reserve and34MiB frame-capacity read overhead.
Observed free14327640064bytes; launcher must recheck. Quota/incomplete source stops the chain,
never admits a partial universe. No old evidence deleted or live retention changed.
Exact code and unchanged five pilot gates: PHASE_03_FRESH_WINDOW_PILOT_PROTOCOL.md.
Offline syntax/API budget validation and canonical/whitespace checks pass; unchanged76 tests
are not repeated for orchestration. Review: exclusive roots/logs, immutable build, all-stage
reservation, source completion and real clock gates, no redraw, complete original recovery.
One successor updated to15:57London/14:57UTC, same task/prompt; initial allowance0% primary/
79% weekly used. Phase3 only; no Phase4 or full acceptance claim.

## D089 final empirical result — 2026-10-05

Complete under404ad5efd12c6913ff062aa3f702db1630c08ea4, wrapper exit0 at10:22:50.943457UTC.
No collector/test remains active. Fresh frame236887 distinct/236843 mapped/44 unresolved,
2369requests, no retries/errors/conflicts, full source and original-code audit. Selection
uniformly chose4of109strata (4/109), with exact conditional member/role fractions preserved.
Eight scheduled/three triggered/one control roles span eight unique markets; two unfilled
control slots remain. Five observed origins/five fresh completed histories/five valid targets,
one actually observed matched pair. Six-of-eight origin/history gates FAIL. Phase3 incomplete.
Full immutable clocks, receipts, values,258 independently checked window/origin/report artifacts,
additional target hashes and extraction scripts: PHASE_03_FRESH_WINDOW_PILOT_EVIDENCE.json.

All50HTTPrequests returned200 (21Gamma,21book,8trades),191706raw bytes. The three absent
histories came from genuine one-sided pre-books:5233594 has67bids/0asks;5299067 has74/0;
628957 has0/54. All three Gamma records were active/nonclosed/accepting orders. Thus refreshing
the frame did not cure this limitation; no transport failure, freshness relaxation, retrospective
filtering or repeat-draw-until-success is justified. Five available histories passed unchanged
clock gates after D087. Native continuity remains unproven; these are receipt-time diagnostics.
None of eight questions matches the KNYC quantity. France/Spain EURO2028 questions suggest a
possible relation but do not establish a rule-aware economic group or causal related-price input.
F01/F02/F10/F27, related/external and v1 rolling-z-score inputs remain honestly unavailable.

Self-review: original audit, exact rational stage weights, all8denominators, actual freeze
eligibility, matched IDs, target deadlines, source raw hashes/level counts, gaps and missingness.
No new implementation; prior76D087 tests remain accepted, not rerun. Canonical/whitespace and
JSON/hash checks validate this evidence change. D085 prose previously copied4of110 from D082;
its immutable evidence actually records4of108 (1/27). No old protocol/data was rewritten.

Next action: read this evidence and PHASE_03_ONE_SIDED_NEXT.md. Do not rerun D089 or reinterpret
one-sided books as midpoint observations. Source data cannot retroactively supply the missing
three histories. Develop only the smallest prospective identity-bound observation refinement
needed to measure recovery from one-sided state; preserve failed pilots and all strict gates.
Phase4 stays in a fresh conversation after genuine full acceptance.

## D090 — one-sided diagnostic observation binding (2026-10-08)

Recovered unfinished D090 work after allowance interruption. New observation_binding reader
verifies original targeted identity/book computation while preserving null midpoint for one-sided
and empty books. Explicit socket binding_mode=observation selects a new v2 journal; default
v1 behavior stays strict. Freshness is rechecked at actual read/save/connect/subscription,
with all actual clocks, raw bytes, failure states and original-code recovery preserved.
No caller transport override, origin/history admission or continuity inference. Endpoint
comparison returns unavailable for an unavailable pre-quote instead of converting null to decimal.

34 targeted socket/binding/original-socket tests passed49.65s. Expanded analysis initially found
the null endpoint bug; after its fix51 binding/socket-analysis/endpoint/original-analysis tests
passed71.53s. Initial reader fixture import error corrected before these runs. Logs:
/tmp/arepo_d090b_tests.log and /tmp/arepo_d090d_tests.log. Explicit isolated /tmp SQLite,
AUTO_MIGRATE=false and disabled email. Ruff/backend, canonical and whitespace checks passed.
Self-review covered opt-in version/event consistency, unavailable arithmetic, legacy defaults,
source identity, fresh subscription and old evidence preservation. These are synthetic software
tests, not empirical Phase3 acceptance. No collector/test active before the next launch.

Next: execute once the committed PHASE_03_ONE_SIDED_DIAGNOSTIC_PROTOCOL.md; fixed three
D089 cases, six bounded HTTP reads, at most three60s subscriptions, all failures retained.
No full-frame redraw, retrospective D089 repair or production action. Then preserve measured
availability/coverage and decide the next prospective design from actual evidence.

D090 empirical diagnostic completed once under e8021098b19cb9d6d8651b14c378767ea54a2200,
2026-10-08 02:49:40–02:50:54UTC, exit0. Six HTTP requests,14188 raw bytes; two closed/nonaccepting
Gamma markets with book404, one active market with an observed one-sided book. The active case
completed60s, one book frame/five PONGs, no received two-sided recovery. Original book/socket/
analysis recovery passed;183 artifact hashes preserve519491bytes. Full result:
PHASE_03_ONE_SIDED_DIAGNOSTIC_EVIDENCE.json. No collector remains; D089 remains failed.
Legacy coverage labels the valid one-sided frame invalid_or_conflicting_message and60s uncovered.
Next D091: distinguish valid one-sided/empty state from malformed input in an explicitly versioned
receipt-coverage diagnostic, with zero midpoint/imbalance admission and unchanged legacy output.
Use synthetic transition tests plus read-only checksum-bound reanalysis; no new collection needed
for this parser distinction. Preserve D090's original analysis and never assert socket continuity.

## D091 — distinguish one-sided receipt state from malformed messages

Explicit window-coverage policy v2 is selected only for D090 observation sockets. Valid one-sided
or empty books retain exact side counts/state hash and replay lineage, while midpoint/imbalance
remain unavailable and the entire interval is uncovered until an actual two-sided update arrives.
Malformed/conflicting input still invalidates replay and requires a fresh full snapshot. PONGs
do not refresh any quote. Legacy policy v1 and its old numerical output remain unchanged.
59 targeted coverage/binding/socket-analysis/original-analysis cases passed39.56s, including
one-sided/empty states, delta recovery, side removal, malformed gaps, no invented history and
original-code recovery. Source formatting corrected afterward only; no behavior change.
Ruff/backend, canonical/whitespace checks pass. Self-review: explicit version selection, bounds,
state invalidation/recovery, exact receipt durations, all source/phase admission flags remainfalse.
Next perform checksum-bound retrospective reanalysis of D090 once under this committed code,
preserving its old analysis. No new external request or empirical acceptance is implied.


## D092 — explicit one-sided observation in the owned panel worker

Opt-in OwnedWindowPolicy.binding_mode=observation selects worker v7 and observation socketv2;
legacy quote mode retains worker v6 and its persisted policy shape. Verified one-sided/empty
pre-books can now be observed without filtering sampled members. The worker checks policy/socket
version consistency, current lifecycle/core identity and all existing acquisition/cold-replay
seals. Real source clocks, freshness, quotas, cancellation and original-code audits stay binding.
Origins still require actual eligible quotes; a two-sided frame received after an unavailable
pre-book never retroactively supplies its midpoint or an eligible price history.

24 affected owned_windows/window_context tests passed172.73s, including two complete synthetic
one-sided pilot variants (remains one-sided versus later two-sided), original runtime recovery,
unavailable histories, policy tamper rejection, legacy behavior, reservations, cancellation and
byte-seal mutation checks. Log /tmp/arepo_d092_tests.log; explicit isolated /tmp SQLite/emailoff.
One line was wrapped after tests for lint only. Ruff/backend, canonical and whitespace pass.
Self-review: explicit mode/version dispatch, legacy serialization, full missing-member accounting,
no history/continuity inference, authenticated dependency chain and unchanged capacity bounds.
No public run under D092, no Phase3 acceptance, no Phase4 or production action.

Next: PHASE_03_ONE_SIDED_NEXT.md current-state section. Reconcile remaining family eligibility
with measured source/selected-question evidence, then freeze a separately justified finite
prospective design before any new requests. Do not repeat D089/D090, weaken old6/8gates or
implement speculative services. Latest disk snapshot13915540KiB free; remeasure and reserve the
entire proposed run before launch. No test/collector remains active.


## D093/D094 — rule evidence and finite observation integration measurement

Verified all8 retained Gamma raw/receipt hashes and reviewed complete resolution descriptions.
France/Spain share identical tournament-winner rules; this is stronger than title matching,
but does not establish a complete outcome set or retroactive causal price binding. No sampled
rule matches the collected KNYC quantity. Explicit retrospective per-market record:
PHASE_03_FAMILY_ELIGIBILITY_REVIEW.json. External/related features remain unavailable; current
source rights and actual prospective observations would be required for any new admission.

D094 freezes one public attempt of the newly implemented owned observation mode, with all
D089 gates/budgets unchanged and a new complete observer-attempt accounting gate. Its reason
is validation of a changed data path, not another draw to obtain success. Exact script and
terminal/no-repeat rule: PHASE_03_OBSERVATION_PILOT_PROTOCOL.md. Self-review: mode selected
explicitly, complete-frame prerequisites, exact probabilities, exclusive roots, full reserve,
causal clocks, original audit, missing-history distinction and no protected changes. No code
changed; D09224 tests stay accepted. Syntax/API/canonical/whitespace checks apply to this plan.


## D094 terminal evidence — October8

Single attempt under53c19a43d9784e7f98a41e22131799f5a63b7e1f completed08:33:57.532132UTC,
exit0, full original-code audit passed. Complete frame267180 distinct/267136 mapped/44unresolved;
2672requests, no retries/errors/conflicts, source interval531.668300s, raw1722038541bytes,
retained4220053077bytes. Four of109 strata sampled (4/109) with exact conditional weights.
Eight scheduled/one triggered/one matched control roles over eight markets; zero unfilled
control slots. Five observed origins/five eligible completed histories/five valid targets.
Both six-of-eight gates FAIL. Original audit, observer-attempt accounting, matched control,
target coverage, origin clocks and reporting pass. Phase3 remains incomplete.

50HTTPrequests:21Gamma200,17book200,4book404,8taker-trade200;142618raw bytes. Six subscriptions
completed their10s intervals. TyroneTracy market3400453 remained one-sided (0bids/20asks at
pre-read); coverage0. Five other windows have bounded receipt coverage (four1s, one1.068165750s).
Two Bitcoin markets5424711/5424716 are closed/nonaccepting with book404; their specified08:00UTC
candle was already past before this frame's08:02:40 start. All eight remain in the denominator.
One-sided deltas reported best_bid0 against an empty bid side and were conservatively marked
conflicting; do not silently reinterpret0 as an empty-side sentinel or invent a prior quote.

PHASE_03_OBSERVATION_PILOT_EVIDENCE.json preserves full manifests, exact timing/numerics,
321 independently checked artifacts, source receipts/raw hashes, all8resolution descriptions,
extractor scripts and gate results. Related Bitcoin thresholds share a candle rule, but no
pre-origin related-price input was bound. Sports/Bitcoin quantities do not match KNYC weather.
No new external source rights/admission; unsupported families and v1 components stay unavailable.
Self-review checked exact sampling products, all denominators, source failures, actual clock
ordering, observed matched IDs, target selection, original recovery and no retrospective repair.
Evidence-only change: no accepted code tests repeated; JSON/hash checks and canonical/whitespace
checks pass. No collector/test active, production/retention untouched, Phase4 not started.

BLOCKED — CAPACITY AND REQUIRED EMPIRICAL DATA UNAVAILABLE for another full measurement at
current bounds. Free9511227392bytes versus required13308526592 (short3797299200bytes).
No repeated draw, source-universe narrowing, destructive cleanup, paid/production storage or
missing-history manufacture is an acceptable workaround. Preserve this failed run. A future
protocol must first reconcile sampling-time lifecycle/close eligibility with its intended
population while retaining the complete discovery inventory and all old denominators; it may
not merely redraw until6/8passes. Then remeasure/reserve capacity before collection.

Exact next action: recheck capacity once on continuation. If unchanged, stop quietly without
new commits/tests/collection. After capacity is available, review that temporal-eligibility
question against current sampling/metadata code and raw frame evidence before designing any
separate prospective attempt. Do not rerun D094. Any additional storage/deletion or production
change requires its own applicable authorisation; no such approval is implied here.
