#!/bin/bash
# The Run button: build (replit_build.sh), then serve. A deployment builds once and runs
# replit_serve.sh only (see .replit).
set -e
bash replit_build.sh
exec bash replit_serve.sh
