# Code Overview
- `DocumentViewer.jsx`: A component that displays the uploaded image as the background and overlays transparent highlight boxes mathematically mapped to the image's original dimensions vs its rendered dimensions.
- **Relationships & Flow**: Rendered by `App.jsx`. Receives the `previewUrl` and `parsedData` as props.

# TODOs in this Code
- [ ] Implement image load handling to capture natural dimensions.
- [ ] Render absolutely-positioned `<div>` elements for highlights based on calculated percentages.
