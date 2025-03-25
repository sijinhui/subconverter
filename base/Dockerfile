FROM hub.sivpn.cn/library/ubuntu:20.04

WORKDIR /ssr

COPY . .

EXPOSE 25500
RUN chmod +x ./subconverter-linux
CMD [ "./subconverter-linux" ]