document.addEventListener('DOMContentLoaded', () => {
    // Scene Setup
    const canvas = document.querySelector('#bg-canvas');
    const scene = new THREE.Scene();
    
    // Optional: Add some dark fog to fade distant stars into the void
    scene.fog = new THREE.FogExp2(0x000000, 0.02);
	scene.background = new THREE.Color(0xffffff);

    const camera = new THREE.PerspectiveCamera(75, window.innerWidth / window.innerHeight, 0.1, 1000);
    camera.position.z = 10;

    const renderer = new THREE.WebGLRenderer({ canvas: canvas, alpha: true, antialias: true });
    renderer.setSize(window.innerWidth, window.innerHeight);
    renderer.setPixelRatio(window.devicePixelRatio);

	// --- Create the Starfield ---
	const starGeometry = new THREE.BufferGeometry();
	const starCount = 10000;
	const posArray = new Float32Array(starCount * 3);
	const colors = new Float32Array(starCount * 3);

	// 1. Define your specific palette (RGB values from 0 to 1)
	const palette = [
		[1.0, 1.0, 1.0], // White
		[1.0, 0, 0], // Red
		[0, 1.0, 0], // Green
		[0, 0, 1]  // Blue
	];

	for (let i = 0; i < starCount; i++) {
		// Random position
		posArray[i * 3] = (Math.random() - 0.5) * 200;
		posArray[i * 3 + 1] = (Math.random() - 0.5) * 200;
		posArray[i * 3 + 2] = (Math.random() - 0.5) * 200;

		// 2. Select a random index from our palette
		const color = palette[Math.floor(Math.random() * palette.length)];

		// 3. Assign RGB values
		colors[i * 3] = color[0];     // Red
		colors[i * 3 + 1] = color[1]; // Green
		colors[i * 3 + 2] = color[2]; // Blue
	}

	starGeometry.setAttribute('position', new THREE.BufferAttribute(posArray, 3));
	starGeometry.setAttribute('color', new THREE.BufferAttribute(colors, 3));

	const starMaterial = new THREE.PointsMaterial({
		size: 0.5,
		vertexColors: true,
		transparent: true,
		opacity: 0.8,
		sizeAttenuation: true
	});

    const starMesh = new THREE.Points(starGeometry, starMaterial);
    scene.add(starMesh);

    // --- Animation Loop ---
    function animate() {
        requestAnimationFrame(animate);

        // Slowly rotate the entire galaxy of stars
        starMesh.rotation.y += 0.0001;
        starMesh.rotation.x += 0.0001;

        renderer.render(scene, camera);
    }
    animate();

    // --- Handle Window Resizing smoothly ---
    window.addEventListener('resize', () => {
        camera.aspect = window.innerWidth / window.innerHeight;
        camera.updateProjectionMatrix();
        renderer.setSize(window.innerWidth, window.innerHeight);
    });
});