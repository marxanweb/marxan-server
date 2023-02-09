FROM --platform=linux/amd64 ubuntu:18.04 as server
ENV MARXAN_SERVER_DIRECTORY=/marxan-server/
# Install miniconda and dependencies
COPY ./unix_install.sh ./marxan-server/
RUN ./marxan-server/unix_install.sh
ENV CONDA_DEFAULT_ENV=base 
ENV GDAL_DATA=/miniconda3/share/gdal 
ENV PROJ_LIB=/miniconda3/share/proj 
# Copy files
COPY . /marxan-server/.
# Create vanilla server files
COPY ./server.dat.default ./marxan-server/server.dat
COPY ./users/admin/user.dat.default ./marxan-server/users/admin/user.dat
COPY ./marxan-server.log.default ./marxan-server/marxan-server.log
COPY ./runlog.dat.default ./marxan-server/runlog.dat
# move favicon to the tornado static file folder
COPY ./favicon.ico ./marxan-client/build/favicon.ico 
# Activate conda base environment
RUN echo "conda activate base" >> ~/.bashrc
SHELL ["/bin/bash", "--login", "-c"]
# Entry point
ENTRYPOINT [ "/miniconda3/bin/python", "/marxan-server/server.py"] 