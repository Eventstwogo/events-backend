from lifespan import settings

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        app="main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=True,
        reload_delay=15,
        use_colors=True,
    )
