# RollCall EODA — Dual attendance and operations specification

Status: implementation planning; NOT production verified.

## Existing application
The current main branch contains a single large index.html with embedded organization logos. Preserve existing appearance, branding, data and flows. Audit actual functions and storage before editing.

## Attendance model
- An event has id, title, type (training, meeting, exercise, operation), start/end, status and attendance policy.
- An attendance record has event_id, member_id, source (self/leader), check_in_at, check_out_at, verification status, verifier, audit timestamps.
- Unique (event_id, member_id) for active attendance; preserve history of corrections in an append-only audit.
- Self check-in requires authenticated member identity. Leader entry requires role authorization and records actor and reason.
- All attendance writes must be validated server-side; never trust a client-provided role or member ID.
- Repeated requests should be idempotent, with safe retry behavior.

## Operation-specific accountability
- Operation: open, active, reconciliation, closed.
- Per-member states: expected, reported, leader-confirmed, deployed, returned, unresolved.
- A member reporting attendance is NOT equivalent to being verified safe.
- The operation cannot be silently closed with unresolved personnel; an authorized leader may record an explicit exception with justification and audit.
- Keep manual headcount and fallback procedures; this application is not a life-safety system.

## Offline behavior
- Queue authenticated, timestamped events locally with stable IDs.
- Show offline/pending/synced/conflict status clearly; do not display pending local writes as globally confirmed.
- Server resolves conflicts and returns explicit reconciliation outcome.
- Test loss of connectivity and duplicate retries on Android/iOS.

## Privacy and administration
- Minimal personal information, role-based access, retention policy and backups.
- No continuous GPS tracking.
- Export CSV/Excel with authorization and data minimization.
- Separate member and leader interfaces.

## Acceptance tests
1. Member self check-in and leader check-in for same event cannot create duplicates.
2. Unauthorized member cannot register another person.
3. Leader edits are audited.
4. Offline entries synchronize once, with visible conflicts.
5. Open operation shows expected/reported/confirmed/deployed/returned/unresolved separately.
6. Closeout handles missing members explicitly.
7. Legacy features, logos and historical records remain intact.
8. Verify on mobile and desktop.

## Delivery order
1. Inventory existing JS functions, data persistence, hosting, login and export.
2. Implement minimal backward-compatible changes behind feature flags.
3. Add automated tests and manual multi-device pilot.
4. Deploy only after review and verified backup.
