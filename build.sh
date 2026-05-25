#!/usr/bin/env bash
# 保证你的build.sh脚本有任何错误就退出
# 如果没有这个设置，发生异常的时候，你在日志中可能根本无法知道到底从哪里开始出问题。
set -e

# 保证你的字符集正确，如果是英文写en_US.UTF-8，如果是中文写zh_CN.UTF-8
# 如果没有设置，你的日志中非英文字符可能会显示乱码
export LC_ALL=en_US.UTF-8
export LANG=en_US.UTF-8
export LANGUAGE=en_US.UTF-8

CURRENT_PATH=$(cd `dirname $0`; pwd)
ROOT_PATH=${CURRENT_PATH}

cd ${ROOT_PATH}
rm -rf output
mkdir -p output
shopt -s extglob
cp -a !(output|.env) output/
