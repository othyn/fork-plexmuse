from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from .models import Artist, PlaylistResponse, PlaylistRequest
from typing import List
import os
import logging
from dotenv import load_dotenv
from .services.plex_service import PlexService
from .services.llm_service import LLMService

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(
    title="Plex GPT Playlist API",
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
plex_service = PlexService(
    base_url=os.getenv('PLEX_BASE_URL'),
    token=os.getenv('PLEX_TOKEN')
)

llm_service = LLMService(openai_key=os.getenv('OPENAI_API_KEY'), anthropic_key=os.getenv('ANTHROPIC_API_KEY'))

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
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/recommendations", response_model=PlaylistResponse)
async def create_recommendations(request: PlaylistRequest):
    try:
        # Step 1: Get artist recommendations
        artists = plex_service.get_all_artists()
        recommended_artists = llm_service.get_artist_recommendations(
            prompt=request.prompt,
            artists=artists,
            model=request.model
        )

        # Step 2: Get all tracks for recommended artists
        artist_tracks = {}
        for artist in recommended_artists:
            artist_tracks.update(plex_service.get_artist_tracks(artist))

        # Step 3: Get specific track recommendations
        track_recommendations = llm_service.get_track_recommendations(
            prompt=request.prompt,
            artist_tracks=artist_tracks,
            model=request.model
        )

        # Step 4: Create the playlist
        playlist = plex_service.create_curated_playlist(
            name=f"AI: {request.prompt[:50]}",
            track_recommendations=track_recommendations
        )
        playlist_items = list(playlist.items()) if hasattr(playlist, 'items') else []
        
        return PlaylistResponse(
            name=playlist.title,
            track_count=len(playlist_items),
            artists=recommended_artists,
            id=str(playlist.ratingKey) if hasattr(playlist, 'ratingKey') else None
        )
    except Exception as e:
        logger.error(f"Error creating playlist: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))