# SolarConnect: Why Pages Take 3–4 s and PDFs 5–8 s

> **Version:** v1.0 · **Date:** 2026-11-09 · **Status:** Findings and proposed fixes. No code changed.
> **Owner report:** opening a page takes 3–4 seconds; generating a PDF takes 5–8 seconds.
> **Checked:** the app code (`nrg-solar-connect-app`, `main`), the live database's query statistics (`pg_stat_statements`, read-only), and Supabase's performance advisor.

---

## 1. The database itself is fast. It is not the cause.

Measured on the live database:
- The app's typical queries (e.g. the projects list) average about **21 ms**.
- The login/user lookup averages **0.1 ms**.
- Supabase's performance advisor shows only minor notes: 5 foreign keys without an index (on small tables) and 171 indexes never used. Neither explains seconds of delay.

**So the time goes on *how many trips* the app makes to the database, and *how far* each trip travels.**

---

## 2. Page loads (3–4 s): three causes

### Cause 1: Where the app server is (most likely the biggest)
- The database is in **Mumbai** (Supabase region `ap-south-1`, confirmed).
- The app runs on **Railway**. Its region can't be seen from the code. **It needs checking in Railway → the service → Settings → Region.**
- If the app runs in the US (a common default), **every trip to the database crosses the world and back, about 0.2–0.3 s each.** Your browser's trip to the app server also crosses the world.
- I don't believe Railway currently offers a Mumbai region (please confirm on its settings page). If not, the nearest is **Singapore**, roughly 0.06–0.07 s per trip.

### Cause 2: About 8–10 database trips, one after another, before every page
Before any page shows anything, this runs **in sequence**, on **every** click:

| Step | Where | Trips |
|---|---|---|
| Check login with Supabase Auth | `middleware.ts` | 1 |
| Look up the employee | `middleware.ts` | 1 |
| Check device approval + module access (in parallel) | `middleware.ts` | 1 |
| Count pending device approvals (admins) | `app/(app)/layout.tsx` | 1 |
| Read module grants for the sidebar | `app/(app)/layout.tsx` | 1 |
| Pending approvals (2 queries, in parallel) | `lib/pending-approvals.ts` via layout | 1 |
| My open tasks + **every task's status for the whole company** (unfiltered) | `app/(app)/layout.tsx` | 1 |
| The page's own data | each page | 1–3 |
| **Total** | | **about 8–10 trips in a row** |

**The arithmetic:** 8–10 trips × 0.25 s (if the server is in the US) ≈ **2–2.5 s**, plus the trip from your browser to the server, plus building the page, **≈ 3–4 s. That matches what you see.**
With the server in Singapore the same 8–10 trips would be about 0.6 s. With the steps also combined (fixes B–C below), about 0.2–0.3 s.

### Cause 3: Nothing appears while you wait
- There are **no loading screens** in the app (0 `loading.tsx` files). After a click, the old page just sits there until the new one is fully ready, so 3 seconds feels like 6.
- The NRG logo is built into the code as a **199 KB** embedded image (`lib/brand-logo.ts`) and used in the sidebar, so it adds weight to page loads.

---

## 3. PDFs (5–8 s): four causes

Every PDF goes through `lib/html-to-pdf.ts`:

| Step | Why it's slow |
|---|---|
| **A whole new Chrome browser is started for every PDF**, then closed | Starting Chrome takes about 1–3 s on a small server, every single time |
| `waitUntil: 'networkidle'` | Waits until the page has been quiet for at least half a second, even though the images are already embedded |
| Big embedded images | Quote covers and back pages are about **1.2 MB** of images built into the code (`lib/quote-cover-assets.ts`); Chrome has to decode and lay them out |
| Then the upload to Google Drive, and the database trips around it | More trips, and more distance if the server is far away |

---

## 4. Fixes, in order (biggest effect for least effort first)

| # | Fix | Effect | Effort | Risk |
|---|---|---|---|---|
| **A** | **Move the Railway app to the region closest to Mumbai** (likely Singapore), or move both to one region | Probably the single biggest gain on every page | **A setting, no code.** A few minutes of downtime during the move. | Low |
| **B** | Combine the middleware lookups (employee + device + module access) into **one** database call, and remember "device approved" for a few minutes in a signed cookie instead of checking on every click | Removes 2–3 trips from every page | Small | Medium: touches login/security code, so it needs careful testing |
| **C** | In the layout, run all the sidebar queries **at the same time** instead of one after another, and **filter the task-status query to the user's own tasks** | Removes 2–4 trips from every page | Small | Low |
| **D** | Add **loading screens** (`loading.tsx`) so a click responds instantly with a skeleton/spinner | Feels much faster even before the other fixes | Small | Very low |
| **E** | Keep **one Chrome running** and reuse it for every PDF, instead of starting a new one each time; use `waitUntil: 'load'` | Probably cuts 1–3 s off every PDF | Small | Low–Medium: needs a restart guard in case Chrome crashes |
| **F** | Shrink the embedded cover/back-page images (re-save at print resolution and sensible JPEG quality) and the 199 KB logo | Faster PDFs and lighter pages | Small | Low: check print quality on a sample |
| **G** | Show the PDF to the user first and **upload to Drive in the background** | The user's wait no longer includes the Drive upload | Medium | Low |
| **H** | Later: move PDF generation to its own service with a queue (see the setup and customisation design, Part 5) | Protects page speed when many people make PDFs at once | Medium | Low |

**Order:** A first (no code; it shows how much of the delay was distance), then D + C (quick and safe), then E + F (PDFs), then B (security code, done carefully), then G and H.

---

## 5. What the owner can check right now, without any code
1. **Railway → your SolarConnect service → Settings → Region.** Note which region it shows.
2. Note whether a region closer to Mumbai (e.g. Singapore) is listed.
3. In Chrome on your laptop: open the app, press **F12 → Network tab**, click a menu item, and note the **time** of the first row (the page itself). That gives a "before" number to compare after each fix.
