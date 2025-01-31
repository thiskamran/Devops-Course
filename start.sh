#!/bin/sh
# Start Nginx in the background
nginx &
nginx_pid=$!

max_retries=30
retry_interval=1

# Wait for services to be available
echo "Waiting for backend services..."
for i in $(seq 1 $max_retries); do
    if curl -s service1:8199/request >/dev/null 2>&1 || \
       curl -s service2:8080 >/dev/null 2>&1; then
        echo "Backend services are up!"
        break
    fi
    echo "Retry $i/$max_retries: Waiting for services..."
    sleep $retry_interval
done

# Monitor backend services
while true; do
    service1_status=$(curl -s service1:8199/request 2>&1)
    service2_status=$(curl -s service2:8080 2>&1)

    if [ $? -ne 0 ] || [ -z "$service1_status" ] && [ -z "$service2_status" ]; then
        echo "All services are down. Stopping Nginx..."
        kill $nginx_pid
        wait $nginx_pid  # Wait for nginx to exit cleanly
        echo "Nginx stopped"
        exit 0
    fi
    sleep 5
done