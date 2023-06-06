FROM node:20
WORKDIR /usr/src/app
COPY package*.json ./
RUN npm install
COPY . .
RUN chown -R node /usr/src/app
EXPOSE 3000
USER node
CMD [ "npm", "run", "start" ]
