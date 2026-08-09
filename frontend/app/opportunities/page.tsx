import { redirect } from "next/navigation";

/** Stable email deep link; Opportunities currently lives at the canonical home route. */
export default function OpportunitiesRedirect() {
  redirect("/");
}
