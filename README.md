# nova-mlops-lab

**OpenStack-first MLOps job runner** with a *LightSpeed-style* interface:

```
run → logs → cleanup
```

Designed for **DevStack labs** and environments where OpenStack runs inside **VirtualBox**, where:
- floating IPs may not work
- direct SSH may be unreliable
- networking is constrained

This project intentionally works **without floating IPs or SSH**.

---

## Why this exists

When learning or demoing OpenStack, you want something *real* to run — not just `cirros ping`.

`nova-mlops-lab` turns **Nova instances into ephemeral job runners**:

- Launch a “job” as a Nova server
- Execute via **cloud-init** (boot-time payload)
- Observe progress via **Nova console logs**
- Tear everything down cleanly

This mirrors how OpenStack operators debug early boot, cloud-init failures, and instance lifecycle issues in real environments.

---

## Current MVP

### OpenStack probes
- `nova-mlops openstack ping`
- `nova-mlops openstack images`
- `nova-mlops openstack flavors`
- `nova-mlops openstack networks`

### VBox-safe job execution
- `nova-mlops openstack run <job>`
- `nova-mlops openstack logs <job>`
- `nova-mlops openstack cleanup <job>`

### Local job state

```text
.nova-mlops/state/
  hello-train.json
```

No daemon. No database. Fully CLI-driven.

---

## Architecture (MVP)

The CLI is **stateless** between invocations.

- `run` → creates a Nova server and stores `server_id`
- `logs` → fetches Nova console output
- `cleanup` → deletes the Nova server and updates state

This keeps the system transparent, debuggable, and easy to extend.

---

## Prerequisites

### Recommended environment
Run on the **DevStack host** (e.g. Ubuntu24 VM).

You need:
- A working DevStack installation
- `openstack` CLI working (`openstack token issue`)
- Python **≥ 3.10**

### OpenStack authentication
`openstacksdk` uses the same auth sources as the `openstack` CLI:

- `source openrc ...`
- or `~/.config/openstack/clouds.yaml`

---

## Quickstart (DevStack / Ubuntu24)

### 1) Clone and create a virtual environment

Ubuntu 24.04 enforces **PEP 668**, so use a virtual environment:

```bash
git clone https://github.com/miharcan/nova-mlops-lab.git
cd nova-mlops-lab

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip

pip install -e ".[openstack]"
```

If `venv` is missing:

```bash
sudo apt update
sudo apt install -y python3-venv python3-full
```

---

### 2) Load DevStack credentials

```bash
source ~/devstack/openrc admin admin
openstack token issue
```

---

### 3) Verify OpenStack connectivity

```bash
nova-mlops openstack ping
```

---

### 4) Discover available resources

```bash
nova-mlops openstack images
nova-mlops openstack flavors
nova-mlops openstack networks
```

Typical DevStack example:

- Image: `ubuntu-jammy`
- Flavor: `m1.small`
- Network: `private`

---

### 5) Run a VBox-safe “training job”

```bash
nova-mlops openstack run hello-train \
  --image ubuntu-jammy \
  --flavor m1.small \
  --network private
```

---

### 6) View logs (no SSH required)

```bash
nova-mlops openstack logs hello-train
```

---

### 7) Clean up the server

```bash
nova-mlops openstack cleanup hello-train
```

---

### NLP demo (real ML, VBox-safe)

```bash
nova-mlops openstack run-nlp sentiment-demo
nova-mlops openstack logs sentiment-demo
nova-mlops openstack cleanup sentiment-demo
```


## VirtualBox notes

This project is designed to work even when:
- floating IPs are unavailable
- SSH access is not possible

It relies on **cloud-init** and **Nova console logs** only.

---

## Development workflow

```bash
pip install -e ".[openstack,dev]"
ruff check .
pytest -q
```

---

## Roadmap

- `openstack status <job>`
- Filter logs to `[NOVA-MLOPS]`
- Optional SSH exec path
- Artifact collection
- Multi-node jobs
- CI (GitHub Actions)

---

## KVM vs VirtualBox

VirtualBox is ideal for learning and accessibility.

For production-like networking (floating IPs, fewer L2 quirks), **KVM/libvirt** is recommended.