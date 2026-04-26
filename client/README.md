# Price Tracker Client

Vanilla JS SPA for the Price Tracker API.

## Quick start

```shell
cd client
npm install
```

Open `index.html` directly in a browser for local development, or use a simple dev server:

```shell
npx serve .
```

## Adding dependencies

```shell
npm install <package>
```

## Docker

Build and run the client container:

```shell
docker build -t pwp-client .
docker run -p 8080:80 pwp-client
```

Or with docker compose from the project root:

```shell
echo "CLIENT_PORT=8080" >> .env
docker compose up -d client
```

