"""Serve the existing React research workstation and provenance-gated API."""
from pathlib import Path
from fastapi import HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from research_api import app

DIST = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
if (DIST / 'assets').is_dir():
    app.mount('/assets', StaticFiles(directory=DIST / 'assets'), name='assets')
if (DIST / 'vendor').is_dir():
    app.mount('/vendor', StaticFiles(directory=DIST / 'vendor'), name='vendor')

@app.get('/favicon.ico')
def favicon():
    return Response(status_code=204)

@app.get('/')
@app.get('/dti')
@app.get('/evolution')
@app.get('/amp-screening')
@app.get('/wheel')
@app.get('/report')
def index_page():
    page = DIST / 'index.html'
    if not page.is_file():
        raise HTTPException(503, 'Build the research UI first: cd frontend; npm run build')
    return FileResponse(page)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='127.0.0.1', port=8000)
