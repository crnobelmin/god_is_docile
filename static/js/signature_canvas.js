window.addEventListener('load', () => { 
    const canvas = document.getElementById('sigCanvas');
    if (!canvas) return; // Stop the script entirely if there's no canvas!
    
    const ctx = canvas.getContext('2d');
    const saveBtn = document.getElementById('saveSigBtn');
    
    // Set internal resolution to match displayed size NOW that the image has loaded
    canvas.width = canvas.getBoundingClientRect().width;
    canvas.height = canvas.getBoundingClientRect().height;

    // Brush Settings
    ctx.lineWidth = 8;
    ctx.lineCap = 'round';
    ctx.lineJoin = 'round';
	ctx.strokeStyle = '#FFFFFF';
	
// --- ROTATION & RESIZE HANDLING ---
    function handleResize() {
        // 1. Save whatever the user has already drawn
        const currentDrawing = canvas.toDataURL();

        // 2. Create a temporary image object to hold our snapshot
        const tempImg = new Image();
        tempImg.src = currentDrawing;

        tempImg.onload = () => {
            // 3. Update the internal resolution to match the newly rotated screen
            const rect = canvas.getBoundingClientRect();
            canvas.width = rect.width;
            canvas.height = rect.height;

            // 4. CRITICAL: Re-apply brush settings (resizing completely wipes these out)
            ctx.lineWidth = 20;
            ctx.lineCap = 'round';
            ctx.lineJoin = 'round';
            ctx.strokeStyle = '#FFFFFF';

            // 5. Paste the snapshot back onto the canvas
            // Note: We stretch it slightly to fit the new dimensions so it doesn't get clipped
            ctx.drawImage(tempImg, 0, 0, canvas.width, canvas.height);
        };
    }

    // Listen for window resizing (desktop)
    window.addEventListener('resize', handleResize);
    
    // Listen specifically for mobile rotation
    window.addEventListener('orientationchange', () => {
        // Phones take a split second to recalculate their layout after rotating.
        // A 100ms delay ensures we grab the correct new dimensions.
        setTimeout(handleResize, 100); 
    });
	
    
// 2. Drawing Logic
    let drawing = false;

    // Helper function to get exact X/Y for both Mouse and Touch
    function getPointerPos(e) {
        const rect = canvas.getBoundingClientRect();
        // If it's a touch event, look at the first finger [0]
        if (e.touches && e.touches.length > 0) {
            return {
                x: e.touches[0].clientX - rect.left,
                y: e.touches[0].clientY - rect.top
            };
        }
        // If it's a mouse event
        return {
            x: e.clientX - rect.left,
            y: e.clientY - rect.top
        };
    }

    // --- START DRAWING ---
    function startDrawing(e) {
        e.preventDefault(); // Stop default browser behaviors
        drawing = true; 
        const pos = getPointerPos(e);
        ctx.beginPath();
        ctx.moveTo(pos.x, pos.y);
    }

    // --- STOP DRAWING ---
    function stopDrawing() {
        drawing = false; 
    }

    // --- DRAWING MOTION ---
    function draw(e) {
        if (!drawing) return;
        e.preventDefault(); // Crucial: Stops the page from pulling/bouncing on mobile
        const pos = getPointerPos(e);
        ctx.lineTo(pos.x, pos.y);
        ctx.stroke();
    }

    // Attach Mouse Events (Desktop)
    canvas.addEventListener('mousedown', startDrawing);
    canvas.addEventListener('mouseup', stopDrawing);
    canvas.addEventListener('mousemove', draw);
    canvas.addEventListener('mouseleave', stopDrawing); // Stops drawing if mouse leaves canvas

    // Attach Touch Events (Mobile)
    canvas.addEventListener('touchstart', startDrawing, { passive: false });
    canvas.addEventListener('touchend', stopDrawing);
    canvas.addEventListener('touchcancel', stopDrawing);
    canvas.addEventListener('touchmove', draw, { passive: false });

    // 3. Upload & Fusion Logic
    saveBtn.addEventListener('click', () => {
        const imageData = canvas.toDataURL('image/png');

        fetch(`/gallery/${groupName}/upload_signature`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        })
        .then(response => {
            if (!response.ok) throw new Error('Upload failed');
            return fetch(`/gallery/${groupName}/fuse_signatures`, { method: 'POST' });
        })
        .then(response => {
            if (!response.ok) throw new Error('Fusion failed');
            
            const maskElement = document.getElementById('maskedPhoto');
            const timestamp = new Date().getTime();
            const newMaskUrl = `/gallery/${groupName}/signatures/fused_signatures.png?t=${timestamp}`;
            
            maskElement.style.webkitMaskImage = `url('${newMaskUrl}')`;
            maskElement.style.maskImage = `url('${newMaskUrl}')`;
            
            console.log("Signature uploaded and fused successfully!");
            window.location.reload(); 
        })
        .catch(error => {
            console.error('Error:', error);
            alert('Something went wrong. Please try again.');
        });
    });
});
