// DOM elements
const form = document.getElementById('playlistForm');
const loadingState = document.getElementById('loadingState');
const results = document.getElementById('results');
const playlistName = document.getElementById('playlistName');
const artistsList = document.getElementById('artistsList');
const trackCount = document.getElementById('trackCount');
const plexLink = document.getElementById('plexLink');

// Handle form submission
form.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Show loading state
    loadingState.classList.remove('hidden');
    results.classList.add('hidden');

    // Get form data
    const prompt = document.getElementById('prompt').value;

    try {
        const response = await fetch('/recommendations', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                prompt,
                model: 'gpt-4',
                min_tracks: 30,
                max_tracks: 50
            }),
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();

        // Update UI with results
        playlistName.textContent = data.name;
        artistsList.innerHTML = data.artists
            .map(artist => `<li>${artist}</li>`)
            .join('');
        trackCount.textContent = `${data.track_count} tracks added to playlist`;

        // Update Plex link if ID is available
        if (data.id) {
            // You might need to adjust this URL based on your Plex server configuration
            plexLink.href = `${window.location.protocol}//${window.location.hostname}:32400/playlists/${data.id}`;
        }

        // Show results
        results.classList.remove('hidden');
    } catch (error) {
        console.error('Error:', error);
        alert('Failed to generate playlist. Please try again.');
    } finally {
        loadingState.classList.add('hidden');
    }
});
