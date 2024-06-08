FROM hub.siji.ci/library/ubuntu

WORKDIR /ssr

COPY . .

EXPOSE 25500
RUN chmod +x ./subconverter-linux
CMD [ "./subconverter-linux" ]