# Deployment Guide — Azure

This guide walks through deploying the Support Ticket Classifier to Azure Kubernetes Service (AKS) from a clean subscription.

---

## 1. Prerequisites

- Azure CLI ≥ 2.55 (`az --version`)
- kubectl ≥ 1.28
- Helm ≥ 3.13
- Docker ≥ 24
- An Azure subscription with Contributor rights

```bash
az login
az account set --subscription "<your-subscription-id>"
```

---

## 2. Provision infrastructure

For a fresh setup we use Terraform (see `deployment/azure/`), but the following Azure CLI commands give a clear picture of what's created.

```bash
# Variables
RG=rg-ticketml-prod
LOCATION=centralindia
ACR=ticketmlacr
AKS=aks-ticketml-prod
MYSQL=mysql-ticketml-prod
REDIS=redis-ticketml-prod
KV=kv-ticketml-prod

# Resource group
az group create -n $RG -l $LOCATION

# Container registry
az acr create -n $ACR -g $RG --sku Standard --admin-enabled false

# AKS cluster (3 nodes, autoscaler on)
az aks create -n $AKS -g $RG \
    --node-count 3 \
    --node-vm-size Standard_D4s_v3 \
    --enable-cluster-autoscaler --min-count 3 --max-count 10 \
    --attach-acr $ACR \
    --enable-managed-identity \
    --network-plugin azure \
    --enable-addons monitoring \
    --generate-ssh-keys

# MySQL Flexible Server
az mysql flexible-server create -n $MYSQL -g $RG \
    --sku-name Standard_B2s --tier Burstable \
    --version 8.0.21 --storage-size 64 \
    --admin-user ticketml --admin-password "$MYSQL_PWD" \
    --public-access None  # private endpoint

# Redis cache
az redis create -n $REDIS -g $RG \
    --sku Standard --vm-size c1 --location $LOCATION

# Key Vault
az keyvault create -n $KV -g $RG -l $LOCATION
az keyvault secret set --vault-name $KV --name jwt-secret  --value "$JWT_SECRET"
az keyvault secret set --vault-name $KV --name mysql-pwd   --value "$MYSQL_PWD"
az keyvault secret set --vault-name $KV --name redis-pwd   --value "$REDIS_PWD"
```

---

## 3. Build and push image

```bash
az acr login -n $ACR
docker build -t $ACR.azurecr.io/ticketml-api:v2.3.0 .
docker push    $ACR.azurecr.io/ticketml-api:v2.3.0
```

In normal operation this happens automatically via GitHub Actions on every push to `main`.

---

## 4. Connect kubectl

```bash
az aks get-credentials -n $AKS -g $RG
kubectl create namespace ticketml
```

---

## 5. Bootstrap cluster

```bash
# Ingress
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm upgrade --install ingress-nginx ingress-nginx/ingress-nginx \
    --namespace ingress-nginx --create-namespace

# Cert-manager for automated TLS
helm repo add jetstack https://charts.jetstack.io
helm upgrade --install cert-manager jetstack/cert-manager \
    --namespace cert-manager --create-namespace \
    --set installCRDs=true

# Secrets Store CSI driver — pulls secrets from Key Vault
helm upgrade --install csi-secrets-store secrets-store-csi-driver/secrets-store-csi-driver \
    --namespace kube-system
```

---

## 6. Create app config + secrets

`ConfigMap` for non-secret env vars:
```bash
kubectl -n ticketml create configmap ticketml-config \
    --from-literal=ENVIRONMENT=production \
    --from-literal=LOG_LEVEL=INFO \
    --from-literal=MYSQL_HOST=mysql-ticketml-prod.mysql.database.azure.com \
    --from-literal=MYSQL_DB=ticketml \
    --from-literal=REDIS_HOST=redis-ticketml-prod.redis.cache.windows.net \
    --from-literal=MODEL_PATH=/app/models/pipeline.pkl
```

`Secret` for credentials (real deployments use the CSI driver instead):
```bash
kubectl -n ticketml create secret generic ticketml-secrets \
    --from-literal=JWT_SECRET="$JWT_SECRET" \
    --from-literal=MYSQL_USER=ticketml \
    --from-literal=MYSQL_PASSWORD="$MYSQL_PWD"
```

---

## 7. Apply Kubernetes manifests

```bash
kubectl apply -f deployment/kubernetes/deployment.yaml
kubectl apply -f deployment/kubernetes/service.yaml
kubectl apply -f deployment/kubernetes/ingress.yaml
kubectl apply -f deployment/kubernetes/hpa.yaml
```

Confirm rollout:
```bash
kubectl -n ticketml rollout status deployment/ticketml-api
kubectl -n ticketml get pods,svc,ingress,hpa
```

---

## 8. Verify

```bash
curl -k https://api.ticketml.example.com/health
# {"status":"ok"}

curl -k https://api.ticketml.example.com/ready
# {"status":"ready","model_loaded":true,...}
```

Swagger UI: <https://api.ticketml.example.com/docs>

---

## 9. Observability

- **Logs** — `kubectl logs` for ad-hoc debug; Azure Log Analytics for cross-pod queries:
  ```kusto
  ContainerLogV2
  | where ContainerName == "api"
  | extend body = parse_json(LogMessage)
  | where body.event == "prediction.served"
  | summarize p95=percentile(toint(body.latency_ms), 95) by bin(TimeGenerated, 5m)
  ```
- **Metrics** — Prometheus scrapes `/metrics`; Grafana dashboard in `docs/grafana/`.
- **Tracing** — Application Insights auto-instrumented via `opencensus-ext-azure` (drop-in, configured in `core/logging.py` when `APPINSIGHTS_CONN_STR` is set).
- **Alerting** — PagerDuty rules:
  - p95 latency > 500 ms for 5 min
  - 5xx error rate > 2% for 3 min
  - Model F1 (canary) < 0.92 for 10 min

---

## 10. Rollback

```bash
kubectl -n ticketml rollout undo deployment/ticketml-api
```

If the model artifact is at fault rather than the code, swap `MODEL_PATH` to the previous artifact and restart pods.
