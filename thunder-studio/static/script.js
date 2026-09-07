// Thunder Studio

document.addEventListener('DOMContentLoaded', () => {
    // Re-trigger lightning on tab return
    const bolt = document.querySelector('.bolt');
    document.addEventListener('visibilitychange', () => {
        if (document.visibilityState === 'visible' && bolt) {
            bolt.style.animation = 'none';
            void bolt.offsetWidth;
            bolt.style.animation = '';
        }
    });
});

// Mobile nav toggle
function toggleMenu() {
    const links = document.querySelector('.nav-links');
    if (links) links.classList.toggle('open');
}
