/**
 * UX Enhancements Package
 * - Dark/Light Theme Toggle
 * - Sound Effects
 * - Animated Transitions
 * - Keyboard Shortcuts
 * Version: 1.0.0
 */

// ============================================================
// THEME SYSTEM
// ============================================================
class ThemeManager {
    constructor() {
        this.currentTheme = localStorage.getItem('theme') || 'dark';
        this.init();
    }

    init() {
        this.applyTheme(this.currentTheme);
        this.createToggleButton();
    }

    applyTheme(theme) {
        document.documentElement.setAttribute('data-theme', theme);
        localStorage.setItem('theme', theme);
        this.currentTheme = theme;
        
        // Update theme colors
        const root = document.documentElement;
        if (theme === 'light') {
            root.style.setProperty('--bg-primary', '#ffffff');
            root.style.setProperty('--bg-secondary', '#f5f5f5');
            root.style.setProperty('--text-primary', '#000000');
            root.style.setProperty('--text-secondary', '#666666');
            root.style.setProperty('--border-color', 'rgba(0, 0, 0, 0.1)');
        } else {
            root.style.setProperty('--bg-primary', '#0a0a0a');
            root.style.setProperty('--bg-secondary', '#1a1a1a');
            root.style.setProperty('--text-primary', '#ffffff');
            root.style.setProperty('--text-secondary', 'rgba(255, 255, 255, 0.7)');
            root.style.setProperty('--border-color', 'rgba(255, 255, 255, 0.1)');
        }
    }

    toggle() {
        const newTheme = this.currentTheme === 'dark' ? 'light' : 'dark';
        this.applyTheme(newTheme);
        
        // Play sound
        if (window.soundManager) {
            window.soundManager.play('click');
        }
    }

    createToggleButton() {
        const button = document.createElement('button');
        button.id = 'theme-toggle';
        button.innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
        button.title = 'Toggle Theme';
        button.style.cssText = `
            position: fixed;
            top: 60px;
            right: 10px;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            color: #ffd700;
            font-size: 20px;
            cursor: pointer;
            z-index: 9999;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        button.addEventListener('click', () => {
            this.toggle();
            button.innerHTML = this.currentTheme === 'dark' ? '☀️' : '🌙';
        });
        
        button.addEventListener('mouseenter', () => {
            button.style.transform = 'scale(1.1) rotate(20deg)';
        });
        
        button.addEventListener('mouseleave', () => {
            button.style.transform = 'scale(1) rotate(0deg)';
        });
        
        document.body.appendChild(button);
    }
}

// ============================================================
// SOUND EFFECTS SYSTEM
// ============================================================
class SoundManager {
    constructor() {
        this.enabled = localStorage.getItem('soundEnabled') !== 'false';
        this.volume = parseFloat(localStorage.getItem('soundVolume') || '0.5');
        this.sounds = {};
        this.init();
    }

    init() {
        // Create audio context
        this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
        
        // Define sound effects using Web Audio API
        this.soundDefinitions = {
            bid: { frequency: 800, duration: 0.1, type: 'sine' },
            sold: { frequency: 1200, duration: 0.3, type: 'square' },
            unsold: { frequency: 400, duration: 0.2, type: 'sawtooth' },
            timer: { frequency: 600, duration: 0.05, type: 'sine' },
            click: { frequency: 1000, duration: 0.05, type: 'sine' },
            notification: { frequency: 880, duration: 0.15, type: 'triangle' },
            success: { frequency: 1400, duration: 0.2, type: 'sine' },
            error: { frequency: 300, duration: 0.3, type: 'square' }
        };
        
        this.createControlButton();
    }

    play(soundName) {
        if (!this.enabled || !this.soundDefinitions[soundName]) return;
        
        const def = this.soundDefinitions[soundName];
        const oscillator = this.audioContext.createOscillator();
        const gainNode = this.audioContext.createGain();
        
        oscillator.connect(gainNode);
        gainNode.connect(this.audioContext.destination);
        
        oscillator.type = def.type;
        oscillator.frequency.value = def.frequency;
        
        gainNode.gain.setValueAtTime(this.volume, this.audioContext.currentTime);
        gainNode.gain.exponentialRampToValueAtTime(0.01, this.audioContext.currentTime + def.duration);
        
        oscillator.start(this.audioContext.currentTime);
        oscillator.stop(this.audioContext.currentTime + def.duration);
    }

    toggle() {
        this.enabled = !this.enabled;
        localStorage.setItem('soundEnabled', this.enabled);
        this.play('click');
    }

    setVolume(volume) {
        this.volume = Math.max(0, Math.min(1, volume));
        localStorage.setItem('soundVolume', this.volume);
    }

    createControlButton() {
        const button = document.createElement('button');
        button.id = 'sound-toggle';
        button.innerHTML = this.enabled ? '🔊' : '🔇';
        button.title = 'Toggle Sound';
        button.style.cssText = `
            position: fixed;
            top: 110px;
            right: 10px;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            color: #ffd700;
            font-size: 20px;
            cursor: pointer;
            z-index: 9999;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        `;
        
        button.addEventListener('click', () => {
            this.toggle();
            button.innerHTML = this.enabled ? '🔊' : '🔇';
        });
        
        button.addEventListener('mouseenter', () => {
            button.style.transform = 'scale(1.1)';
        });
        
        button.addEventListener('mouseleave', () => {
            button.style.transform = 'scale(1)';
        });
        
        document.body.appendChild(button);
    }
}

// ============================================================
// ANIMATION SYSTEM
// ============================================================
class AnimationManager {
    constructor() {
        this.init();
    }

    init() {
        this.addGlobalStyles();
        this.observeElements();
    }

    addGlobalStyles() {
        const style = document.createElement('style');
        style.textContent = `
            /* Fade in animation */
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(20px); }
                to { opacity: 1; transform: translateY(0); }
            }

            /* Slide in from right */
            @keyframes slideInRight {
                from { opacity: 0; transform: translateX(50px); }
                to { opacity: 1; transform: translateX(0); }
            }

            /* Bounce animation */
            @keyframes bounce {
                0%, 100% { transform: translateY(0); }
                50% { transform: translateY(-10px); }
            }

            /* Pulse animation */
            @keyframes pulse {
                0%, 100% { transform: scale(1); }
                50% { transform: scale(1.05); }
            }

            /* Shake animation */
            @keyframes shake {
                0%, 100% { transform: translateX(0); }
                25% { transform: translateX(-10px); }
                75% { transform: translateX(10px); }
            }

            /* Glow animation */
            @keyframes glow {
                0%, 100% { box-shadow: 0 0 5px rgba(255, 215, 0, 0.5); }
                50% { box-shadow: 0 0 20px rgba(255, 215, 0, 0.8); }
            }

            /* Apply animations */
            .animate-fade-in {
                animation: fadeIn 0.5s ease-out;
            }

            .animate-slide-in {
                animation: slideInRight 0.5s ease-out;
            }

            .animate-bounce {
                animation: bounce 0.6s ease-in-out;
            }

            .animate-pulse {
                animation: pulse 1s ease-in-out infinite;
            }

            .animate-shake {
                animation: shake 0.5s ease-in-out;
            }

            .animate-glow {
                animation: glow 2s ease-in-out infinite;
            }

            /* Smooth transitions for all interactive elements */
            button, .btn, .card, .player-card, .player-card-admin {
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }

            /* Hover effects */
            button:hover, .btn:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }

            button:active, .btn:active {
                transform: translateY(0);
            }
        `;
        document.head.appendChild(style);
    }

    observeElements() {
        // Observe new elements and animate them
        const observer = new IntersectionObserver((entries) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('animate-fade-in');
                }
            });
        }, { threshold: 0.1 });

        // Observe player cards
        document.querySelectorAll('.player-card, .player-card-admin').forEach(card => {
            observer.observe(card);
        });
    }

    animate(element, animationName) {
        element.classList.add(`animate-${animationName}`);
        element.addEventListener('animationend', () => {
            element.classList.remove(`animate-${animationName}`);
        }, { once: true });
    }
}

// ============================================================
// KEYBOARD SHORTCUTS
// ============================================================
class KeyboardShortcuts {
    constructor() {
        this.shortcuts = {
            '?': () => this.showHelp(),
            '/': () => this.focusSearch(),
            'Escape': () => this.closeModals(),
            't': () => window.themeManager?.toggle(),
            's': () => window.soundManager?.toggle(),
            'r': () => location.reload(),
            'h': () => window.location.href = '/',
            'a': () => this.navigateTo('/admin'),
            'd': () => this.navigateTo('/dashboard')
        };
        this.init();
    }

    init() {
        document.addEventListener('keydown', (e) => {
            // Don't trigger if user is typing in an input
            if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') {
                return;
            }

            const key = e.key;
            if (this.shortcuts[key]) {
                e.preventDefault();
                this.shortcuts[key]();
            }
        });

        this.createHelpButton();
    }

    showHelp() {
        const modal = document.createElement('div');
        modal.id = 'keyboard-shortcuts-modal';
        modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.9);
            backdrop-filter: blur(10px);
            z-index: 10000;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s ease-out;
        `;

        modal.innerHTML = `
            <div style="background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%); padding: 2rem; border-radius: 20px; max-width: 500px; border: 1px solid rgba(255, 215, 0, 0.3);">
                <h2 style="color: #ffd700; margin-bottom: 1.5rem; text-align: center;">⌨️ Keyboard Shortcuts</h2>
                <div style="display: grid; gap: 1rem; color: #fff;">
                    <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 8px;">
                        <span><kbd style="background: #333; padding: 4px 8px; border-radius: 4px;">?</kbd></span>
                        <span>Show this help</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 8px;">
                        <span><kbd style="background: #333; padding: 4px 8px; border-radius: 4px;">/</kbd></span>
                        <span>Focus search</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 8px;">
                        <span><kbd style="background: #333; padding: 4px 8px; border-radius: 4px;">Esc</kbd></span>
                        <span>Close modals</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 8px;">
                        <span><kbd style="background: #333; padding: 4px 8px; border-radius: 4px;">T</kbd></span>
                        <span>Toggle theme</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 8px;">
                        <span><kbd style="background: #333; padding: 4px 8px; border-radius: 4px;">S</kbd></span>
                        <span>Toggle sound</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 8px;">
                        <span><kbd style="background: #333; padding: 4px 8px; border-radius: 4px;">R</kbd></span>
                        <span>Reload page</span>
                    </div>
                    <div style="display: flex; justify-content: space-between; padding: 0.5rem; background: rgba(255, 255, 255, 0.05); border-radius: 8px;">
                        <span><kbd style="background: #333; padding: 4px 8px; border-radius: 4px;">H</kbd></span>
                        <span>Go to home</span>
                    </div>
                </div>
                <button onclick="document.getElementById('keyboard-shortcuts-modal').remove()" style="margin-top: 1.5rem; width: 100%; padding: 0.75rem; background: #ffd700; color: #000; border: none; border-radius: 10px; font-weight: bold; cursor: pointer;">
                    Got it!
                </button>
            </div>
        `;

        modal.addEventListener('click', (e) => {
            if (e.target === modal) {
                modal.remove();
            }
        });

        document.body.appendChild(modal);
    }

    focusSearch() {
        const searchInput = document.querySelector('input[type="text"], input[type="search"]');
        if (searchInput) {
            searchInput.focus();
        }
    }

    closeModals() {
        document.querySelectorAll('.modal, [id$="-modal"]').forEach(modal => {
            modal.remove();
        });
    }

    navigateTo(path) {
        window.location.href = path;
    }

    createHelpButton() {
        const button = document.createElement('button');
        button.innerHTML = '⌨️';
        button.title = 'Keyboard Shortcuts (?)';
        button.style.cssText = `
            position: fixed;
            top: 160px;
            right: 10px;
            width: 40px;
            height: 40px;
            border-radius: 50%;
            border: 1px solid rgba(255, 255, 255, 0.2);
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(10px);
            color: #ffd700;
            font-size: 20px;
            cursor: pointer;
            z-index: 9999;
            transition: all 0.3s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        button.addEventListener('click', () => this.showHelp());
        button.addEventListener('mouseenter', () => {
            button.style.transform = 'scale(1.1)';
        });
        button.addEventListener('mouseleave', () => {
            button.style.transform = 'scale(1)';
        });

        document.body.appendChild(button);
    }
}

// ============================================================
// INITIALIZE ALL SYSTEMS
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
    window.themeManager = new ThemeManager();
    window.soundManager = new SoundManager();
    window.animationManager = new AnimationManager();
    window.keyboardShortcuts = new KeyboardShortcuts();
    
    console.log('🎨 UX Enhancements loaded!');
});
