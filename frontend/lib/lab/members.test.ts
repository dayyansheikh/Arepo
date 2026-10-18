import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it, vi } from "vitest";
import {
  ACTION_COPY,
  applyLocally,
  auditSentence,
  availableActions,
  dataSummary,
  emailMatches,
  filterCounts,
  filterMembers,
  loadMembers,
  MEMBERS_SIGNIN_REDIRECT,
  requestFor,
  runMemberAction,
  type Member,
  type MemberActionKind,
} from "./members";
import { buildMembersFixture } from "./members-fixture";

function res(status: number, body?: unknown): Response {
  return new Response(body === undefined ? null : JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  });
}

const base: Member = {
  id: "u1",
  email: "m@example.com",
  first_name: "Ada",
  last_name: "Lovelace",
  is_active: true,
  is_verified: true,
  is_superuser: false,
  created_at: "2026-10-01T00:00:00+00:00",
  data: {},
};
const ME = "me";

describe("loading", () => {
  it("sends the session cookie to both endpoints and returns users, me and audit", async () => {
    const fetchImpl = vi.fn(async (url: string) =>
      url.endsWith("/users") ? res(200, { users: [base], me: ME }) : res(200, { entries: [] }),
    );
    const out = await loadMembers(fetchImpl);
    expect(out).toEqual({ kind: "ok", data: { users: [base], me: ME, audit: [] } });
    expect(fetchImpl).toHaveBeenCalledTimes(2);
    for (const call of fetchImpl.mock.calls as unknown as Array<[string, RequestInit]>) {
      expect(call[1].credentials).toBe("include");
      expect(call[1].method).toBe("GET");
    }
  });

  it("maps 401 to unauthorized and 404 to not_found", async () => {
    expect(await loadMembers(async () => res(401))).toEqual({ kind: "unauthorized" });
    expect(await loadMembers(async () => res(404, { detail: "Not Found" }))).toEqual({ kind: "not_found" });
    expect(MEMBERS_SIGNIN_REDIRECT).toBe("/signin?next=/lab/members");
  });

  it("reports network failures and server errors without throwing", async () => {
    const down = await loadMembers(async () => {
      throw new TypeError("network");
    });
    expect(down.kind).toBe("error");
    const bad = await loadMembers(async () => res(500, { detail: "boom" }));
    expect(bad).toEqual({ kind: "error", status: 500, message: "boom" });
  });
});

describe("actions", () => {
  it("maps every action to the right request", () => {
    expect(requestFor("password_reset", "u1")).toEqual({ method: "POST", path: "/api/lab/admin/users/u1/password-reset" });
    expect(requestFor("verification_email", "u1").path).toBe("/api/lab/admin/users/u1/verification-email");
    expect(requestFor("verify", "u1").path).toBe("/api/lab/admin/users/u1/verify");
    expect(requestFor("suspend", "u1").path).toBe("/api/lab/admin/users/u1/suspend");
    expect(requestFor("restore", "u1").path).toBe("/api/lab/admin/users/u1/restore");
    expect(requestFor("admin_grant", "u1", "m@example.com")).toEqual({
      method: "POST",
      path: "/api/lab/admin/users/u1/admin",
      body: { grant: true, confirm_email: "m@example.com" },
    });
    expect(requestFor("admin_revoke", "u1", "x").body).toEqual({ grant: false, confirm_email: "x" });
    expect(requestFor("delete", "u1", "m@example.com")).toEqual({
      method: "DELETE",
      path: "/api/lab/admin/users/u1",
      body: { confirm_email: "m@example.com" },
    });
  });

  it("posts JSON with credentials and surfaces server messages", async () => {
    const fetchImpl = vi.fn(async () => res(200, { id: "u1" }));
    expect(await runMemberAction("delete", "u1", "m@example.com", fetchImpl)).toEqual({ ok: true });
    const [url, init] = fetchImpl.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toContain("/api/lab/admin/users/u1");
    expect(init.method).toBe("DELETE");
    expect(init.credentials).toBe("include");
    expect((init.headers as Record<string, string>)["Content-Type"]).toBe("application/json");
    expect(JSON.parse(init.body as string)).toEqual({ confirm_email: "m@example.com" });

    const conflict = await runMemberAction("suspend", "u1", "", async () => res(409, { detail: "You can't suspend your own account." }));
    expect(conflict).toEqual({ ok: false, status: 409, message: "You can't suspend your own account." });
    const limited = await runMemberAction("password_reset", "u1", "", async () => res(429, { detail: "Too many emails sent this hour. Try again later." }));
    expect(limited.ok).toBe(false);
    if (!limited.ok) expect(limited.message).toMatch(/Too many/);
    const expired = await runMemberAction("verify", "u1", "", async () => res(401));
    expect(expired).toMatchObject({ ok: false, status: 401, unauthorized: true });
  });
});

describe("available actions mirror the API guards", () => {
  const kinds = (m: Member, me = ME) => availableActions(m, me);

  it("offers reset, grant, suspend and delete for an ordinary verified member", () => {
    expect(kinds(base)).toEqual(["password_reset", "admin_grant", "suspend", "delete"]);
  });

  it("offers verification and no admin grant for an unverified member", () => {
    const k = kinds({ ...base, is_verified: false });
    expect(k).toContain("verification_email");
    expect(k).toContain("verify");
    expect(k).not.toContain("admin_grant");
  });

  it("offers restore (not reset or grant) for a suspended member", () => {
    const k = kinds({ ...base, is_active: false });
    expect(k).toContain("restore");
    expect(k).not.toContain("password_reset");
    expect(k).not.toContain("suspend");
    expect(k).not.toContain("admin_grant");
  });

  it("never offers suspend, delete or revoke on yourself", () => {
    const k = kinds({ ...base, id: ME, is_superuser: true });
    expect(k).toEqual(["password_reset"]);
  });

  it("requires revoking admin before suspend/delete of another admin", () => {
    const k = kinds({ ...base, is_superuser: true });
    expect(k).toEqual(["password_reset", "admin_revoke"]);
  });

  it("requires typed email for delete and admin changes only", () => {
    const typed = (Object.keys(ACTION_COPY) as MemberActionKind[]).filter((k) => ACTION_COPY[k].typed);
    expect(typed.sort()).toEqual(["admin_grant", "admin_revoke", "delete"]);
  });

  it("matches typed emails case-insensitively and rejects empty input", () => {
    expect(emailMatches(" M@Example.com ", "m@example.com")).toBe(true);
    expect(emailMatches("m@example.co", "m@example.com")).toBe(false);
    expect(emailMatches("", "")).toBe(false);
  });
});

describe("list helpers", () => {
  const fixture = buildMembersFixture(Date.parse("2026-10-19T12:00:00Z"));

  it("filters by status and searches name and email", () => {
    const users = fixture.users;
    expect(filterMembers(users, "", "admins").every((u) => u.is_superuser)).toBe(true);
    expect(filterMembers(users, "", "suspended").every((u) => !u.is_active)).toBe(true);
    expect(filterMembers(users, "PATEL", "all").map((u) => u.email)).toEqual(["sam.research@example.com"]);
    expect(filterMembers(users, "example.org", "all")).toHaveLength(1);
    const c = filterCounts(users);
    expect(c.all).toBe(users.length);
    expect(c.admins).toBe(2);
    expect(c.unverified).toBe(1);
    expect(c.suspended).toBe(1);
  });

  it("summarises saved data in plain words", () => {
    expect(dataSummary({})).toBe("No saved data");
    expect(dataSummary(undefined)).toBe("No saved data");
    expect(dataSummary({ saved_markets: 1, alert_preferences: 1, digest_deliveries: 3 })).toBe(
      "1 saved market · alert settings · 3 digests",
    );
  });

  it("writes audit sentences", () => {
    expect(
      auditSentence({
        id: 1,
        at: null,
        actor_user_id: "a",
        actor_email: "owner@example.com",
        action: "admin_grant",
        target_user_id: "b",
        target_email: "m@example.com",
        detail: null,
      }),
    ).toBe("owner@example.com made admin m@example.com");
  });

  it("applies simulated fixture actions locally", () => {
    const users = [base];
    expect(applyLocally(users, "suspend", "u1")[0].is_active).toBe(false);
    expect(applyLocally(users, "admin_grant", "u1")[0].is_superuser).toBe(true);
    expect(applyLocally(users, "delete", "u1")).toEqual([]);
  });
});

describe("production safety", () => {
  it("only loads the members fixture behind the literal NODE_ENV guard and fixtureAllowed()", () => {
    const src = readFileSync(resolve(__dirname, "use-members.ts"), "utf8");
    const guard = src.indexOf('process.env.NODE_ENV !== "production"');
    const imp = src.indexOf('import("./members-fixture")');
    expect(guard).toBeGreaterThan(-1);
    expect(imp).toBeGreaterThan(guard);
    expect(src).toContain("fixtureAllowed(process.env.NODE_ENV, window.location.search)");
    expect(src).not.toMatch(/^import .*members-fixture/m);
  });

  it("never uses browser alert/confirm dialogs on the members page", () => {
    for (const f of ["../../components/lab/MembersAdmin.tsx", "../../components/lab/MemberRow.tsx"]) {
      const src = readFileSync(resolve(__dirname, f), "utf8");
      expect(src).not.toMatch(/\b(window\.)?(alert|confirm|prompt)\(/);
    }
  });
});
