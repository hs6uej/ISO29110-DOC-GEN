"""Run the server: `python -m app`. Port comes from PORT in .env (default 8290)."""
import os

import uvicorn

from . import settings  # noqa: F401  (loads .env into os.environ)


def main():
    port = int(os.getenv("PORT", "8290"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("app.main:app", host=host, port=port)


if __name__ == "__main__":
    main()
