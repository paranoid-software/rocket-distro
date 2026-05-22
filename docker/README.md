# Rocket — distribution deploy

Run Rocket from published images. No source code required.

## Layout

```
docker/
├── docker-compose.yml          # full stack, uses ghcr.io images for api/bridge/indexer
├── .env.example                # template — copy to .env and edit
├── config-samples/             # settings.json templates per service
│   ├── api/settings.json.example
│   ├── bridge/settings.json.example
│   └── indexer/settings.json.example
├── logy-emulator/              # bundled local emulator (Python, tiny image)
├── zookeeper-emulator/         # bundled local emulator (Python, tiny image)
└── scripts/
    └── generate-api-auth.py    # creates master-account.cookie + JWT keypairs + mongodb keyfile
```

## First-time setup

```bash
cd docker
cp .env.example .env
# Edit .env: set MONGO_INITDB_ROOT_PASSWORD, RABBITMQ_DEFAULT_PASS, STORAGE_PATH (absolute is recommended).
```

### 1. Storage dirs

```bash
mkdir -p ${STORAGE_PATH:-./storage}/{api,bridge,indexer}/config
mkdir -p ${STORAGE_PATH:-./storage}/{api,bridge}/secrets
mkdir -p ${STORAGE_PATH:-./storage}/{mongodb/data,opensearch/data,rabbitmq/data,redis/data}
```

### 2. Auth + encryption + Mongo keyfile

```bash
pip install cryptography
STORAGE_PATH=${STORAGE_PATH:-./storage} python3 scripts/generate-api-auth.py
# Creates: <STORAGE_PATH>/api/auth/* and <STORAGE_PATH>/mongodb/keyfile

openssl rand -out ${STORAGE_PATH:-./storage}/api/secrets/cookie-monsta 96
cp ${STORAGE_PATH:-./storage}/api/secrets/cookie-monsta ${STORAGE_PATH:-./storage}/bridge/secrets/
```

### 3. Linux permissions

MongoDB / RabbitMQ / Redis run as UID 999, OpenSearch as 1000:0:

```bash
sudo chown -R 999:999 ${STORAGE_PATH:-./storage}/{mongodb,rabbitmq,redis}
sudo chmod 400 ${STORAGE_PATH:-./storage}/mongodb/keyfile
sudo chown -R 1000:0 ${STORAGE_PATH:-./storage}/opensearch/data
sudo chmod 775 ${STORAGE_PATH:-./storage}/opensearch/data
```

### 4. Service config

```bash
cp config-samples/api/settings.json.example     ${STORAGE_PATH:-./storage}/api/config/settings.json
cp config-samples/bridge/settings.json.example  ${STORAGE_PATH:-./storage}/bridge/config/settings.json
cp config-samples/indexer/settings.json.example ${STORAGE_PATH:-./storage}/indexer/config/settings.json
# Edit each settings.json: credentials must match .env (Mongo + Rabbit).
```

### 5. Bring it up

```bash
docker compose up -d
```

The `mongo-init` service runs once after Mongo is healthy and calls `rs.initiate()` automatically. Bridge and API wait for `mongo-init: service_completed_successfully`, so they only start once the replica set is ready.

## Daily commands

```bash
docker compose ps
docker compose logs -f <service>
docker compose restart <service>
docker compose down                  # stop, keep data (bind mounts under STORAGE_PATH)
```

## Choosing the image tag

`.env`:

```env
ROCKET_TAG=latest    # main branch
ROCKET_TAG=develop   # develop branch
ROCKET_TAG=<sha>     # pin to a commit
```

## Use your own infrastructure (compose profiles)

Each bundled service (Mongo, OpenSearch, RabbitMQ, Redis, Logy, Zookeeper) is gated behind a compose profile. The Rocket apps (`api`, `bridge`, `indexer`) have no profile and always run. Their `depends_on` references to bundled services are `required: false`, so any service you opt out of is skipped.

Toggle via `COMPOSE_PROFILES` in `.env`:

```env
# All bundled (default)
COMPOSE_PROFILES=bundled-mongo,bundled-opensearch,bundled-rabbitmq,bundled-redis,bundled-logy,bundled-zookeeper

# Bring your own Mongo
COMPOSE_PROFILES=bundled-opensearch,bundled-rabbitmq,bundled-redis,bundled-logy,bundled-zookeeper

# Rocket apps only (everything else external)
COMPOSE_PROFILES=
```

After removing a profile, update the corresponding `hostName`/credentials in `${STORAGE_PATH}/<service>/config/settings.json` so the apps connect to your external endpoint instead of the bundled one:

| Profile removed | Update in `settings.json` |
|---|---|
| `bundled-mongo` | `masterDbContext.{hostName, portNumber, username, password}` (api + bridge) |
| `bundled-opensearch` | `searchCacheDbContext.{hostName, portNumber}` (api + indexer) |
| `bundled-rabbitmq` | `messageBrokerServiceContext.{hostName, portNumber, userName, password}` (bridge + indexer) |
| `bundled-redis` | `memDbContext.{hostName, portNumber}` (bridge) |
| `bundled-logy` | `loggingServiceContext.baseEndpoint` (api + bridge + indexer) |
| `bundled-zookeeper` | `zooServiceContext.baseEndpoint` (api + bridge + indexer) |

Notes:
- `bundled-mongo` bundles `mongo-init` (replica-set bootstrap). If you bring your own Mongo, **it must already be a replica set** — Bridge needs change streams.
- `RABBITMQ_DEFAULT_USER/PASS` in `.env` only apply on first init of the Mnesia volume. To rotate later: `docker compose exec rabbitmq rabbitmqctl change_password <user> '<new>'`.

## Ports (defaults — override in .env)

| Service | Host port | Env var |
|---|---|---|
| MongoDB | 27017 | `MONGO_PORT` |
| OpenSearch | 9200 | `OS_PORT` |
| RabbitMQ AMQP | 5672 | `RABBITMQ_AMQP_PORT` |
| RabbitMQ mgmt | 15672 | `RABBITMQ_MGMT_PORT` |
| Redis | 6379 | `REDIS_PORT` |
| API | 8000 | (fixed) |
| Bridge | 8081 | (fixed) |
| Indexer | 8082 | (fixed) |
| Logy emulator | 30077 | (fixed) |
| Zookeeper emulator | 30079 | (fixed) |

## Troubleshooting

**Bridge crashloop with `ReplicaSetGhost` / `TimeoutException` selecting server**
The replica set isn't initiated. Normally `mongo-init` handles this; if a previous run set the wrong host in the data dir (e.g. you renamed `COMPOSE_PROJECT_NAME`), force a reconfig:
```bash
docker compose exec mongodb mongosh -u admin -p YOUR_PASSWORD --quiet --eval '
  var c = rs.conf(); c.members[0].host = "mongodb:27017"; c.version++;
  rs.reconfig(c, { force: true });
'
```
Or wipe `${STORAGE_PATH}/mongodb/data/*` for a fresh start.

**Indexer/Bridge: RabbitMQ `ACCESS_REFUSED - Login was refused`**
`messageBrokerServiceContext.userName/password` in `${STORAGE_PATH}/{bridge,indexer}/config/settings.json` must match `RABBITMQ_DEFAULT_USER` / `RABBITMQ_DEFAULT_PASS` in `.env`.

**MongoDB "Authentication failed"**
Data dir was initialized with different credentials than current `.env`. Either restore the original password or wipe `${STORAGE_PATH}/mongodb/data`.
