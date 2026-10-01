FROM node:22-alpine AS build
# Not /app. Next confuses the login page (app/page.tsx) with the
# dashboard (app/app/page.tsx) when the project directory is named app.
WORKDIR /frontend
COPY package.json package-lock.json* ./
RUN npm install --include=dev
COPY . .
ARG NEXT_PUBLIC_API_URL=
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN node scripts/build-css.cjs \
    && npm run build \
    && grep -q 'href="/styles.css"' .next/server/app/index.html

FROM node:22-alpine
WORKDIR /frontend
ENV NODE_ENV=production
COPY --from=build /frontend/.next/standalone ./
COPY --from=build /frontend/.next/static ./.next/static
COPY --from=build /frontend/public ./public
EXPOSE 3000
CMD ["node", "server.js"]
