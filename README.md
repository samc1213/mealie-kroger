# Mealie-Kroger
An application to link Mealie recipes to the Kroger supermarket online ordering system

## Development
To run the server:

```
poetry env use python3
poetry shell
poetry install
MEALIE_URL=xxx KROGER_CLIENT_ID=xxx KROGER_CLIENT_SECRET=xxx uvicorn mealie_kroger.app:app --reload
```

