# Code Overview
- `ParsedWord` and `ProcessResponse`: Pydantic models to strictly define the structure of the API responses.
- **Relationships & Flow**: These schemas map the messy output of the LLM and internal processing into a uniform structure that the React frontend precisely expects.

# TODOs in this Code
- [ ] Add more detailed validation if necessary (e.g. valid POS categories).
