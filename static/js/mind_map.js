document.addEventListener('DOMContentLoaded', () => {
// --- 1. MINDMAP LAYOUT LOGIC ---
    const hub = document.getElementById('hub');
    const cards = document.querySelectorAll('.group-card');
	const totalNodes = cards.length;
    
    // Set Center Point
    const centerX = 5000;
    const centerY = 5000;
    
    hub.style.left = `${centerX}px`;
    hub.style.top = `${centerY}px`;

    const scatteredNodes = [];
    
    // NEW: Define how far apart the centers of the cards must be.
    // If your cards are 150px wide, 250 ensures 100px of empty space between them.
    const minDistance = 400; 
	const radiusExpansion = Math.floor(totalNodes / 10) * 50;

    cards.forEach((card) => {
        let isValidPosition = false;
        let radius, baseAngle, startX, startY;
        let attempts = 0;
        const maxAttempts = 200; // Prevents the browser from freezing if space gets too crowded

        // Keep guessing a random spot until we find an empty one
        while (!isValidPosition && attempts < maxAttempts) {
            // 1. Generate a random guess
            radius = 350 + (Math.random() * 1000) + radiusExpansion; 
            baseAngle = Math.random() * (Math.PI * 2);
            
            // 2. Calculate what the X/Y coordinates would be for this guess
            startX = centerX + Math.cos(baseAngle) * radius;
            startY = centerY + Math.sin(baseAngle) * radius;

            // 3. Check this distance against all cards we've already placed
            isValidPosition = true; // Assume it's good until proven otherwise
            
            for (let i = 0; i < scatteredNodes.length; i++) {
                const existingCard = scatteredNodes[i];
                // Math.hypot calculates the straight-line distance between two points
                const distance = Math.hypot(startX - existingCard.startX, startY - existingCard.startY);
                
                if (distance < minDistance) {
                    isValidPosition = false; // Too close! 
                    break; // Stop checking and immediately try a new random guess
                }
            }
            attempts++;
        }

        // Once we find a valid spot (or hit the attempt limit), save it
        scatteredNodes.push({
            element: card,
            radius: radius,
            baseAngle: baseAngle,
            startX: startX, // Storing these so the next cards can check against them
            startY: startY
        });
    });

    // --- The Orbit Animation Loop ---
    let orbitAngle = 0;
    const rotationSpeed = 0.0005;

    function animateOrbit() {
        orbitAngle += rotationSpeed;

        scatteredNodes.forEach((node) => {
            const currentAngle = node.baseAngle + orbitAngle;
            
            const x = centerX + Math.cos(currentAngle) * node.radius;
            const y = centerY + Math.sin(currentAngle) * node.radius;
            
            node.element.style.left = `${x}px`;
            node.element.style.top = `${y}px`;
        });

        requestAnimationFrame(animateOrbit);
    }

    animateOrbit();


    // --- 2. PAN & ZOOM LOGIC ---
    const viewport = document.getElementById('viewport');
    const canvas = document.getElementById('canvas');
    
    let scale = 1;
    let panX = (window.innerWidth / 2) - centerX;
    let panY = (window.innerHeight / 2) - centerY;

    let isDragging = false;
    let startX, startY;

    updateTransform();

    // -- MOUSE CONTROLS (Desktop) --
    viewport.addEventListener('mousedown', (e) => {
        if(e.target.closest('a')) return; 
        isDragging = true;
        startX = e.clientX - panX;
        startY = e.clientY - panY;
    });

    window.addEventListener('mousemove', (e) => {
        if (!isDragging) return;
        panX = e.clientX - startX;
        panY = e.clientY - startY;
        updateTransform();
    });

    window.addEventListener('mouseup', () => isDragging = false);
    window.addEventListener('mouseleave', () => isDragging = false); 

    viewport.addEventListener('wheel', (e) => {
        e.preventDefault(); 
        const zoomIntensity = 0.002;
        const wheel = e.deltaY < 0 ? 1 : -1;
        applyZoom(wheel * zoomIntensity * 50, e.clientX, e.clientY);
    }, { passive: false });


    // -- NEW: TOUCH CONTROLS (Mobile) --
    let initialPinchDistance = null;

    viewport.addEventListener('touchstart', (e) => {
        // Don't intercept clicks on links or the auth form
        if(e.target.closest('a') || e.target.closest('.auth-box')) return; 
        
        if (e.touches.length === 1) {
            // One finger: Pan
            isDragging = true;
            startX = e.touches[0].clientX - panX;
            startY = e.touches[0].clientY - panY;
        } else if (e.touches.length === 2) {
            // Two fingers: Setup Pinch
            isDragging = false; 
            initialPinchDistance = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );
        }
    }, { passive: false });

    viewport.addEventListener('touchmove', (e) => {
        // Crucial: stops the browser from pull-to-refresh or bouncing the page
        e.preventDefault(); 

        if (e.touches.length === 1 && isDragging) {
            panX = e.touches[0].clientX - startX;
            panY = e.touches[0].clientY - startY;
            updateTransform();
        } else if (e.touches.length === 2 && initialPinchDistance) {
            const currentDistance = Math.hypot(
                e.touches[0].clientX - e.touches[1].clientX,
                e.touches[0].clientY - e.touches[1].clientY
            );

            // Calculate how much they pinched in/out
            const pinchRatio = currentDistance / initialPinchDistance;
            
            // Find the exact midpoint between their two fingers
            const midX = (e.touches[0].clientX + e.touches[1].clientX) / 2;
            const midY = (e.touches[0].clientY + e.touches[1].clientY) / 2;

            applyPinchZoom(pinchRatio, midX, midY);
            
            // Reset for the next frame of movement
            initialPinchDistance = currentDistance; 
        }
    }, { passive: false });

    viewport.addEventListener('touchend', (e) => {
        if (e.touches.length < 2) {
            initialPinchDistance = null; // Kill the pinch tracking
        }
        if (e.touches.length === 0) {
            isDragging = false;
        } else if (e.touches.length === 1) {
            // If they lift one finger but leave the other down, seamlessly switch back to panning
            isDragging = true;
            startX = e.touches[0].clientX - panX;
            startY = e.touches[0].clientY - panY;
        }
    });

    // --- Helper Functions ---
    function applyZoom(delta, mouseX, mouseY) {
        let newScale = scale * Math.exp(delta);
        finalizeZoom(newScale, mouseX, mouseY);
    }

    function applyPinchZoom(ratio, midX, midY) {
        let newScale = scale * ratio;
        finalizeZoom(newScale, midX, midY);
    }

    function finalizeZoom(newScale, focalX, focalY) {
        newScale = Math.min(Math.max(0.15, newScale), 3); // Allow zooming a bit further out (0.15) for large graphs
        
        const rect = viewport.getBoundingClientRect();
        const targetX = focalX - rect.left;
        const targetY = focalY - rect.top;

        // Shift the pan so the focal point stays exactly under the mouse/fingers
        panX = targetX - (targetX - panX) * (newScale / scale);
        panY = targetY - (targetY - panY) * (newScale / scale);
        scale = newScale;

        updateTransform();
    }

    function updateTransform() {
        // Use translate3d to force hardware acceleration on mobile
        canvas.style.transform = `translate3d(${panX}px, ${panY}px, 0) scale(${scale})`;
    }
});