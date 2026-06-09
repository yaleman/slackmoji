#!/bin/bash

if [ -z "$1" ]; then
  echo "Usage: $0 <instance>"
  exit 1
fi

if [ ! -d "output/$1/emoji/" ]; then
  echo "Error: output/$1/emoji/ does not exist."
  exit 1
fi

cd "output/$1/emoji/" || exit 1
tar czvf "../../../emoji-$1.tar.gz" ./*
cd "$(dirname "$0")" || { echo "Couldn't return to base directory"; exit 1; }