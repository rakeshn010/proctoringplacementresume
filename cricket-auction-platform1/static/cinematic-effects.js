// Cinematic Effects - Particle Background
// Add this to any page for Hollywood-level effects

(function() {
    'use strict';
    
    // Initialize particle background
    function initParticles() {
        // Check if canvas already exists
        let canvas = document.getElementById('particles');
        
        // Create canvas if it doesn't exist
        if (!canvas) {
            canvas = document.createElement('canvas');
            canvas.id = 'particles';
            canvas.style.cssText = 'position:fixed;top:0;left:0;width:100%;height:100%;z-index:0;opacity:0.15;pointer-events:none;';
            document.body.insertBefore(canvas, document.body.firstChild);
        }
        
        const ctx = canvas.getContext('2d');
        canvas.width = window.innerWidth;
        canvas.height = window.innerHeight;
        
        const particles = [];
        const particleCount = 50;
        
        // Create particles
        for (let i = 0; i < particleCount; i++) {
            particles.push({
                x: Math.random() * canvas.width,
                y: Math.random() * canvas.height,
                radius: Math.random() * 2 + 1,
                vx: (Math.random() - 0.5) * 0.5,
                vy: (Math.random() - 0.5) * 0.5
            });
        }
        
        // Animation loop
        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            ctx.fillStyle = 'rgba(255, 215, 0, 0.3)';
            
            particles.forEach(p => {
                p.x += p.vx;
                p.y += p.vy;
                
                // Bounce off edges
                if (p.x < 0 || p.x > canvas.width) p.vx *= -1;
                if (p.y < 0 || p.y > canvas.height) p.vy *= -1;
                
                // Draw particle
                ctx.beginPath();
                ctx.arc(p.x, p.y, p.radius, 0, Math.PI * 2);
                ctx.fill();
            });
            
            requestAnimationFrame(animate);
        }
        
        animate();
        
        // Handle window resize
        window.addEventListener('resize', () => {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        });
    }
    
    // Initialize when DOM is ready
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initParticles);
    } else {
        initParticles();
    }
    
    // Add cinematic classes to elements
    function enhanceElements() {
        // Add enhanced hover to cards
        document.querySelectorAll('.card').forEach(card => {
            if (!card.classList.contains('card-enhanced')) {
                card.classList.add('card-enhanced', 'particle-hover');
            }
        });
        
        // Add 3D effect to buttons
        document.querySelectorAll('.btn').forEach(btn => {
            if (!btn.classList.contains('btn-3d')) {
                btn.classList.add('btn-3d');
            }
        });
        
        // Add page transition
        document.body.classList.add('page-transition');
    }
    
    // Run enhancements
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', enhanceElements);
    } else {
        enhanceElements();
    }
    
})();
