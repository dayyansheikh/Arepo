import type { AccountUser, DigestEvaluation } from "./types";

export function initialsForUser(
  user: Pick<AccountUser, "first_name" | "last_name" | "email">,
): string {
  const first = user.first_name?.trim() ?? "";
  const last = user.last_name?.trim() ?? "";
  if (first && last) return `${first[0]}${last[0]}`.toUpperCase();
  const oneName = first || last;
  if (oneName) return oneName.slice(0, 2).toUpperCase();
  const emailInitial = user.email.trim()[0];
  return emailInitial ? emailInitial.toUpperCase() : "A";
}

export function digestEvaluationLabel(evaluation: DigestEvaluation): string {
  if (evaluation.resolved) {
    return evaluation.resolved_outcome
      ? `Resolved: ${evaluation.resolved_outcome}`
      : "Resolved";
  }
  return {
    moved_expected: "Moved as signalled",
    moved_against: "Moved against signal",
    no_change: "Unchanged",
    pending: "Pending",
    unavailable: "Unavailable",
    closed_before_horizon: "Closed before horizon",
    invalid: "Unavailable",
  }[evaluation.state] ?? "Pending";
}
