#!/bin/bash
set -e

cargo run
java src/layer1.java
node src/layer2.js
python src/layer3.py
npx tsc
node src/layer4.js
go run src/layer5.go
python src/layer6.py