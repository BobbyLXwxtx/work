// Cloudflare Worker: Polar Merchant-of-Record Webhook + Token-Gated Dataset Delivery

async function verifySignature(bodyText, signatureHeader, secret) {
  if (!signatureHeader || !secret) return false;
  const enc = new TextEncoder();
  const key = await crypto.subtle.importKey(
    "raw",
    enc.encode(secret),
    { name: "HMAC", hash: "SHA-256" },
    false,
    ["sign"]
  );
  const sig = await crypto.subtle.sign("HMAC", key, enc.encode(bodyText));
  const expected = Array.from(new Uint8Array(sig))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return signatureHeader.endsWith(expected);
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (request.method === "POST" && url.pathname === "/webhook/polar") {
      const bodyText = await request.text();
      const sig = request.headers.get("webhook-signature") || "";
      const valid = await verifySignature(bodyText, sig, env.POLAR_WEBHOOK_SECRET);
      if (!valid) {
        return new Response("Invalid signature", { status: 401 });
      }

      const event = JSON.parse(bodyText);
      if (event.type === "order.paid") {
        const order = event.data;
        const token = crypto.randomUUID();
        await env.DB.prepare(
          "INSERT OR IGNORE INTO orders (id, customer_email, product_id, api_token, status, created_at) VALUES (?, ?, ?, ?, 'active', ?)"
        )
          .bind(
            order.id,
            order.customer?.email || "unknown",
            order.product_id || "default",
            token,
            new Date().toISOString()
          )
          .run();
      }
      return new Response("ok", { status: 200 });
    }

    if (request.method === "GET" && url.pathname === "/api/v1/feed") {
      const token = url.searchParams.get("token") || request.headers.get("x-api-key") || "";
      const row = await env.DB.prepare(
        "SELECT status FROM orders WHERE api_token = ? LIMIT 1"
      )
        .bind(token)
        .first();

      if (!row || row.status !== "active") {
        return new Response("Unauthorized", { status: 401 });
      }

      // Proxy the latest normalized JSON from your Pages/R2 origin
      const upstream = await fetch(`${env.PAGES_ORIGIN}/data/latest.json`);
      return new Response(upstream.body, {
        headers: { "content-type": "application/json; charset=utf-8" },
      });
    }

    return new Response("Not Found", { status: 404 });
  },
};