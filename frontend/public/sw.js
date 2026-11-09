// CampusMind service worker: makes the app installable, shows an offline page, and lets reminders
// appear as system notifications. Answers always come from the live server: nothing else is cached.
const OFFLINE_HTML = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>CampusMind · Offline</title>
<style>:root{color-scheme:light dark}body{margin:0;min-height:100vh;display:grid;place-items:center;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;background:#F5F5F7;color:#1D1D1F}
@media (prefers-color-scheme:dark){body{background:#000;color:#F5F5F7}}main{max-width:360px;padding:24px;text-align:center}h1{font-size:22px;font-weight:600;margin:0 0 8px}p{font-size:15px;opacity:.7;line-height:1.5}</style></head>
<body><main><h1>CampusMind is offline</h1><p>The CampusMind server isn't reachable. Check your connection, or start CampusMind on the laptop, then reload.</p></main></body></html>`;

self.addEventListener("install", () => self.skipWaiting());
self.addEventListener("activate", (event) => event.waitUntil(self.clients.claim()));

self.addEventListener("fetch", (event) => {
  if (event.request.mode !== "navigate") return;
  event.respondWith(
    fetch(event.request).catch(() => new Response(OFFLINE_HTML, { headers: { "Content-Type": "text/html; charset=utf-8" } })),
  );
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      const open = clients.find((c) => c.url.includes("/calendar"));
      if (open) return open.focus();
      return self.clients.openWindow("/calendar");
    }),
  );
});
