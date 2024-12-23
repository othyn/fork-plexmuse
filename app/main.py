"""
Plexmuse API

This module sets up the FastAPI application for generating AI-powered playlists
from your Plex music library. It includes configuration for logging, environment
variables, and CORS middleware.
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
    allow_origins=["*"],  # Adjust this in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize services
plex_service = PlexService(base_url=os.getenv("PLEX_BASE_URL"), token=os.getenv("PLEX_TOKEN"))

llm_service = LLMService(openai_key=os.getenv("OPENAI_API_KEY"), anthropic_key=os.getenv("ANTHROPIC_API_KEY"))


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy"}


@app.get("/artists", response_model=List[Artist])
async def get_artists():
    """Get all artists from the Plex music library"""
    try:
        artists = plex_service.get_all_artists()
        return artists
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@app.post("/recommendations", response_model=PlaylistResponse)
async def create_recommendations(request: PlaylistRequest):
    """
    Create playlist recommendations based on the provided prompt and model.

    Args:
        request (PlaylistRequest): The request object containing the prompt and model.

    Returns:
        PlaylistResponse: The response object containing the recommended playlist.
    """
    try:
        # Step 1: Get artist recommendations
        artists = plex_service.get_all_artists()
        recommended_artists = llm_service.get_artist_recommendations(
            prompt=request.prompt, artists=artists, model=request.model
        )

        # Step 2: Get all tracks for recommended artists
        artist_tracks = {}
        for artist in recommended_artists:
            artist_tracks.update(plex_service.get_artist_tracks(artist))

        # Step 3: Get specific track recommendations
        track_recommendations = llm_service.get_track_recommendations(
            prompt=request.prompt, artist_tracks=artist_tracks, model=request.model
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
