#!/bin/bash
#Install required libs for python
PATH=$PATH:~/.local/bin
python3 -m pip install --upgrade pip | grep -v 'Requirement already satisfied'
pip3 install -r requirements.txt | grep -v 'Requirement already satisfied'

ARGS=$@
#This consumes $@ so save to ARGS first
while [[ $# > 0 && -z $SQL_PROVIDER ]]
do
  key="$1"
  if [[ $key = "--sqlProvider" ]]; then
    SQL_PROVIDER="$2"
  fi
  shift
done

if [[ ! -z "$SQL_PROVIDER" ]]; then
  echo "SQL_PROVIDER = $SQL_PROVIDER"
fi

os=$(uname)
if [[ "$os" == "Linux" ]]; then
    if ! command -v cf &> /dev/null
    then
      echo "Installing CloudFoundry CLI"
      wget -q -O - https://packages.cloudfoundry.org/debian/cli.cloudfoundry.org.key | sudo apt-key add -
      echo "deb https://packages.cloudfoundry.org/debian stable main" | sudo tee /etc/apt/sources.list.d/cloudfoundry-cli.list
      sudo apt-get update
      sudo apt-get install cf-cli
    fi
    if [[ "$SQL_PROVIDER" == "oracle" ]]; then
      echo "Installing ORACLE components"
      wget -q https://download.oracle.com/otn_software/linux/instantclient/215000/instantclient-basiclite-linux.x64-21.5.0.0.0dbru.zip
      unzip instantclient-basiclite-linux.x64-21.5.0.0.0dbru.zip
      export LD_LIBRARY_PATH=$PWD/instantclient_21_5
    fi
elif [[ "$os" == "Darwin" ]]; then
  if [[ "$SQL_PROVIDER" == "oracle" ]] ; then
    if [[ ! -d "./instantclient_19_8" ]]; then
      echo "Installing ORACLE components"
      wget -q https://download.oracle.com/otn_software/mac/instantclient/198000/instantclient-basiclite-macos.x64-19.8.0.0.0dbru.zip
      unzip instantclient-basiclite-macos.x64-19.8.0.0.0dbru.zip
    fi
    export LD_LIBRARY_PATH=$PWD/instantclient_19_8
  fi

fi
export PYTHONPATH=./src/python:$PYTHONPATH
python3 -m scdf_at.clean --serverCleanUp
python3 -m scdf_at.setup $ARGS