#!/bin/sh
nginx &
nginx_pid=$!

echo "Waiting for backend services to start..."
while true
do
    if ! curl -s service1:8199/request >/dev/null 2>&1 && \
       ! curl -s service2:8080 >/dev/null 2>&1
    then
        echo "All services are down. Shutting down Nginx..."
        kill $nginx_pid
        exit 0
    fi
    sleep 5
done