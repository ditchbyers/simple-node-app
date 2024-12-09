#!/bin/bash

# Wait for Jenkins to start (waiting for port 8080)
until nc -z -v -w30 localhost 8080; do
  echo "Waiting for Jenkins to start..."
  sleep 5
done

# Install the plugins using jenkins-plugin-cli
echo "Installing Jenkins plugins..."
/usr/local/bin/jenkins-plugin-cli --plugins blueocean pipeline-utility-steps pipeline-api docker git

# Wait for Jenkins to restart after installing plugins
echo "Plugins installed. Jenkins is ready."
