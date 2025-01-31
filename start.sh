#!/bin/sh
# Start Nginx in the background
nginx &
nginx_pid=$!

# Store PID in a file for reliability
echo $nginx_pid > /var/run/nginx.pid

max_retries=30
retry_interval=1

# Wait for services to be available
echo "Waiting for backend services..."
i=1
while [ $i -le $max_retries ]; do
    if curl -s service1:8199/request >/dev/null 2>&1 || \
       curl -s service2:8080 >/dev/null 2>&1; then
        echo "Backend services are up!"
        break
    fi
    echo "Retry $i/$max_retries: Waiting for services..."
    sleep $retry_interval
    i=$((i + 1))
done

# Monitor backend services
while true; do
    service1_status=$(curl -s service1:8199/request 2>&1)
    service2_status=$(curl -s service2:8080 2>&1)

    if [ $? -ne 0 ] || [ -z "$service1_status" ] && [ -z "$service2_status" ]; then
        echo "All services are down. Stopping Nginx..."
        
        # Try multiple ways to stop nginx gracefully
        if [ -f /var/run/nginx.pid ]; then
            pid=$(cat /var/run/nginx.pid)
            kill $pid 2>/dev/null || true
        fi
        
        kill $nginx_pid 2>/dev/null || true
        nginx -s quit 2>/dev/null || true
        
        sleep 2
        echo "Nginx stopped"
        exit 0
    fi
    sleep 5
done