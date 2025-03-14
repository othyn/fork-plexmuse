# Plexmuse 🎶🤖

Welcome to **Plexmuse**! This project leverages the power of AI to generate personalized playlists from your Plex music library. Whether you're looking for new music recommendations or creating the perfect playlist for any occasion, this API has got you covered.

## Features ✨

- **AI-Powered Recommendations**: Generate playlists using advanced language models like GPT-4 and Claude.
- **Seamless Plex Integration**: Fetch and manage your music library directly from Plex.
- **Customizable Playlists**: Tailor your playlists with specific prompts and models.

## Getting Started 🚀

### Prerequisites

- Python 3
- Plex Media Server with a Music library
- OpenAI API Key (for GPT-4)
- Anthropic API Key (optional, for Claude)

### Installation

1. **Clone the repository**:

    ```sh
    git clone git@github.com:LubergAlexander/plexmuse.git
    cd plexmuse
    ```

2. **Setup**:

    ```sh
    make all
    ```

3. **Set up environment variables**:
    Create a .env file in the root directory and add your API keys:

    ```sh
    cp .env.example .env
    ```

    To find `PLEX_BASE_URL` and `PLEX_TOKEN`, refer to the Plex support article: [Finding an Authentication Token (X-Plex-Token)](https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/).

    For setting up OpenAI, Anthropic, or other LLM keys, follow the instructions in the LiteLLM documentation: [LiteLLM - Set Keys](https://docs.litellm.ai/docs/set_keys).

### Running the Application

You can run the application using the Makefile or directly with Docker.

#### Using the Makefile

1. **Set up and run the application**:

    ```sh
    make run
    ```

#### Using Docker

1. **Build the Docker image**:

    ```sh
    docker compose build
    ```

2. **Start the Docker container**:

    ```sh
    docker compose up
    ```

#### Using the Published Docker Image

You can also use the pre-built Docker image from GitHub Container Registry, which is automatically built and published on each push to the master branch:

1. **Pull the Docker image**:

    ```sh
    docker pull ghcr.io/lubergalexander/plexmuse:latest
    ```

2. **Run the Docker container**:

    ```sh
    docker run -p 8000:8000 \
      -e PLEX_BASE_URL=your_plex_url \
      -e PLEX_TOKEN=your_plex_token \
      -e OPENAI_API_KEY=your_openai_key \
      ghcr.io/lubergalexander/plexmuse:latest
    ```

3. **Using Docker Compose**:

    Create a `docker-compose.yml` file:

    ```yaml
    version: '3'
    services:
      plexmuse:
        image: ghcr.io/lubergalexander/plexmuse:latest
        ports:
          - "8000:8000"
        environment:
          - PLEX_BASE_URL=your_plex_url
          - PLEX_TOKEN=your_plex_token
          - OPENAI_API_KEY=your_openai_key
          # Add other environment variables as needed
        restart: unless-stopped
    ```

    Then run:

    ```sh
    docker compose up -d
    ```

4. **Available Tags**:

   - `latest`: The most recent build from the master branch
   - SHA tags: Each image is also tagged with the Git commit SHA

## Usage 📖

### User Interface

Access the user interface at the root route `/`. This UI allows you to interact with the API, select playlist length, and is mobile-friendly.
![UI Screenshot](plexmuse-ui.png)

### API

Send a POST request to `/recommendations` with the following JSON body:

```json
{
    "prompt": "Chill vibes for a rainy day",
    "model": "anthropic/claude-3-5-sonnet-latest",
    "min_tracks": 10,
    "max_tracks": 20
}
```

### API Documentation

Open your browser and navigate to `http://127.0.0.1:8000/docs` to explore the API endpoints.
