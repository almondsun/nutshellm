#!/bin/sh
set -eu

if [ "$(id -u)" = "0" ]; then
  chown nutshellm:nutshellm /app/data
  exec runuser -u nutshellm -- "$@"
fi

exec "$@"
