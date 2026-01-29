# Troubleshooting: KVM + OpenStack (DevStack)

This document captures real failure modes encountered while running OpenStack labs on KVM and using `nova-mlops-lab`.
It is written as diagnostic pathways: **symptom → checks → root cause → fix**.

> Guiding principle: **Neutron does switching; Linux does routing.**
> If the host has no IP on a network, that network is invisible to it.

---

## 0) Baseline: verify KVM/libvirt are healthy

### Install modern packages (Ubuntu)

On newer Ubuntu releases, the old `qemu` meta-package may not exist; install the architecture packages explicitly:

```bash
sudo apt update
sudo apt install -y   bridge-utils   cpu-checker   libvirt-clients   libvirt-daemon-system   qemu-system-x86   qemu-utils   virt-manager
```

### Validate acceleration

```bash
kvm-ok
```
Expected: `KVM acceleration can be used`

### Permissions (avoid sudo for libvirt)

```bash
sudo usermod -aG libvirt,kvm $USER
newgrp libvirt
```

---

## 1) `virt-install` “hangs” with `--graphics none`

### Symptom

- `virt-install ... --graphics none` starts
- `virsh console <vm>` is blank forever
- You suspect the installer is stuck

### Checks

1) Check domain state:

```bash
sudo virsh domstate <vm>
sudo virsh dominfo <vm> | egrep 'State|CPU time'
```

2) If `paused`, inspect the QEMU log:

```bash
sudo tail -n 200 /var/log/libvirt/qemu/<vm>.log
```

### Root causes (observed)

#### A) VM is paused due to KVM runtime failure

Smells like:
- Domain enters `paused`
- Resume fails with “Resetting the Virtual Machine is required”
- QEMU log shows:

```
KVM: entry failed, hardware error 0x0
```

**Fix**
- Confirm that hardware virtualization is enabled in BIOS/UEFI.
- Confirm your environment is truly bare metal KVM (not nested by accident).
- Confirm no other hypervisor kernel modules are currently holding VT-x/AMD-V.
- If you just need to boot once to proceed, use software emulation as a workaround:

```bash
sudo virt-install   --name ubuntu-guest-tcg   --os-variant ubuntu20.04   --vcpus 2   --ram 2048   --disk size=25,bus=virtio   --network network=default,model=virtio   --location /path/to/ubuntu-20.04.6-live-server-amd64.iso   --graphics none   --console pty,target_type=serial   --virt-type qemu   --machine q35   --extra-args "console=ttyS0,115200n8"
```

#### B) Installer is not writing to the serial console

The domain is `running`, CPU time increases, but console is empty.

**Fix**
Use an ISO-based install and ensure serial console arguments are correct:

```bash
sudo virt-install   --name ubuntu-guest   --os-variant ubuntu20.04   --vcpus 2   --ram 2048   --disk size=25,bus=virtio   --network network=default,model=virtio   --location /tmp/ubuntu-20.04.6-live-server-amd64.iso   --graphics none   --console pty,target_type=serial   --extra-args "console=ttyS0,115200n8"
```

#### C) You used an unstable `--location` netboot tree

Some `--location http://.../installer-amd64/` trees boot, but do not reliably surface the installer on `ttyS0`.
Prefer ISO for consistent results.

---

## 2) External networking: Floating IPs fail even though Neutron “looks fine”

### Symptom

- `br-ex` exists
- Neutron router has `qg-*` interface
- Floating IPs stop working (ping/SSH)
- Host cannot ping router external IP (example: `172.24.4.104`)

### Checks

```bash
ip -4 addr show br-ex
ip route | head
ping -c 2 172.24.4.104
```

If `br-ex` has no IP in the external CIDR, Linux will not consider that network “directly reachable”.

### Fix (one-line, immediate)

Add an IP in the external network to `br-ex`:

```bash
sudo ip addr add 172.24.4.1/24 dev br-ex
```

This instantly:
- gives the host a presence on the external network
- creates a connected route (`172.24.4.0/24 dev br-ex`)
- enables ARP and restores reachability to the Neutron router external IP

---

## 3) Rewire `br-ex` to a NIC (OpenStack running inside a VM)

### Symptom

- External connectivity works briefly, then breaks after reboots/restacks
- `br-ex` exists but is not attached to the expected NIC
- Floating IPs don’t work

### Fix (rewire live)

> Do this from the VM console, not via SSH, because you can drop connectivity while moving IPs.

```bash
# 1) Attach NIC to br-ex
sudo ovs-vsctl --may-exist add-port br-ex enp1s0

# 2) Bring links up
sudo ip link set br-ex up
sudo ip link set enp1s0 up

# 3) Move the management IP from NIC → br-ex
sudo ip addr flush dev enp1s0
sudo ip addr add 192.168.122.109/24 dev br-ex

# 4) Restore default route via NAT gateway
sudo ip route replace default via 192.168.122.1

# 5) Ensure br-ex has an IP on the external CIDR (critical)
sudo ip addr add 172.24.4.1/24 dev br-ex
```

Verify:

```bash
ip -4 addr show br-ex
ip route | head
ping -c 3 192.168.122.1
ping -c 3 172.24.4.104
```

Optional cleanup (if a stale port exists):

```bash
sudo ovs-vsctl --if-exists del-port br-int <stale-tap-port>
```

---

## 4) Persist `br-ex` across reboots (Ubuntu 24.04: Netplan + OVS)

### Symptom

- Floating IPs work until reboot, then fail again
- Manual `ip addr add ...` fixes it temporarily

### Fix (Netplan)

Edit a netplan file (commonly `/etc/netplan/50-cloud-init.yaml`) to match the working runtime state:

```yaml
network:
  version: 2
  renderer: networkd

  ethernets:
    enp1s0:
      dhcp4: no
      dhcp6: no

  bridges:
    br-ex:
      interfaces: [enp1s0]
      openvswitch: {}
      addresses:
        - 192.168.122.109/24
        - 172.24.4.1/24
      routes:
        - to: default
          via: 192.168.122.1
      nameservers:
        addresses: [8.8.8.8, 1.1.1.1]
```

Apply safely:

```bash
sudo netplan try
```

Then reboot and re-check:

```bash
ip -4 addr show br-ex
ip route | head
ping -c 3 172.24.4.104
```

---

## 5) `ovs-vsctl: command not found` inside an instance

### Symptom
You run `ovs-vsctl` inside a tenant VM and it fails.

### Explanation
This is expected. `ovs-vsctl` is an Open vSwitch management tool on the OpenStack node. Instances attach via virtio/tap interfaces; they do not manage OVS.

### Fix
Run OVS commands on the DevStack/OpenStack host.

---

## 6) cloud-init jobs “do nothing” or emit no markers

### Symptom

- Instance boots
- `nova-mlops openstack logs <job>` shows cloud-init ran
- Your job markers (e.g. `[NOVA-MLOPS]`) never appear

### Root cause A: `/bin/sh` executes `runcmd` (dash), not bash

If your script contains bash-isms like `set -o pipefail`, dash will fail with:

```
set: Illegal option -o pipefail
```

### Fix: force bash explicitly

Wrap your commands in `bash -lc`:

```yaml
runcmd:
  - [ bash, -lc, |
      set -euxo pipefail
      echo "[NOVA-MLOPS] job=sentiment-demo starting" | tee /dev/console
      # … your job logic …
    ]
```

### Root cause B: package installs fail due to broken egress (common after restack)

Symptoms in logs include `apt` showing `Ign:` lines or cloud-init “failure installing packages”.

**Checks**
- Router exists and has external gateway
- IP forwarding on host is enabled
- NAT rules exist and are not reset by restack/reboot

---

## 7) Quick sanity commands (copy/paste)

### Hypervisor sanity

```bash
kvm-ok
virsh list --all
```

### OpenStack external network sanity

```bash
ip -4 addr show br-ex
ip route | head
ping -c 2 172.24.4.104
```

### Neutron router sanity (DevStack defaults vary)

```bash
openstack router list
openstack router show router1 -f yaml -c external_gateway_info -c interfaces_info
```
