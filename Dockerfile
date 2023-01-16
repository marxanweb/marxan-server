FROM --platform=linux/amd64 ubuntu:18.04 as server
COPY . /marxan-server/.
ENV MARXAN_SERVER_DIRECTORY=/marxan-server/
RUN ./marxan-server/unix_install.sh
ENTRYPOINT [${CONDA_PYTHON_EXE} ${MARXAN_SERVER_DIRECTORY}\/marxan-server.py]
