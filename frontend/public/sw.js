// Conjure Service Worker — Phase 1: minimal registration
// Phase 5 will add: offline caching, app asset caching, background sync

const CACHE_NAME = "conjure-v1";

self.addEventListener("install", () => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(clients.claim());
});

self.addEventListener("fetch", (event) => {
  // Phase 1: pass-through (no caching)
  // Phase 5: cache-first for /apps/*, network-first for /api/*
  event.respondWith(fetch(event.request));
});
