document.addEventListener("DOMContentLoaded", function() {
    // Add to Watchlist
    document.body.addEventListener("click", function(event) {
        if (event.target.classList.contains("add-watchlist")) {
            const button = event.target;
            const movieData = {
                title: button.getAttribute("data-title"),
                poster: button.getAttribute("data-poster"),
                rating: button.getAttribute("data-rating"),
                genre: button.getAttribute("data-genre")
            };

            fetch("/add_watchlist", {
                method: "POST",
                body: JSON.stringify(movieData),
                headers: { "Content-Type": "application/json" }
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                button.textContent = "✔ Added"; // Update button text after adding
                button.disabled = true; // Prevent duplicate additions
                button.style.backgroundColor = "#28a745";
            })
            .catch(error => console.error("Error:", error));
        }
    });

    // Remove from Watchlist
    document.body.addEventListener("click", function(event) {
        if (event.target.classList.contains("remove-watchlist")) {
            const button = event.target;
            const movieId = button.getAttribute("data-id");

            fetch(`/remove_watchlist/${movieId}`, {
                method: "POST"
            })
            .then(response => response.json())
            .then(data => {
                alert(data.message);
                button.closest(".movie-card").remove(); // Remove the movie card from UI
            })
            .catch(error => console.error("Error:", error));
        }
    });
});
