from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="KingPi",
        description="Lightweight PyPI package analytics server",
        version="0.1.0",
    )

    return app


app = create_app()
