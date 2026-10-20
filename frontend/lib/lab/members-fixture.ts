// Dev-only fixture for the Members page (screenshots / visual work). Loaded only behind the same
// guard as the Lab fixture (non-production build AND ?fixture=1); never part of production data.
import type { AuditEntry, Member, MembersSnapshot } from "./members";

const ME = "00000000-0000-4000-8000-000000000001";

export function buildMembersFixture(nowMs: number): MembersSnapshot {
  const ago = (days: number) => new Date(nowMs - days * 86_400_000).toISOString();
  const mins = (m: number) => new Date(nowMs - m * 60_000).toISOString();
  const users: Member[] = [
    { id: ME, email: "owner@example.com", first_name: "Olivia", last_name: "Owner", is_active: true, is_verified: true, is_superuser: true, created_at: ago(240), data: { alert_preferences: 1, saved_markets: 12, alert_deliveries: 48, digest_deliveries: 30 } },
    { id: "00000000-0000-4000-8000-000000000002", email: "sam.research@example.com", first_name: "Sam", last_name: "Patel", is_active: true, is_verified: true, is_superuser: false, created_at: ago(61), data: { alert_preferences: 1, saved_markets: 4, alert_deliveries: 9, digest_deliveries: 6 } },
    { id: "00000000-0000-4000-8000-000000000003", email: "newcomer@example.org", first_name: "Jun", last_name: "Lee", is_active: true, is_verified: false, is_superuser: false, created_at: ago(1), data: {} },
    { id: "00000000-0000-4000-8000-000000000004", email: "alex.w@example.net", first_name: "Alex", last_name: "Wright", is_active: false, is_verified: true, is_superuser: false, created_at: ago(120), data: { alert_preferences: 1, saved_markets: 2 } },
    { id: "00000000-0000-4000-8000-000000000005", email: "maria.collaborator.with.a.long.address@example.com", first_name: "Maria", last_name: "Gonzalez", is_active: true, is_verified: true, is_superuser: true, created_at: ago(90), data: { alert_preferences: 1, saved_markets: 7, digest_deliveries: 14 } },
    { id: "00000000-0000-4000-8000-000000000006", email: "legacy-user@example.com", first_name: null, last_name: null, is_active: true, is_verified: true, is_superuser: false, created_at: ago(300), data: { saved_markets: 1 } },
  ];
  const audit: AuditEntry[] = [
    { id: 4, at: mins(12), actor_user_id: ME, actor_email: "owner@example.com", action: "verification_email", target_user_id: users[2].id, target_email: users[2].email, detail: null },
    { id: 3, at: mins(190), actor_user_id: ME, actor_email: "owner@example.com", action: "suspend", target_user_id: users[3].id, target_email: users[3].email, detail: null },
    { id: 2, at: ago(3), actor_user_id: ME, actor_email: "owner@example.com", action: "admin_grant", target_user_id: users[4].id, target_email: users[4].email, detail: null },
    { id: 1, at: ago(9), actor_user_id: ME, actor_email: "owner@example.com", action: "delete", target_user_id: "00000000-0000-4000-8000-000000000099", target_email: "s***@example.com", detail: '{"removed": {"alert_deliveries": 0, "alert_preferences": 0, "digest_deliveries": 0, "saved_markets": 0}}' },
  ];
  return { users, me: ME, audit };
}
