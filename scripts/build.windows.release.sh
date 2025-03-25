#!/bin/bash
set -xe

git clone https://github.com/curl/curl --depth=1 --branch curl-8_8_0
cd curl
cmake -DCMAKE_BUILD_TYPE=Release -DCURL_USE_LIBSSH2=OFF -DHTTP_ONLY=ON -DCURL_USE_SCHANNEL=ON -DBUILD_SHARED_LIBS=OFF -DBUILD_CURL_EXE=OFF -DCMAKE_INSTALL_PREFIX="$MINGW_PREFIX" -G "Unix Makefiles" -DHAVE_LIBIDN2=OFF -DCURL_USE_LIBPSL=OFF .
make install -j4
cd ..

git clone https://github.com/jbeder/yaml-cpp --depth=1
cd yaml-cpp
cmake -DCMAKE_BUILD_TYPE=Release -DYAML_CPP_BUILD_TESTS=OFF -DYAML_CPP_BUILD_TOOLS=OFF -DCMAKE_INSTALL_PREFIX="$MINGW_PREFIX" -G "Unix Makefiles" .
make install -j4
cd ..

git clone https://github.com/ftk/quickjspp --depth=1
cd quickjspp
patch quickjs/quickjs-libc.c -i ../scripts/patches/0001-quickjs-libc-add-realpath-for-Windows.patch
cmake -G "Unix Makefiles" \
      -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_C_FLAGS="-D__MINGW_FENV_DEFINED" .
make quickjs -j4
# 如果是 32 位编译，则处理 libquickjs.a，去掉重复定义的符号
# 注意：此处通过检测目标架构环境变量，你也可以根据实际情况加个判断
echo "处理 32 位 libquickjs.a，去除重复定义的符号..."
mkdir -p tmp_lib
cd tmp_lib
# 解包静态库
ar x ../quickjs/libquickjs.a
# 对每个目标文件，删除这几个符号
for obj in *.o; do
  objcopy --strip-symbol=__mingw_fe_pc53_env --strip-symbol=__mingw_fe_pc64_env --strip-symbol=__mingw_fe_dfl_env "$obj"
done
# 重新打包为新的静态库
ar rcs ../quickjs/libquickjs_fixed.a *.o
cd ..
# 用处理后的库覆盖原库（或直接安装新库）
mv quickjs/libquickjs_fixed.a quickjs/libquickjs.a
install -d "$MINGW_PREFIX/lib/quickjs/"
install -m644 quickjs/libquickjs.a "$MINGW_PREFIX/lib/quickjs/"
install -d "$MINGW_PREFIX/include/quickjs"
install -m644 quickjs/quickjs.h quickjs/quickjs-libc.h "$MINGW_PREFIX/include/quickjs/"
install -m644 quickjspp.hpp "$MINGW_PREFIX/include/"
cd ..

git clone https://github.com/PerMalmberg/libcron --depth=1
cd libcron
git submodule update --init
cmake -G "Unix Makefiles" -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX="$MINGW_PREFIX" .
make libcron install -j4
cd ..

git clone https://github.com/Tencent/rapidjson --depth=1
cd rapidjson
cmake -DRAPIDJSON_BUILD_DOC=OFF -DRAPIDJSON_BUILD_EXAMPLES=OFF -DRAPIDJSON_BUILD_TESTS=OFF -DCMAKE_INSTALL_PREFIX="$MINGW_PREFIX" -G "Unix Makefiles" .
make install -j4
cd ..

git clone https://github.com/ToruNiina/toml11 --branch "v4.3.0" --depth=1
cd toml11
cmake -DCMAKE_INSTALL_PREFIX="$MINGW_PREFIX" -G "Unix Makefiles" -DCMAKE_CXX_STANDARD=11 .
make install -j4
cd ..

python -m ensurepip
python -m pip install gitpython
python scripts/update_rules.py -c scripts/rules_config.conf

rm -f C:/Strawberry/perl/bin/pkg-config C:/Strawberry/perl/bin/pkg-config.bat
cmake -DCMAKE_BUILD_TYPE=Release -G "Unix Makefiles" .
make -j4
rm subconverter.exe
# shellcheck disable=SC2046
g++ $(find CMakeFiles/subconverter.dir/src -name "*.obj") curl/lib/libcurl.a -o base/subconverter.exe -static -lbcrypt -lpcre2-8 -l:quickjs/libquickjs.a -llibcron -lyaml-cpp -liphlpapi -lcrypt32 -lws2_32 -lwsock32 -lz -s
mv base subconverter