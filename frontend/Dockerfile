# Astrolabe frontend — Next.js production build
FROM node:20-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY package.json package-lock.json* ./
RUN npm ci || npm install
COPY . .
# NEXT_PUBLIC_API_BASE is baked at build time for client bundles; override at build if needed.
ARG NEXT_PUBLIC_API_BASE=http://localhost:8000
ENV NEXT_PUBLIC_API_BASE=$NEXT_PUBLIC_API_BASE
RUN npm run build

FROM node:20-slim AS run
WORKDIR /app
ENV NODE_ENV=production \
    NEXT_TELEMETRY_DISABLED=1 \
    PORT=3000
# Copy the full built app (node_modules, .next, public if present, config, package.json).
COPY --from=build /app ./
RUN useradd --create-home --uid 10001 astro && chown -R astro:astro /app
USER astro
EXPOSE 3000
CMD ["npm", "start"]
