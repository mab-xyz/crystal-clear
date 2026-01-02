import json
import os

from fastapi.openapi.utils import get_openapi


from src.api.main import app


def get_openapi_spec():
    routes = [
        route
        for route in app.routes
        if not route.path.startswith(("/contract", "/repository", "/audit"))
    ]
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=routes,
    )

    return json.dumps(openapi_schema, indent=2)


if __name__ == "__main__":
    spec = get_openapi_spec()
    with open("openapi.json", "w") as f:
        f.write(spec)
    print("OpenAPI specification written to openapi.json")
