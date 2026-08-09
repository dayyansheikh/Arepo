import { expect, test, type Route } from "@playwright/test";

const USER = {
  id: "user-1",
  email: "dayyan@example.com",
  first_name: "Dayyan",
  last_name: "Sheikh",
  is_active: true,
  is_verified: true,
  is_superuser: false,
  auth_provider: "local",
  consent_at: null,
};

async function json(route: Route, status: number, body: unknown) {
  await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
}

test("signup sends first and last name and uses production verification wording", async ({ page }) => {
  let registration: Record<string, unknown> | null = null;
  await page.route("http://localhost:8000/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/users/me") return json(route, 401, { detail: "Unauthorized" });
    if (url.pathname === "/api/auth/register") {
      registration = route.request().postDataJSON();
      return json(route, 201, USER);
    }
    return json(route, 404, { detail: "Not found" });
  });

  await page.goto("/signup");
  await page.getByLabel("First name").fill("Dayyan");
  await page.getByLabel("Last name").fill("Sheikh");
  await page.getByLabel("Email").fill("dayyan@example.com");
  await page.getByLabel("Password").fill("Sufficiently-Long-1");
  await page.getByRole("checkbox").check();
  await page.getByRole("button", { name: "Create account" }).click();

  await expect(page.getByText("Check your email to verify your Arepo account.")).toBeVisible();
  expect(registration).toEqual({
    first_name: "Dayyan",
    last_name: "Sheikh",
    email: "dayyan@example.com",
    password: "Sufficiently-Long-1",
  });
  expect(registration).not.toHaveProperty("username");
});

test("authenticated session survives refresh, shows initials and signs out", async ({ page }) => {
  let signedIn = true;
  await page.route("http://localhost:8000/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/users/me") {
      return signedIn ? json(route, 200, USER) : json(route, 401, { detail: "Unauthorized" });
    }
    if (url.pathname === "/api/account/digests") {
      return json(route, 200, { items: [], has_more: false });
    }
    if (url.pathname === "/api/auth/logout") {
      signedIn = false;
      return route.fulfill({ status: 204 });
    }
    return json(route, 404, { detail: "Not found" });
  });

  await page.goto("/account");
  await expect(page.getByRole("link", { name: "Your account" })).toHaveText("DS");
  await expect(page.getByRole("tab", { name: "Your digests" })).toBeVisible();
  await expect(page.getByRole("tab", { name: "Preferences" })).toBeVisible();

  await page.reload();
  await expect(page.getByRole("link", { name: "Your account" })).toHaveText("DS");
  await page.getByRole("button", { name: "Sign out" }).click();
  await expect(page.getByRole("link", { name: "Sign in" }).first()).toBeVisible();
});

test("account page does not expose personalised content when signed out", async ({ page }) => {
  await page.route("http://localhost:8000/api/**", async (route) => {
    await json(route, 401, { detail: "Unauthorized" });
  });
  await page.goto("/account");
  await expect(page.getByText("Sign in to review your digests and preferences.")).toBeVisible();
  await expect(page.getByRole("tab")).toHaveCount(0);
});

test("published digest CTA route resolves to the current Opportunities page", async ({ page }) => {
  await page.route("http://localhost:8000/api/**", async (route) => {
    const url = new URL(route.request().url());
    if (url.pathname === "/api/users/me") return json(route, 401, { detail: "Unauthorized" });
    if (url.pathname === "/api/scan/opportunities") {
      return json(route, 200, { has_scan: false, rows: [], denominator: null });
    }
    return json(route, 404, { detail: "Not found" });
  });

  await page.goto("/opportunities");
  await expect(page).toHaveURL(/\/$/);
  await expect(page.getByTestId("opportunities-page")).toBeVisible();
});
