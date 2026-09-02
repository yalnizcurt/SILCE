// Viewport Auto-Scaling Logic for 1920x1080 Slide Sheets

document.addEventListener('DOMContentLoaded', () => {
    const wrappers = document.querySelectorAll('.slide-wrapper');
    
    function handleScaling() {
        if (!wrappers || wrappers.length === 0) return;

        // If printing, bypass transformations to preserve raw 1920x1080 dimensions
        if (window.matchMedia('print').matches) {
            wrappers.forEach(w => {
                w.style.transform = 'none';
            });
            return;
        }

        const targetWidth = 1920;
        const targetHeight = 1080;

        const scaleX = window.innerWidth / targetWidth;
        const scaleY = window.innerHeight / targetHeight;
        
        // Scale down or up proportionally to perfectly fit the screen window
        const scaleFactor = Math.min(scaleX, scaleY);

        wrappers.forEach(w => {
            w.style.transform = `scale(${scaleFactor})`;
            w.style.transformOrigin = 'center center';
        });
    }

    // Initialize scaling listeners
    window.addEventListener('resize', handleScaling);
    window.addEventListener('load', handleScaling);
    handleScaling();
});
