function triggerPlay(event, groupName) {
    // 1. Stop the browser from trying to follow the href="#" link
    event.preventDefault(); 
    
    // 2. Fire the background POST request to your Flask API
    fetch(`/api/play/${groupName}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        }
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === "success") {
            console.log("Sequence started successfully:", data.message);
            // Optional: Add code here to turn the button green or show a visual "Playing" indicator
        } else {
            alert("Error starting playback: " + data.message);
        }
    })
    .catch(error => {
        console.error("Network error talking to Kustos server:", error);
    });
}