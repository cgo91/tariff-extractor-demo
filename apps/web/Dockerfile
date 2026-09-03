# Two stages: build the SPA with Node, then serve the static output with nginx.
# The runtime image carries no Node and no sources, only the compiled bundle.

FROM node:22-alpine AS build

WORKDIR /app

# pnpm ships with Node via corepack; pinning through the lockfile keeps the
# production build byte-identical to the one produced on a developer machine.
RUN corepack enable

COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile

COPY . .
RUN pnpm build


FROM nginx:1.27-alpine

# Same-origin routing: the SPA and the API answer on one hostname.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
