"""
Plexmuse API with initialization
"""

import logging
import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.models import Artist, PlaylistRequest, PlaylistResponse

from .services.llm_service import LLMService
from .services.plex_service import PlexService

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="Plexmuse API",
    description="API for generating AI-powered playlists from your Plex music library",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
plex_service = PlexService(base_url=os.getenv("PLEX_BASE_URL"), token=os.getenv("PLEX_TOKEN"))
plex_service.initialize(app)

llm_service = LLMService()


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "cache_size": plex_service.get_cache_size()}


@app.get("/artists", response_model=List[Artist])
async def get_artists():
    """Get all artists from the Plex music library"""
    return plex_service.get_all_artists()


@app.post("/recommendations", response_model=PlaylistResponse)
async def create_recommendations(request: PlaylistRequest):
    """Create playlist recommendations"""
    try:
        # Step 1: Get artist recommendations from cached artists
        artists = plex_service.get_all_artists()
        recommended_artists = llm_service.get_artist_recommendations(
            prompt=request.prompt, artists=artists, model=request.model
        )

        # Step 2: Get all recommended artists' albums in one call
        artist_albums = plex_service.get_artists_albums_bulk(recommended_artists)

        # Step 3: Get track recommendations
        track_recommendations = llm_service.get_track_recommendations(
            prompt=request.prompt,
            artist_tracks=artist_albums,
            model=request.model,
            min_tracks=request.min_tracks,
            max_tracks=request.max_tracks,
        )

        # Step 4: Generate playlist name
        playlist_name = llm_service.generate_playlist_name(prompt=request.prompt, model=request.model)

        # Step 5: Create the playlist
        playlist = plex_service.create_curated_playlist(
            name=playlist_name,
            track_recommendations=track_recommendations,
        )
        playlist_items = list(playlist.items()) if hasattr(playlist, "items") else []

        return PlaylistResponse(
            name=playlist.title,
            track_count=len(playlist_items),
            artists=recommended_artists,
            id=str(playlist.ratingKey) if hasattr(playlist, "ratingKey") else None,
        )
    except Exception as e:
        logger.error("Error creating playlist: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e
