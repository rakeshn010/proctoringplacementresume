/**
 * Lazy Loading & Code Splitting Optimizer
 * Professional-grade performance optimization
 * Version: 1.0.0
 */

class LazyLoader {
  constructor() {
    this.imageObserver = null;
    this.componentObserver = null;
    this.init();
  }

  init() {
    // Initialize Intersection Observer for images
    this.initImageLazyLoading();
    
    // Initialize component lazy loading
    this.initComponentLazyLoading();
    
    // Preconnect to CDNs (lightweight optimization)
    this.preconnectToCDNs();
    
    // Register service worker (optional, won't break if it fails)
    this.registerServiceWorker();
  }
  
  /**
   * Preconnect to CDNs for faster external resource loading
   */
  preconnectToCDNs() {
    const cdns = [
      'https://cdn.jsdelivr.net',
      'https://cdnjs.cloudflare.com'
    ];
    
    cdns.forEach(cdn => {
      const link = document.createElement('link');
      link.rel = 'preconnect';
      link.href = cdn;
      link.crossOrigin = 'anonymous';
      document.head.appendChild(link);
    });
  }

  /**
   * Lazy load images using Intersection Observer
   * Much more efficient than scroll events
   */
  initImageLazyLoading() {
    if ('IntersectionObserver' in window) {
      this.imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const img = entry.target;
            this.loadImage(img);
            observer.unobserve(img);
          }
        });
      }, {
        rootMargin: '50px 0px', // Start loading 50px before entering viewport
        threshold: 0.01
      });

      // Observe all images with data-src attribute
      this.observeImages();
    } else {
      // Fallback for older browsers
      this.loadAllImages();
    }
  }

  observeImages() {
    const lazyImages = document.querySelectorAll('img[data-src], img[loading="lazy"]');
    lazyImages.forEach(img => {
      if (img.dataset.src) {
        this.imageObserver.observe(img);
      }
    });
  }

  loadImage(img) {
    const src = img.dataset.src || img.src;
    
    // Create a new image to preload
    const tempImg = new Image();
    
    tempImg.onload = () => {
      img.src = src;
      img.classList.add('loaded');
      img.removeAttribute('data-src');
      
      // Fade in effect
      img.style.opacity = '0';
      img.style.transition = 'opacity 0.3s ease-in';
      setTimeout(() => {
        img.style.opacity = '1';
      }, 10);
    };
    
    tempImg.onerror = () => {
      // Use fallback image
      const fallback = img.dataset.fallback || this.getDefaultPlayerImage();
      img.src = fallback;
      img.classList.add('error');
    };
    
    tempImg.src = src;
  }

  loadAllImages() {
    const lazyImages = document.querySelectorAll('img[data-src]');
    lazyImages.forEach(img => this.loadImage(img));
  }

  getDefaultPlayerImage() {
    return 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="280" height="220"%3E%3Crect fill="%230a0a0a" width="280" height="220"/%3E%3Ctext x="50%25" y="50%25" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="80" fill="%23ffd700"%3E👤%3C/text%3E%3C/svg%3E';
  }

  /**
   * Lazy load components/sections
   */
  initComponentLazyLoading() {
    if ('IntersectionObserver' in window) {
      this.componentObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const component = entry.target;
            this.loadComponent(component);
            this.componentObserver.unobserve(component);
          }
        });
      }, {
        rootMargin: '100px 0px',
        threshold: 0.01
      });

      // Observe lazy components
      const lazyComponents = document.querySelectorAll('[data-lazy-component]');
      lazyComponents.forEach(comp => this.componentObserver.observe(comp));
    }
  }

  loadComponent(component) {
    const componentName = component.dataset.lazyComponent;
    
    // Add loading state
    component.classList.add('loading');
    
    // Simulate component loading (replace with actual logic)
    setTimeout(() => {
      component.classList.remove('loading');
      component.classList.add('loaded');
      
      // Trigger custom event
      component.dispatchEvent(new CustomEvent('componentLoaded', {
        detail: { componentName }
      }));
    }, 100);
  }

  /**
   * Preload critical resources
   */
  preloadCriticalResources() {
    // Disabled to prevent "not used" warnings
    // Resources are loaded fast enough without preload
    return;
  }

  /**
   * Register service worker for offline support
   * This is optional - app works fine without it
   */
  async registerServiceWorker() {
    if ('serviceWorker' in navigator) {
      try {
        // Unregister old service workers first
        const registrations = await navigator.serviceWorker.getRegistrations();
        for (let registration of registrations) {
          await registration.unregister();
        }
        
        // Register new service worker from root path
        const registration = await navigator.serviceWorker.register('/service-worker.js', {
          scope: '/'
        });
        
        console.log('[LazyLoader] Service Worker registered successfully:', registration.scope);
        
        // Handle updates
        registration.addEventListener('updatefound', () => {
          const newWorker = registration.installing;
          
          newWorker.addEventListener('statechange', () => {
            if (newWorker.state === 'installed' && navigator.serviceWorker.controller) {
              // New service worker available
              this.showUpdateNotification();
            }
          });
        });
      } catch (error) {
        // Service worker failed - not critical, app still works
        console.log('[LazyLoader] Service Worker not available (this is OK):', error.message);
      }
    }
  }

  showUpdateNotification() {
    // Show a notification that an update is available
    if (typeof showToast === 'function') {
      showToast('Update Available', 'A new version is available. Refresh to update.', 'info');
    }
  }

  /**
   * Prefetch next page resources
   */
  prefetchPage(url) {
    const link = document.createElement('link');
    link.rel = 'prefetch';
    link.href = url;
    document.head.appendChild(link);
  }

  /**
   * Preconnect to external domains
   */
  preconnect(domain) {
    const link = document.createElement('link');
    link.rel = 'preconnect';
    link.href = domain;
    link.crossOrigin = 'anonymous';
    document.head.appendChild(link);
  }

  /**
   * Load script dynamically
   */
  async loadScript(src, async = true) {
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = src;
      script.async = async;
      
      script.onload = () => resolve(script);
      script.onerror = () => reject(new Error(`Failed to load script: ${src}`));
      
      document.body.appendChild(script);
    });
  }

  /**
   * Load CSS dynamically
   */
  async loadCSS(href) {
    return new Promise((resolve, reject) => {
      const link = document.createElement('link');
      link.rel = 'stylesheet';
      link.href = href;
      
      link.onload = () => resolve(link);
      link.onerror = () => reject(new Error(`Failed to load CSS: ${href}`));
      
      document.head.appendChild(link);
    });
  }

  /**
   * Optimize images on the fly
   */
  optimizeImage(img, maxWidth = 800) {
    if (img.naturalWidth > maxWidth) {
      img.style.maxWidth = maxWidth + 'px';
      img.style.height = 'auto';
    }
  }

  /**
   * Defer non-critical CSS
   */
  deferCSS(href) {
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = href;
    link.media = 'print';
    link.onload = function() {
      this.media = 'all';
    };
    document.head.appendChild(link);
  }
}

// Initialize lazy loader
const lazyLoader = new LazyLoader();

// Export for global use
window.lazyLoader = lazyLoader;

// Re-observe images when DOM changes (for dynamic content)
if (typeof MutationObserver !== 'undefined') {
  const observer = new MutationObserver(() => {
    lazyLoader.observeImages();
  });
  
  observer.observe(document.body, {
    childList: true,
    subtree: true
  });
}

console.log('[LazyLoader] Initialized successfully');
