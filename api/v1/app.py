from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import config.config as CONF
from api.v1.routes import upload


app = FastAPI(
    title="Code Analysis API",
    description="API for analyzing code and storing in a graph database",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(upload.router, prefix="/api/v1", tags=["upload"])


@app.get("/")
async def root():
    """
    Root endpoint to verify the API is running
    """
    return {
        "message": "Code Analysis API is running",
        "graph_host": CONF.GRAPH_HOST,
        "graph_port": CONF.GRAPH_PORT
    }


@app.get("/health")
async def health_check():
    """
    Health check endpoint
    """
    return {"status": "healthy"}
