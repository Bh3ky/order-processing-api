from fastapi import APIRouter

# TODO: Implement each feature's own router.
# The main application will later include this router under the "/api/v1" prefix.
router = APIRouter()

@router.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """
    Health check endpoint

    This endpoint is used by load balancers, container orchestrators
    (e.g., Docker or Kubernetes), and monitoring systems to verify that
    the API process is running and able to serve requests.
    """
    return {
        "status": "healthy",
    }
