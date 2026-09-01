# Python 3.12 is pinned because WeasyPrint and Pillow ship stable wheels for it.
FROM python:3.12-slim

# WeasyPrint renders through Pango/Cairo, which are system libraries rather than
# Python packages. Installing them here is what keeps PDF generation reproducible.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpango-1.0-0 \
        libpangoft2-1.0-0 \
        libharfbuzz0b \
        libcairo2 \
        libgdk-pixbuf-2.0-0 \
        libffi-dev \
        shared-mime-info \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/srv \
    PIP_NO_CACHE_DIR=1

WORKDIR /srv

# Only the dependencies are installed, and they are read straight out of
# pyproject.toml so there is no second list to keep in sync. Doing this before
# the source copy means editing code never invalidates the (slow) pip layer.
# The application itself is not pip-installed: it is run from /srv, which
# PYTHONPATH already covers.
COPY pyproject.toml ./
RUN pip install --upgrade pip \
    && python -c "import tomllib; d=tomllib.load(open('pyproject.toml','rb'))['project']; print(chr(10).join(d['dependencies'] + d['optional-dependencies']['dev']))" > /tmp/requirements.txt \
    && pip install -r /tmp/requirements.txt

COPY app ./app
COPY tests ./tests

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
