# NOT BUILT BY DEFAULT. The nginx-in-image fallback of doc 03 section 3.2:
# neither compose file nor scripts/build-push.sh references it any more. The
# shipped artifact is the single root Dockerfile, which bakes this same SPA
# build into the API image and serves it from :8000. Kept, labelled, because
# nginx.conf beside it is the written record of the response policy the app
# re-implements, and git history is not something an operator taking the
# fallback in eighteen months will find.
FROM node:20-alpine AS build
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build

FROM nginx:alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
