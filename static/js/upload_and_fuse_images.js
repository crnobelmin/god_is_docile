document.addEventListener('DOMContentLoaded', () => {
	const portraitInput = document.getElementById('portraitInput');
	if (portraitInput) { // Only run if the input actually exists on the page
		portraitInput.addEventListener('change', (event) => {
			// Grab the files directly from the event target (the input)
			const files = event.target.files;
			
			// If the user opens the file dialog but clicks "Cancel", files.length will be 0.
			// We just return silently instead of showing an alert.
			if (files.length === 0) {
				return;
			}

			// Create FormData object to send files
			const formData = new FormData();
			for (let i = 0; i < files.length; i++) {
				formData.append('portraits', files[i]);
			}

			// Optional UI enhancement: You could show a loading spinner here or change text
			// console.log("Uploading and fusing...");

			// 1. Upload the files
			fetch(`/gallery/${groupName}/upload_portraits`, {
				method: 'POST',
				body: formData // Browser automatically sets Content-Type: multipart/form-data
			})
			.then(response => {
				if (!response.ok) throw new Error('Upload failed');
				// 2. Trigger the fusion process
				return fetch(`/gallery/${groupName}/create_fused_portrait`, { method: 'POST' });
			})
			.then(response => {
				if (!response.ok) throw new Error('Fusion failed');
				console.log("Portraits uploaded and fused successfully!");
				window.location.reload(); // Refresh the page to see the new fused portrait
			})
			.catch(error => {
				console.error('Error:', error);
				alert('Failed to process portraits.');
			});
		});
	}
});