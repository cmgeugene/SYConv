# Code Overview
- `read_root()`: A simple health check endpoint to verify the FastAPI server is running.
- **Relationships & Flow**: This is the main entry point of the backend application. It initializes the FastAPI app, loads environment variables using `python-dotenv`, and sets up CORS middleware so the React frontend can make requests. It includes the routing layer from `backend.api.routes`.

# TODOs in this Code
- [x] Add the `/api/process-document` POST endpoint for file uploads.
- [x] Integrate configuration (dotenv loaded).
- [ ] Connect image processing and LLM parsing routers.
