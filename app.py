from flask import Flask, render_template, request, jsonify
import google.generativeai as genai
import requests
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate  # Flask-Migrate for handling schema changes
from config import GEMINI_API_KEY, TMDB_API_KEY

# Initialize Flask app
app = Flask(__name__)

# Configure Database
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///movies.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Initialize Database & Migration
db = SQLAlchemy(app)
migrate = Migrate(app, db)  # Enables migrations

# Configure Gemini AI
genai.configure(api_key=GEMINI_API_KEY)

# User Watchlist Model
class Watchlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), unique=True, nullable=False)
    poster = db.Column(db.String(255))
    rating = db.Column(db.Float)
    genre = db.Column(db.String(50))
    popularity = db.Column(db.Float, default=0.0)  # Ensures it exists
    release_year = db.Column(db.Integer)
    language = db.Column(db.String(20))
    cast = db.Column(db.String(255))

def get_movie_recommendations(user_query, genre_filter=None):
    """Fetch movie recommendations using Gemini AI."""
    model = genai.GenerativeModel("gemini-pro")
    query = f"Recommend 10 {genre_filter} movies" if genre_filter else "Recommend 10 movies"
    
    try:
        response = model.generate_content(
            query + f" based on: {user_query}. Provide only movie names, separated by commas."
        )

        if response and response.text:
            movie_names = list(set(response.text.split(", ")))  # Remove duplicates
            return [name.strip() for name in movie_names if name]  # Remove empty entries
    except Exception as e:
        print(f"Error fetching recommendations: {e}")
    
    return []

def get_movie_details(movie_name):
    """Fetch movie details from TMDb including YouTube trailer."""
    search_url = f"https://api.themoviedb.org/3/search/movie?api_key={TMDB_API_KEY}&query={movie_name}"
    
    try:
        response = requests.get(search_url).json()
        if not response.get("results"):
            return None

        movie = response["results"][0]
        movie_id = movie["id"]

        # Fetch additional movie details including credits and videos (for trailer)
        details_url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=credits,videos"
        details_response = requests.get(details_url).json()

        # Extract top 5 cast members
        top_cast = ", ".join([actor["name"] for actor in details_response.get("credits", {}).get("cast", [])[:5]])

        # Extract YouTube trailer key (first official trailer)
        trailer_key = None
        for video in details_response.get("videos", {}).get("results", []):
            if video["type"] == "Trailer" and video["site"] == "YouTube":
                trailer_key = video["key"]
                break

        return {
            "title": movie.get("title", "Unknown"),
            "poster": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else "https://via.placeholder.com/200x300",
            "rating": movie.get("vote_average", "N/A"),
            "genre": ", ".join([genre["name"] for genre in details_response.get("genres", [])]) if details_response.get("genres") else "N/A",
            "popularity": movie.get("popularity", "N/A"),
            "release_year": details_response.get("release_date", "N/A")[:4] if details_response.get("release_date") else "N/A",
            "language": details_response.get("original_language", "N/A"),
            "cast": top_cast if top_cast else "N/A",
            "trailer": f"https://www.youtube.com/embed/{trailer_key}" if trailer_key else None  # Full YouTube URL
        }
    except Exception as e:
        print(f"Error fetching movie details for {movie_name}: {e}")
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        user_query = request.form["query"]
        genre_filter = request.form.get("genre")
        movie_names = get_movie_recommendations(user_query, genre_filter)

        # Fetch details for each recommended movie
        movies = [get_movie_details(name) for name in movie_names]
        movies = [movie for movie in movies if movie]  # Remove None values

        return render_template("recommendations.html", query=user_query, movies=movies, genres=["Action", "Comedy", "Drama", "Sci-Fi", "Horror"])

    return render_template("index.html", genres=["Action", "Comedy", "Drama", "Sci-Fi", "Horror"])

@app.route("/watchlist", methods=["GET"])
def watchlist():
    """View saved watchlist."""
    movies = Watchlist.query.all()
    return render_template("watchlist.html", movies=movies)

@app.route("/add_watchlist", methods=["POST"])
def add_watchlist():
    """Add movie to watchlist."""
    data = request.get_json()
    print("Received Data:", data)  # Debugging: See what data is received

    # Ensure required fields are present with defaults
    title = data.get("title", "Unknown")
    poster = data.get("poster", "https://via.placeholder.com/200x300")
    rating = data.get("rating", "N/A")
    genre = data.get("genre", "N/A")
    popularity = data.get("popularity", 0.0)
    release_year = data.get("release_year", "Unknown")  # 🔹 Use default if missing
    language = data.get("language", "N/A")
    cast = data.get("cast", "N/A")

    # Check if the movie already exists
    existing_movie = Watchlist.query.filter_by(title=title).first()
    if existing_movie:
        return jsonify({"message": "Movie already in watchlist!"})

    movie = Watchlist(
        title=title,
        poster=poster,
        rating=rating,
        genre=genre,
        popularity=popularity,
        release_year=release_year,
        language=language,
        cast=cast
    )

    db.session.add(movie)
    db.session.commit()
    return jsonify({"message": "Added to watchlist!"})


@app.route("/remove_watchlist/<int:id>", methods=["POST"])
def remove_watchlist(id):
    """Remove movie from watchlist."""
    movie = Watchlist.query.get(id)
    if movie:
        db.session.delete(movie)
        db.session.commit()
        return jsonify({"message": "Removed from watchlist!"})
    return jsonify({"error": "Movie not found"}), 404

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Ensures tables are created if missing
    app.run(debug=True)
