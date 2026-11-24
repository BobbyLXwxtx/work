# $0.00 Autonomous Niche Data Utility — Starter Kit

A complete, zero-capital, self-operating digital product pipeline:
1. **GitHub Actions** (`0 6 * * *` UTC) runs `src/etl/fetch_and_normalize.py` on free public repo runners.
2. **Self-healing validation** halts deployment if upstream schema or row counts fail, preserving the last known-good snapshot.
3. **Static SEO storefront** (`dist/index.html`) deploys to **Cloudflare Pages** (`*.pages.dev`, $0/mo) or **GitHub Pages** ($0/mo).
4. **Polar Starter** ($0/mo, 5% + $0.50/txn) handles checkout, global VAT/sales tax, and fires signed webhooks to **Cloudflare Workers + D1** (`worker/index.js`).

## 10-Minute $0.00 Setup
1. Create a **public** GitHub repository and push this folder.
2. Connect the repo to **Cloudflare Pages** (build output directory: `dist`) or enable **GitHub Pages**.
3. Create a **Cloudflare D1** database (`npx wrangler d1 create autonomous_feed`) and apply `worker/schema.sql`.
4. Deploy `worker/index.js` (`npx wrangler deploy`) and set `POLAR_WEBHOOK_SECRET` via `npx wrangler secret put POLAR_WEBHOOK_SECRET`.
5. Create a digital product on **Polar.sh** (Starter plan, $0/mo), copy your Checkout Link into `POLAR_CHECKOUT_URL` in GitHub repo variables, and point Polar's webhook to your Worker URL (`/webhook/polar`).
