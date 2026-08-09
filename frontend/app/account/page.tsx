"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { digestEvaluationLabel } from "@/lib/account";
import { useAuth } from "@/lib/auth-context";
import {
  deleteAccount,
  getDigestDetail,
  getDigestHistory,
  getPreferences,
  updatePreferences,
} from "@/lib/api";
import type {
  AlertPreferences,
  DigestDetail,
  DigestSummary,
} from "@/lib/types";
import { PageHeader } from "@/components/ui";
import { FormMessage, TextLink } from "@/components/account/AuthUI";

type AccountTab = "digests" | "preferences";

const CATEGORY_OPTIONS = [
  "Geopolitics / War",
  "Economics / Macro",
  "Commodities",
  "Politics / Elections",
  "Crypto",
  "Technology / Business",
  "Sports",
  "Entertainment / Culture",
  "Other",
] as const;

const FREQUENCIES: Array<{
  value: AlertPreferences["digest_frequency"];
  label: string;
}> = [
  { value: "off", label: "Off" },
  { value: "every_6h", label: "Every 6 hours" },
  { value: "daily", label: "Once daily" },
  { value: "twice_daily", label: "Twice daily" },
  { value: "weekly", label: "Weekly" },
];

export default function AccountPage() {
  const { user, loading, signOut } = useAuth();
  const router = useRouter();
  const [tab, setTab] = useState<AccountTab>("digests");

  useEffect(() => {
    const requested = new URLSearchParams(window.location.search).get("tab");
    if (requested === "preferences") setTab("preferences");
  }, []);

  function chooseTab(next: AccountTab) {
    setTab(next);
    const query = next === "preferences" ? "?tab=preferences" : "";
    window.history.replaceState(null, "", `/account${query}`);
  }

  if (loading) return <p className="text-arepo-muted">Loading…</p>;
  if (!user) {
    return (
      <div className="mx-auto max-w-md text-center">
        <PageHeader title="Account" lead="Sign in to review your digests and preferences." />
        <TextLink href="/signin">Sign in</TextLink>{" "}or{" "}
        <TextLink href="/signup">create a free account</TextLink>.
      </div>
    );
  }

  const name = [user.first_name, user.last_name].filter(Boolean).join(" ");
  return (
    <div className="mx-auto max-w-3xl space-y-7">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <PageHeader title={name || "Your account"} lead={user.email} />
        <div className="flex items-center gap-3 text-[13px]">
          <Link href="/forgot" className="focus-ring text-arepo-muted underline hover:text-arepo-ink">
            Reset password
          </Link>
          <button
            type="button"
            onClick={async () => {
              try {
                await signOut();
              } finally {
                router.push("/");
              }
            }}
            className="focus-ring rounded-md border border-arepo-border px-3 py-1.5 font-medium text-arepo-ink hover:bg-arepo-surface2"
          >
            Sign out
          </button>
        </div>
      </div>

      <div role="tablist" aria-label="Account" className="flex border-b border-arepo-border">
        <TabButton active={tab === "digests"} onClick={() => chooseTab("digests")}>
          Your digests
        </TabButton>
        <TabButton active={tab === "preferences"} onClick={() => chooseTab("preferences")}>
          Preferences
        </TabButton>
      </div>

      {tab === "digests" ? <DigestsTab /> : <PreferencesTab onDeleted={() => router.push("/")} />}
    </div>
  );
}

function TabButton({
  active,
  onClick,
  children,
}: {
  active: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      role="tab"
      aria-selected={active}
      onClick={onClick}
      className={`focus-ring -mb-px border-b-2 px-4 py-3 text-[14px] font-semibold ${
        active
          ? "border-arepo-accent text-arepo-ink"
          : "border-transparent text-arepo-muted hover:text-arepo-ink"
      }`}
    >
      {children}
    </button>
  );
}

function DigestsTab() {
  const [items, setItems] = useState<DigestSummary[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [openId, setOpenId] = useState<number | null>(null);
  const [detail, setDetail] = useState<DigestDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  async function load(offset: number) {
    setError("");
    try {
      const page = await getDigestHistory(20, offset);
      setItems((current) => (offset === 0 ? page.items : [...current, ...page.items]));
      setHasMore(page.has_more);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load your digests.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load(0);
  }, []);

  async function toggle(item: DigestSummary) {
    if (openId === item.id) {
      setOpenId(null);
      setDetail(null);
      return;
    }
    setOpenId(item.id);
    setDetail(null);
    setDetailLoading(true);
    try {
      setDetail(await getDigestDetail(item.id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not open this digest.");
    } finally {
      setDetailLoading(false);
    }
  }

  if (loading) return <p className="text-[14px] text-arepo-muted">Loading your digests…</p>;
  return (
    <section role="tabpanel" aria-label="Your digests" className="space-y-3">
      {error && <FormMessage tone="error">{error}</FormMessage>}
      {items.length === 0 ? (
        <div className="rounded-card border border-arepo-border bg-arepo-surface p-6">
          <h2 className="font-display text-lg font-semibold text-arepo-ink">No digests yet</h2>
          <p className="mt-1 text-[14px] text-arepo-muted">
            When Arepo sends your first signal digest, it will appear here.
          </p>
        </div>
      ) : (
        items.map((item) => (
          <div key={item.id} className="rounded-card border border-arepo-border bg-arepo-surface">
            <button
              type="button"
              aria-expanded={openId === item.id}
              onClick={() => void toggle(item)}
              className="focus-ring flex w-full items-center justify-between gap-4 rounded-card px-5 py-4 text-left"
            >
              <span>
                <span className="block font-display text-[16px] font-semibold text-arepo-ink">
                  {formatDigestDay(item.sent_at)}
                </span>
                <span className="mt-0.5 block text-[12px] text-arepo-muted">
                  {formatDigestTime(item.sent_at)} · {item.signal_count}{" "}
                  {item.signal_count === 1 ? "opportunity" : "opportunities"}
                </span>
              </span>
              <span aria-hidden="true" className="text-arepo-muted">
                {openId === item.id ? "−" : "+"}
              </span>
            </button>
            {openId === item.id && (
              <div className="border-t border-arepo-border px-5 py-4">
                {detailLoading && <p className="text-[13px] text-arepo-muted">Loading…</p>}
                {detail && detail.id === item.id && <DigestEntries detail={detail} />}
              </div>
            )}
          </div>
        ))
      )}
      {hasMore && (
        <button
          type="button"
          onClick={() => void load(items.length)}
          className="focus-ring rounded-md border border-arepo-border px-3 py-2 text-[13px] font-medium text-arepo-ink hover:bg-arepo-surface2"
        >
          Load older digests
        </button>
      )}
    </section>
  );
}

function DigestEntries({ detail }: { detail: DigestDetail }) {
  return (
    <div className="space-y-3">
      {detail.entries.map((entry) => (
        <article key={`${entry.market_id}-${entry.token_id}`} className="rounded-md bg-arepo-surface2 p-4">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0 flex-1">
              <Link
                href={entry.canonical_url}
                className="focus-ring font-medium text-arepo-ink hover:text-arepo-accentActive"
              >
                {entry.market_question}
              </Link>
              <p className="mt-1 text-[12px] text-arepo-muted">{entry.category}</p>
            </div>
            <span className="text-[12px] font-medium text-arepo-ink2">
              {entry.outcome_name || "Outcome"} repricing {entry.direction === "up" ? "higher" : "lower"}
            </span>
          </div>
          <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-[12px] text-arepo-muted">
            <span>Priority {entry.research_priority}/100</span>
            <span>Strength {Math.round(entry.strength * 100)}%</span>
            <span>{digestEvaluationLabel(entry.evaluation)} · {entry.evaluation.horizon}</span>
          </div>
        </article>
      ))}
    </div>
  );
}

function PreferencesTab({ onDeleted }: { onDeleted: () => void }) {
  const { signOut } = useAuth();
  const [prefs, setPrefs] = useState<AlertPreferences | null>(null);
  const [error, setError] = useState("");
  const [saved, setSaved] = useState(false);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    getPreferences()
      .then(setPrefs)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load preferences."));
  }, []);

  function patch(changes: Partial<AlertPreferences>) {
    setPrefs((current) => (current ? { ...current, ...changes } : current));
    setSaved(false);
  }

  async function save() {
    if (!prefs) return;
    setPending(true);
    setError("");
    try {
      const updated = await updatePreferences({
        categories: prefs.categories,
        digest_top_n: prefs.digest_top_n,
        digest_frequency: prefs.digest_frequency,
      });
      setPrefs(updated);
      setSaved(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save preferences.");
    } finally {
      setPending(false);
    }
  }

  if (!prefs) {
    return (
      <section role="tabpanel" aria-label="Preferences">
        {error ? <FormMessage tone="error">{error}</FormMessage> : <p className="text-arepo-muted">Loading…</p>}
      </section>
    );
  }

  return (
    <section role="tabpanel" aria-label="Preferences" className="space-y-8">
      <div className="space-y-7 rounded-card border border-arepo-border bg-arepo-surface p-5 sm:p-6">
        {error && <FormMessage tone="error">{error}</FormMessage>}
        {saved && <FormMessage tone="ok">Preferences saved.</FormMessage>}

        <PreferenceGroup title="Categories" hint="Leave all unselected to include every category.">
          <div className="flex flex-wrap gap-2">
            {CATEGORY_OPTIONS.map((category) => {
              const selected = prefs.categories.includes(category);
              return (
                <button
                  key={category}
                  type="button"
                  aria-pressed={selected}
                  onClick={() =>
                    patch({
                      categories: selected
                        ? prefs.categories.filter((item) => item !== category)
                        : [...prefs.categories, category],
                    })
                  }
                  className={`focus-ring rounded-full border px-3 py-1.5 text-[12.5px] font-medium ${
                    selected
                      ? "border-arepo-accent bg-arepo-accentTint text-arepo-accentActive"
                      : "border-arepo-border text-arepo-muted hover:text-arepo-ink"
                  }`}
                >
                  {category}
                </button>
              );
            })}
          </div>
        </PreferenceGroup>

        <PreferenceGroup title="Number of opportunities">
          <Segmented>
            {([5, 10, 20] as const).map((count) => (
              <Choice
                key={count}
                selected={prefs.digest_top_n === count}
                onClick={() => patch({ digest_top_n: count })}
              >
                Top {count}
              </Choice>
            ))}
          </Segmented>
        </PreferenceGroup>

        <PreferenceGroup title="Frequency">
          <Segmented>
            {FREQUENCIES.map((frequency) => (
              <Choice
                key={frequency.value}
                selected={prefs.digest_frequency === frequency.value}
                onClick={() => patch({ digest_frequency: frequency.value })}
              >
                {frequency.label}
              </Choice>
            ))}
          </Segmented>
        </PreferenceGroup>

        <button
          type="button"
          onClick={() => void save()}
          disabled={pending}
          className="focus-ring rounded-md bg-arepo-accent px-4 py-2 text-[14px] font-semibold text-white hover:bg-arepo-accentHover disabled:opacity-60"
        >
          {pending ? "Saving…" : "Save preferences"}
        </button>
      </div>

      <AccountActions
        onDeleted={async () => {
          try {
            await signOut();
          } finally {
            onDeleted();
          }
        }}
      />
    </section>
  );
}

function PreferenceGroup({
  title,
  hint,
  children,
}: {
  title: string;
  hint?: string;
  children: React.ReactNode;
}) {
  return (
    <fieldset>
      <legend className="text-[14px] font-semibold text-arepo-ink">{title}</legend>
      {hint && <p className="mb-3 mt-1 text-[12px] text-arepo-muted">{hint}</p>}
      {!hint && <div className="h-3" />}
      {children}
    </fieldset>
  );
}

function Segmented({ children }: { children: React.ReactNode }) {
  return <div className="flex flex-wrap gap-2">{children}</div>;
}

function Choice({
  selected,
  onClick,
  children,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      onClick={onClick}
      className={`focus-ring rounded-md border px-3 py-2 text-[13px] font-medium ${
        selected
          ? "border-arepo-accent bg-arepo-accentTint text-arepo-accentActive"
          : "border-arepo-border text-arepo-muted hover:text-arepo-ink"
      }`}
    >
      {children}
    </button>
  );
}

function AccountActions({ onDeleted }: { onDeleted: () => void }) {
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
    <details className="text-[13px] text-arepo-muted">
      <summary className="focus-ring w-fit cursor-pointer rounded-md hover:text-arepo-ink">
        Account actions
      </summary>
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <Link href="/forgot" className="focus-ring underline hover:text-arepo-ink">
          Reset password
        </Link>
        {confirming ? (
          <>
            <button
              type="button"
              onClick={() => void remove()}
              disabled={pending}
              className="focus-ring rounded-md border border-arepo-warn/40 px-3 py-1.5 font-medium text-arepo-warnText disabled:opacity-60"
            >
              {pending ? "Deleting…" : "Confirm account deletion"}
            </button>
            <button type="button" onClick={() => setConfirming(false)} className="focus-ring hover:text-arepo-ink">
              Cancel
            </button>
          </>
        ) : (
          <button type="button" onClick={() => setConfirming(true)} className="focus-ring text-arepo-warnText">
            Delete account
          </button>
        )}
      </div>
    </details>
  );
}

function formatDigestDay(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    weekday: "long",
    day: "numeric",
    month: "long",
  }).format(new Date(value));
}

function formatDigestTime(value: string): string {
  return new Intl.DateTimeFormat("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    timeZoneName: "short",
  }).format(new Date(value));
}
