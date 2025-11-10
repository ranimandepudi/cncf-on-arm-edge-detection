ARG GIT_COMMIT="main"
ARG VERSION="main"

FROM --platform=$TARGETARCH cgr.dev/chainguard/python:latest-dev AS dev
WORKDIR /app
RUN python -m venv venv
RUN touch /app/empty
ENV PATH="/app/venv/bin":$PATH
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt


FROM --platform=$TARGETARCH cgr.dev/chainguard/python:latest
ARG GIT_COMMIT
ARG VERSION
COPY --chown=nonroot:nonroot api.py /app/main.py
COPY --chown=nonroot:nonroot static /app/static
COPY --chown=nonroot:nonroot index.html /app/index.html
COPY --chown=nonroot:nonroot replical.html /app/replical.html

COPY --from=dev /app/venv /app/venv
ENV PATH="/app/venv/bin:$PATH" \
    GIT_COMMIT=$GIT_COMMIT \
    VERSION=$VERSION \
    UVICORN_PORT="8080"
WORKDIR /app
USER nonroot:nonroot
EXPOSE 8080/tcp
ENTRYPOINT ["uvicorn", "api:app"]
