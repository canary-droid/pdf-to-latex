# Compiler environment provisioning only. Document compilation remains offline,
# non-root and isolated. No book, credentials or project tree enter this context.
FROM debian:bookworm-slim
ARG PDF2TEX_PACKAGES="texlive-latex-base texlive-latex-recommended texlive-latex-extra texlive-fonts-recommended texlive-science texlive-pictures lmodern cm-super"
RUN apt-get update && apt-get install -y --no-install-recommends $PDF2TEX_PACKAGES && rm -rf /var/lib/apt/lists/*
WORKDIR /work
