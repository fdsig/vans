#! /bin/bash
set -euo pipefail  # exit on error, unset var, or pipe failure

# Ensure pyenv and pyenv-virtualenv are initialised (works even in non-interactive script)
if command -v pyenv >/dev/null 2>&1; then
  export PYENV_ROOT="${PYENV_ROOT:-$HOME/.pyenv}"
  # shellcheck disable=SC1090
  eval "$(pyenv init -)"
  eval "$(pyenv virtualenv-init -)"
else
  echo "pyenv not found – please install pyenv and pyenv-virtualenv first." >&2
  exit 1
fi

# list all python versions available to pyenv locally and capture highest version
pyenv_version=$(pyenv versions --bare | sort -V | tail -n 1)

# create the virtual environment if it doesn't already exist
if ! pyenv versions --bare | grep -qx "vans"; then
  pyenv virtualenv "$pyenv_version" vans
fi

# activate the environment
pyenv activate vans

# install tooling & dependencies
pip install --upgrade pip uv
uv pip install -r requirements.txt

# install Playwright browsers
python -m playwright install --with-deps
