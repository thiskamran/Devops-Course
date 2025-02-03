
FROM node:16-alpine

# Set the working directory in the container
WORKDIR /app

# Copy package.json and install dependencies
COPY package*.json /app/
RUN npm install --only=production

# Bundle app source
COPY . /app

# Expose the port service2 will run on
EXPOSE 8080

# Start the app
CMD ["node", "service2.js"]
