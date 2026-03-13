/**
 * Service Worker for Cricket Auction Platform
 * Provides offline capability and faster loading
 * Version: 3.0.0 - Force cache clear for security tab update
 */

const CACHE_NAME = 'cricket-auction-v3.0.0';
const RUNTIME_CACHE = 'cricket-auction-runtime-v3';

// Assets to cache immediately on install
const PRECACHE_ASSETS = [
  '/static/player-cards.css',
  '/static/skit-pro.css',
  '/static/mobile-optimized.css',
  '/static/realtime-optimizer.js',
  '/static/ux-enhancements.js',
  '/static/lazy-loader.js',
  // Add more critical assets as needed
];

// Install event - cache critical assets
self.addEventListener('install', (event) => {
  console.log('[SW] Installing service worker...');
  
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then((cache) => {
        console.log('[SW] Precaching assets');
        return cache.addAll(PRECACHE_ASSETS);
      })
      .then(() => self.skipWaiting())
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', (event) => {
  console.log('[SW] Activating service worker...');
  
  event.waitUntil(
    caches.keys()
      .then((cacheNames) => {
        return Promise.all(
          cacheNames
            .filter((name) => name !== CACHE_NAME && name !== RUNTIME_CACHE)
            .map((name) => {
              console.log('[SW] Deleting old cache:', name);
              return caches.delete(name);
            })
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch event - serve from cache, fallback to network
self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);
  
  // Skip non-GET requests
  if (request.method !== 'GET') {
    return;
  }
  
  // Skip WebSocket connections
  if (url.pathname.startsWith('/ws')) {
    return;
  }
  
  // Skip API calls (always fetch fresh)
  if (url.pathname.startsWith('/api') || 
      url.pathname.startsWith('/auth') ||
      url.pathname.startsWith('/auction') ||
      url.pathname.startsWith('/players') ||
      url.pathname.startsWith('/teams') ||
      url.pathname.startsWith('/security')) {
    event.respondWith(networkFirst(request));
    return;
  }
  
  // For static assets and pages, use cache-first strategy
  if (url.pathname.startsWith('/static/') || 
      url.pathname === '/' ||
      url.pathname === '/team/dashboard' ||
      url.pathname === '/admin' ||
      url.pathname === '/live') {
    event.respondWith(cacheFirst(request));
    return;
  }
  
  // Default: network first
  event.respondWith(networkFirst(request));
});

/**
 * Cache-first strategy
 * Try cache first, fallback to network
 * Good for static assets
 */
async function cacheFirst(request) {
  const cache = await caches.open(CACHE_NAME);
  const cached = await cache.match(request);
  
  if (cached) {
    console.log('[SW] Serving from cache:', request.url);
    // Update cache in background
    fetch(request).then((response) => {
      if (response.ok) {
        cache.put(request, response.clone());
      }
    });
    return cached;
  }
  
  console.log('[SW] Cache miss, fetching:', request.url);
  const response = await fetch(request);
  
  if (response.ok) {
    cache.put(request, response.clone());
  }
  
  return response;
}

/**
 * Network-first strategy
 * Try network first, fallback to cache
 * Good for dynamic content
 */
async function networkFirst(request) {
  const cache = await caches.open(RUNTIME_CACHE);
  
  try {
    const response = await fetch(request);
    
    if (response.ok) {
      cache.put(request, response.clone());
    }
    
    return response;
  } catch (error) {
    console.log('[SW] Network failed, trying cache:', request.url);
    const cached = await cache.match(request);
    
    if (cached) {
      return cached;
    }
    
    // Return offline page or error
    return new Response('Offline - Please check your connection', {
      status: 503,
      statusText: 'Service Unavailable',
      headers: new Headers({
        'Content-Type': 'text/plain'
      })
    });
  }
}

// Handle messages from clients
self.addEventListener('message', (event) => {
  if (event.data === 'skipWaiting') {
    self.skipWaiting();
  }
  
  if (event.data === 'clearCache') {
    event.waitUntil(
      caches.keys().then((names) => {
        return Promise.all(names.map((name) => caches.delete(name)));
      })
    );
  }
});

// Background sync for offline actions
self.addEventListener('sync', (event) => {
  console.log('[SW] Background sync:', event.tag);
  
  if (event.tag === 'sync-bids') {
    event.waitUntil(syncOfflineBids());
  }
});

async function syncOfflineBids() {
  // Sync any offline bids when connection is restored
  console.log('[SW] Syncing offline bids...');
  // Implementation would go here
}

console.log('[SW] Service Worker loaded');
