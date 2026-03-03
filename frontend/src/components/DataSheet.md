# Code Overview
- `DataSheet.jsx`: Extends Ag-Grid to present the extracted text, parts of speech, and meanings in an editable spreadsheet interface.
- **Relationships & Flow**: Rendered inside the right panel of `App.jsx`. Communicates edited data back up to the parent component.

# TODOs in this Code
- [ ] Implement `ag-grid-react` columns and editing events.
- [ ] Connect the `onDataChange` prop to keep global state perfectly in sync.
