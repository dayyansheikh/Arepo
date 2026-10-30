import type { Metadata } from "next";
import { SecurityKeys } from "@/components/lab/SecurityKeys";
import "../lab.css";

// Private owner-only page: never indexed, never linked from public navigation. Access control is
// enforced by the API (401 -> sign-in, 404 for anyone but the owner); this page holds no data.
export const metadata: Metadata = {
  robots: { index: false, follow: false, nocache: true, googleBot: { index: false, follow: false } },
};

export default function LabSecurityPage() {
  return <SecurityKeys />;
}
