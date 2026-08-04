"use client";

import { useCallback, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  deleteAccount,
  getAlertHistory,
  getPreferences,
  getSavedMarkets,
  unsaveMarket,
  updatePreferences,
} from "@/lib/api";
import type { AlertDelivery, AlertPreferences, SavedMarket } from "@/lib/types";
import { PageHeader, SectionTitle } from "@/components/ui";
import { FormMessage, TextLink } from "@/components/account/AuthUI";

export default function AccountPage() {
  const { user, loading, signOut } = useAuth();
  const router = useRouter();

  if (loading) return <p className="text-arepo-muted">Loading…</p>;
  if (!user) {
    return (
      <div className="mx-auto max-w-md text-center">
        <PageHeader title="Account" lead="Sign in to manage your alerts and saved markets." />
        <TextLink href="/signin">Sign in</TextLink>{" "}or{" "}
        <TextLink href="/signup">create a free account</TextLink>.
      </div>
    );
  }

  return (
    <div className="space-y-10">
      <PageHeader
        title="Your account"
        lead="Manage your research alerts, the markets you follow, and your account."
      />
      <ProfileSection
        email={user.email}
        verified={user.is_verified}
        onSignOut={async () => {
          await signOut();
          router.push("/");
        }}
      />
      <PreferencesSection />
      <SavedSection />
      <HistorySection />
      <DangerSection
        onDeleted={async () => {
          await signOut();
          router.push("/");
        }}
      />
    </div>
  );
}

function ProfileSection({
  email,
  verified,
  onSignOut,
}: {
  email: string;
  verified: boolean;
  onSignOut: () => void;
}) {
  return (
    <section>
      <SectionTitle>Profile</SectionTitle>
      <div className="mt-3 flex flex-wrap items-center justify-between gap-3 rounded-card border border-arepo-border bg-arepo-surface p-4">
        <div className="text-[14px]">
          <div className="font-medium text-arepo-ink">{email}</div>
          <div className="text-[13px] text-arepo-muted">
            {verified ? "Email verified" : "Email not yet verified"}
          </div>
        </div>
        <button
          type="button"
          onClick={onSignOut}
          className="focus-ring rounded-md border border-arepo-border px-3 py-1.5 text-[13px] font-medium text-arepo-ink hover:bg-arepo-surface2"
        >
          Sign out
        </button>
      </div>
    </section>
  );
}

const CATEGORY_OPTIONS = ["Politics", "Sports", "Crypto", "Economics", "Culture", "Science"];

function PreferencesSection() {
  const [prefs, setPrefs] = useState<AlertPreferences | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    getPreferences()
      .then(setPrefs)
      .catch((e) => setError(e instanceof Error ? e.message : "Could not load preferences."));
  }, []);

  const patch = useCallback((changes: Partial<AlertPreferences>) => {
    setPrefs((p) => (p ? { ...p, ...changes } : p));
    setSaved(false);
  }, []);

  async function save() {
    if (!prefs) return;
    setPending(true);
    setError("");
    try {
      const updated = await updatePreferences({
        email_enabled: prefs.email_enabled,
        immediate_exceptional: prefs.immediate_exceptional,
        daily_digest: prefs.daily_digest,
        weekly_summary: prefs.weekly_summary,
        min_research_priority: prefs.min_research_priority,
        min_confidence: prefs.min_confidence,
        categories: prefs.categories,
        short_term_only: prefs.short_term_only,
        max_hours_to_close: prefs.max_hours_to_close,
        paused: prefs.paused,
        unsubscribed: prefs.unsubscribed,
      });
      setPrefs(updated);
      setSaved(true);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not save preferences.");
    } finally {
      setPending(false);
    }
  }

  if (!prefs) {
    return (
      <section>
        <SectionTitle>Alert settings</SectionTitle>
        <FormMessage tone="error">{error}</FormMessage>
      </section>
    );
  }

  return (
    <section>
      <SectionTitle>Alert settings</SectionTitle>
      <p className="mt-1 text-[13px] text-arepo-muted">
        Alerts are opt-in and only ever go to a verified email. They are statistical research
        signals, not financial advice.
      </p>
      <div className="mt-4 space-y-4 rounded-card border border-arepo-border bg-arepo-surface p-5">
        {error && <FormMessage tone="error">{error}</FormMessage>}
        {saved && <FormMessage tone="ok">Preferences saved.</FormMessage>}

        <Toggle
          label="Email alerts enabled"
          hint="The master switch. When off, Arepo sends you nothing."
          checked={prefs.email_enabled}
          onChange={(v) => patch({ email_enabled: v })}
        />
        <Toggle
          label="Immediate high-priority alerts"
          hint="Email me when an exceptional, high-priority opportunity appears."
          checked={prefs.immediate_exceptional}
          onChange={(v) => patch({ immediate_exceptional: v })}
        />
        <Toggle
          label="Daily digest"
          checked={prefs.daily_digest}
          onChange={(v) => patch({ daily_digest: v })}
        />
        <Toggle
          label="Weekly summary"
          checked={prefs.weekly_summary}
          onChange={(v) => patch({ weekly_summary: v })}
        />

        <Slider
          label="Minimum Research Priority"
          hint="Only alert me on markets scoring at least this (0-100)."
          min={0}
          max={100}
          step={5}
          value={prefs.min_research_priority}
          onChange={(v) => patch({ min_research_priority: v })}
        />
        <Slider
          label="Minimum confidence"
          hint="Only alert me when the reliability confidence (data quality x evidence corroboration) is at least this high."
          min={0}
          max={100}
          step={5}
          value={Math.round(prefs.min_confidence * 100)}
          onChange={(v) => patch({ min_confidence: v / 100 })}
          suffix="%"
        />

        <Toggle
          label="Short-term opportunities only"
          hint="Prefer markets closing soon."
          checked={prefs.short_term_only}
          onChange={(v) => patch({ short_term_only: v })}
        />
        {prefs.short_term_only && (
          <Slider
            label="Maximum time to close (hours)"
            min={6}
            max={168}
            step={6}
            value={prefs.max_hours_to_close ?? 168}
            onChange={(v) => patch({ max_hours_to_close: v })}
            suffix="h"
          />
        )}

        <fieldset>
          <legend className="mb-1 text-[13px] font-medium text-arepo-ink2">
            Preferred categories
          </legend>
          <p className="mb-2 text-[12px] text-arepo-muted">
            Leave all unchecked to receive alerts from every category.
          </p>
          <div className="flex flex-wrap gap-2">
            {CATEGORY_OPTIONS.map((cat) => {
              const on = prefs.categories.includes(cat);
              return (
                <button
                  key={cat}
                  type="button"
                  aria-pressed={on}
                  onClick={() =>
                    patch({
                      categories: on
                        ? prefs.categories.filter((c) => c !== cat)
                        : [...prefs.categories, cat],
                    })
                  }
                  className={`focus-ring rounded-full border px-3 py-1 text-[12.5px] font-medium ${
                    on
                      ? "border-arepo-accent bg-arepo-accentTint text-arepo-accentActive"
                      : "border-arepo-border text-arepo-muted hover:text-arepo-ink"
                  }`}
                >
                  {cat}
                </button>
              );
            })}
          </div>
        </fieldset>

        <Toggle
          label="Pause all alerts"
          hint="Temporarily stop alerts without changing your other settings."
          checked={prefs.paused}
          onChange={(v) => patch({ paused: v })}
        />
        <Toggle
          label="Unsubscribe from all emails"
          hint="A hard opt-out. You will receive nothing until you turn this off."
          checked={prefs.unsubscribed}
          onChange={(v) => patch({ unsubscribed: v })}
        />

        <button
          type="button"
          onClick={save}
          disabled={pending}
          className="focus-ring inline-flex items-center justify-center rounded-md bg-arepo-accent px-4 py-2 text-[14px] font-semibold text-white hover:bg-arepo-accentHover disabled:opacity-60"
        >
          {pending ? "Saving…" : "Save preferences"}
        </button>
      </div>
    </section>
  );
}

function Toggle({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <label className="flex items-start justify-between gap-4">
      <span>
        <span className="block text-[14px] font-medium text-arepo-ink">{label}</span>
        {hint && <span className="block text-[12px] text-arepo-muted">{hint}</span>}
      </span>
      <input
        type="checkbox"
        checked={checked}
        onChange={(e) => onChange(e.target.checked)}
        className="focus-ring mt-1 h-4 w-4 flex-none"
      />
    </label>
  );
}

function Slider({
  label,
  hint,
  min,
  max,
  step,
  value,
  onChange,
  suffix,
}: {
  label: string;
  hint?: string;
  min: number;
  max: number;
  step: number;
  value: number;
  onChange: (v: number) => void;
  suffix?: string;
}) {
  return (
    <label className="block">
      <span className="flex items-center justify-between">
        <span className="text-[14px] font-medium text-arepo-ink">{label}</span>
        <span className="font-tabular text-[13px] text-arepo-ink2">
          {value}
          {suffix ?? ""}
        </span>
      </span>
      {hint && <span className="mb-1 block text-[12px] text-arepo-muted">{hint}</span>}
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="focus-ring mt-1 w-full accent-arepo-accent"
      />
    </label>
  );
}

function SavedSection() {
  const [saved, setSaved] = useState<SavedMarket[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getSavedMarkets()
      .then(setSaved)
      .catch(() => setSaved([]))
      .finally(() => setLoaded(true));
  }, []);

  async function remove(id: string) {
    await unsaveMarket(id);
    setSaved((s) => s.filter((m) => m.market_id !== id));
  }

  return (
    <section>
      <SectionTitle>Saved markets</SectionTitle>
      {loaded && saved.length === 0 && (
        <p className="mt-2 text-[13px] text-arepo-muted">
          You have not saved any markets yet. Open a market and choose Save to follow it.
        </p>
      )}
      <ul className="mt-3 space-y-2">
        {saved.map((m) => (
          <li
            key={m.market_id}
            className="flex items-center justify-between gap-3 rounded-md border border-arepo-border bg-arepo-surface px-4 py-2"
          >
            <Link
              href={`/markets/${encodeURIComponent(m.market_id)}`}
              className="focus-ring text-[14px] font-medium text-arepo-ink hover:text-arepo-accentActive"
            >
              {m.question || m.market_id}
            </Link>
            <button
              type="button"
              onClick={() => remove(m.market_id)}
              className="focus-ring text-[13px] text-arepo-muted hover:text-arepo-warnText"
            >
              Remove
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

function HistorySection() {
  const [items, setItems] = useState<AlertDelivery[]>([]);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    getAlertHistory()
      .then(setItems)
      .catch(() => setItems([]))
      .finally(() => setLoaded(true));
  }, []);

  return (
    <section>
      <SectionTitle>Recent alerts</SectionTitle>
      {loaded && items.length === 0 && (
        <p className="mt-2 text-[13px] text-arepo-muted">
          No alerts have been sent to you yet.
        </p>
      )}
      <ul className="mt-3 space-y-2">
        {items.map((a, i) => (
          <li
            key={`${a.market_id}-${i}`}
            className="rounded-md border border-arepo-border bg-arepo-surface px-4 py-2 text-[13px]"
          >
            <div className="flex items-center justify-between gap-3">
              <span className="font-medium text-arepo-ink">{a.subject || a.market_id}</span>
              <span className="text-arepo-muted">{new Date(a.at).toLocaleString("en-GB")}</span>
            </div>
            <div className="text-[12px] text-arepo-muted">
              {a.status}
              {a.detail ? ` · ${a.detail}` : ""}
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}

function DangerSection({ onDeleted }: { onDeleted: () => void }) {
  const [confirming, setConfirming] = useState(false);
  const [pending, setPending] = useState(false);

  async function remove() {
    setPending(true);
    try {
      await deleteAccount();
      onDeleted();
    } finally {
      setPending(false);
    }
  }

  return (
    <section>
      <SectionTitle>Delete account</SectionTitle>
      <p className="mt-1 text-[13px] text-arepo-muted">
        This permanently deletes your account, preferences, saved markets and alert history. It
        cannot be undone.
      </p>
      {confirming ? (
        <div className="mt-3 flex items-center gap-3">
          <button
            type="button"
            onClick={remove}
            disabled={pending}
            className="focus-ring rounded-md border border-arepo-warn/40 bg-arepo-warn/10 px-3 py-1.5 text-[13px] font-medium text-arepo-warnText disabled:opacity-60"
          >
            {pending ? "Deleting…" : "Yes, delete my account"}
          </button>
          <button
            type="button"
            onClick={() => setConfirming(false)}
            className="focus-ring text-[13px] text-arepo-muted hover:text-arepo-ink"
          >
            Cancel
          </button>
        </div>
      ) : (
        <button
          type="button"
          onClick={() => setConfirming(true)}
          className="focus-ring mt-3 rounded-md border border-arepo-border px-3 py-1.5 text-[13px] font-medium text-arepo-warnText hover:bg-arepo-surface2"
        >
          Delete my account
        </button>
      )}
    </section>
  );
}
