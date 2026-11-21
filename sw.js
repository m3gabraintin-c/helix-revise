/* Helix Revise service worker. Plain script, no build step; every path is relative to this file so it works at /helix-revise/.
   Update behaviour: skipWaiting() + clients.claim() mean a new worker takes over open tabs as soon as it activates. Pages
   already open keep running the old index.html in memory until they reload, but their later data/ and content/ requests go to the new worker.
   Navigations are network-first, so an online reload always gets the newest page. When the shell assets change, bump CACHE
   (old caches are deleted on activate). data/ and content/ refresh themselves in the background without a bump (stale-while-revalidate). */
const CACHE = "helix-v1";
const KATEX = "https://cdn.jsdelivr.net/npm/katex@0.19.1/dist/";
const PRECACHE = ["./", "index.html", "data/index.json", "manifest.webmanifest", "icons/icon-192.png", "icons/icon-512.png", "icons/icon-maskable-512.png", "icons/apple-touch-icon.png"];
const PRECACHE_CORS = [KATEX + "katex.min.css", KATEX + "katex.min.js", KATEX + "contrib/auto-render.min.js"];

/* <sw-routing> */
// Which strategy a request gets: "network-first" (the page), "swr" (stale-while-revalidate: own data/ and content/),
// "cache-first" (icons, manifest, fonts, KaTeX files) or null (leave to the network, never cached).
function strategyFor(url, method, mode, origin) {
  const u = new URL(url);
  if (method !== "GET") return null;
  if (u.origin === origin) {
    if (mode === "navigate" || /(^|\/)index\.html$/.test(u.pathname)) return "network-first";
    if (/\/(data|content)\/[^?#]+\.json$/.test(u.pathname)) return "swr";
    if (/\/(icons\/[^/]+\.png|manifest\.webmanifest)$/.test(u.pathname)) return "cache-first";
    return null;
  }
  if (u.origin === "https://fonts.googleapis.com" || u.origin === "https://fonts.gstatic.com" || (u.origin === "https://cdn.jsdelivr.net" && u.pathname.startsWith("/npm/katex@0.19.1/"))) return "cache-first";
  return null;
}
/* </sw-routing> */

self.addEventListener("install", e => {
  e.waitUntil(caches.open(CACHE).then(c => Promise.all([
    c.addAll(PRECACHE),
    ...PRECACHE_CORS.map(u => c.add(new Request(u, { mode: "cors" }))),
  ])).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});

// Only successful responses are stored (so a 404 stays a 404). Opaque responses (Google Fonts CSS is a no-cors stylesheet) are
// kept only for the font hosts, since we cannot see their status.
const storable = (req, r) => r && (r.ok || (r.type === "opaque" && /^https:\/\/fonts\.g/.test(req.url)));
const put = (req, r) => { if (storable(req, r)) { const copy = r.clone(); caches.open(CACHE).then(c => c.put(req, copy)); } return r; };

self.addEventListener("fetch", e => {
  const req = e.request, s = strategyFor(req.url, req.method, req.mode, self.location.origin);
  if (!s) return;
  if (s === "network-first") {
    // Key every navigation to the one cached page, whatever the hash or query.
    const key = new Request("index.html");
    e.respondWith(fetch(req).then(r => (r.ok && caches.open(CACHE).then(c => c.put(key, r.clone())), r)).catch(() => caches.match(key).then(r => r || caches.match("./"))));
  } else if (s === "swr") {
    e.respondWith(caches.match(req).then(hit => {
      const net = fetch(req).then(r => put(req, r));
      if (hit) { net.catch(() => {}); return hit; }
      return net;
    }));
  } else {
    e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => put(req, r))));
  }
});
