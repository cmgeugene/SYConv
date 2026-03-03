# Code Overview
- `App.jsx`: The main entry point for the React frontend application. It manages the global state (uploaded file, parsed data, loading state) and orchestrates the layout.
- **Relationships & Flow**: Serves as the parent for `DocumentViewer` (left pane) and `DataSheet` (right pane). It handles the file upload logic and communicates with the FastAPI backend.

# TODOs in this Code
- [x] Implement file upload handler and fetch to `/api/process-document`.
- [x] Set up the split-pane layout using CSS Flexbox.
- [x] Pass parsed data to the DataSheet component.
