# Gap Analysis Report: Staging vs Pub/RHEL10.2

**Date:** 2025-07-17
**Repos Compared:**
- **Staging (baseline, working):** `/root/staging/omnia/src/orchestrator/`
- **Pub/RHEL10.2 (target, broken):** `/root/rohith/omnia/src/orchestrator/`

**Summary:** Pub/RHEL10.2 contains the IPv6 IPoIB dual-stack feature (ER-ORCH-005) merged on top of staging, plus several non-IPv6 fixes. This report identifies regressions introduced during that merge, improvements that should be retained, and the full IPv6 feature file inventory.

**Total files differing:** 35 modified + 15 new in pub + 0 missing from pub

---

## Table of Contents

1. [Section A: Regressions — Must Fix](#section-a-regressions--must-fix)
2. [Section B: Improvements — Must Keep](#section-b-improvements--must-keep)
3. [Section C: IPv6 Feature — New Files](#section-c-ipv6-feature--new-files)
4. [Section D: IPv6 Feature — Modified Files (Backward Compatible)](#section-d-ipv6-feature--modified-files-backward-compatible)
5. [Section E: Summary Action Items](#section-e-summary-action-items)

---

## Section A: Regressions — Must Fix

These are changes in pub that **break or risk breaking** the working staging behavior.

### A1. PXE Failure Default Changed — Silent Failure (HIGH)

**File:** `roles/pxe_boot_reporting/tasks/main.yml`

| | Staging (correct) | Pub (changed) |
|---|---|---|
| `defer_pxe_failure` default | `false` | `true` |
| Behavior when PXE fails | **Hard-fail** — stops the play | **Warn and continue** — silently proceeds |

**Impact:** Existing deployments that don't explicitly set `defer_pxe_failure` will silently continue past PXE boot and node-registration failures instead of stopping. Failed nodes proceed to downstream tasks, potentially causing cascading issues.

**Root Cause:** Default policy changed from fail-closed to fail-open during the IPv6 merge.

**Recommended Fix:** Restore default to `false`:

```yaml
# Warning task (can keep the warning, but only when user opts in)
when:
  - pxeboot_failed | bool
  - defer_pxe_failure | default(false) | bool

# Fail task
when:
  - pxeboot_failed | bool
  - not (defer_pxe_failure | default(false) | bool)
```

---

### A2. Undefined `compiler_login_list` Loop Crash (HIGH)

**File:** `roles/slurm_config/tasks/build_slurm_conf.yml`

Pub added NodeAddr injection for compiler-login nodes, but the loop at line 51 uses:

```yaml
loop: "{{ compiler_login_list }}"
when: compiler_login_list is defined and (compiler_login_list | length > 0)
```

Ansible may evaluate the `loop` expression **before** the `when` condition. If `compiler_login_list` is undefined, the task fails even though the `when` guard checks for definition.

**Impact:** Deployments without compiler-login nodes fail during Slurm configuration.

**Recommended Fix:**

```yaml
loop: "{{ compiler_login_list | default([]) }}"
```

---

### A3. Unconditional `inject_ib_nodeaddr.yml` Include (MEDIUM)

**File:** `roles/slurm_config/tasks/confs.yml`

Pub unconditionally includes `inject_ib_nodeaddr.yml` when Slurm is enabled:

```yaml
- name: Inject IB NodeAddr into node_params
  ansible.builtin.include_tasks: inject_ib_nodeaddr.yml
  when:
    - node_params | length > 0
    - "'slurm' in conf_files"
```

Inside `inject_ib_nodeaddr.yml`, line 38 references:

```yaml
path: "{{ hostvars['localhost']['pxe_mapping_file_path'] }}"
```

If `pxe_mapping_file_path` is undefined (no PXE mapping configured), Jinja2 templating fails before the `stat` task runs.

**Impact:** Slurm configuration fails in deployments without a PXE mapping file.

**Recommended Fix:** Add a guard condition:

```yaml
when:
  - node_params | length > 0
  - "'slurm' in conf_files"
  - hostvars['localhost']['pxe_mapping_file_path'] | default('') | length > 0
```

---

### A4. `gpu_params` Initialization Removed (MEDIUM)

**File:** `roles/slurm_config/tasks/read_node_homogeneous.yml`

| Staging | Pub |
|---|---|
| Initializes `gpu_params` for GRES-enabled homogeneous nodes | Only sets `node_params`, drops `gpu_params` initialization |

Staging line:

```yaml
- name: Add to Nodeparam dict
  ansible.builtin.set_fact:
    node_params: "{{ node_params + [proc_params] }}"
    gpu_params: "{{ gpu_params | default({}) | combine({item: []} if group_specs.gres is defined else {}) }}"
```

Pub line:

```yaml
- name: Add to Nodeparam dict
  ansible.builtin.set_fact:
    node_params: "{{ node_params + [proc_params] }}"
```

**Impact:** Latent regression. If any downstream consumer depends on `gpu_params` being initialized for homogeneous nodes with GRES configuration, it will fail or produce incorrect Slurm config.

**Recommended Fix:** Restore the staging initialization:

```yaml
gpu_params: "{{ gpu_params | default({}) | combine({item: []} if group_specs.gres is defined else {}) }}"
```

---

### A5. IB Script Template Rendered Without Guard for No-IB Deployments (MEDIUM)

**Files:**
- `roles/provision_common/templates/metadata_svc/ms-group-default_x86_64.yaml.j2`
- `roles/provision_common/templates/metadata_svc/ms-group-os_x86_64.yaml.j2`
- `roles/provision_common/templates/metadata_svc/ms-group-os_aarch64.yaml.j2`

Pub adds to ALL three templates:

```yaml
write_files:
  - path: /usr/local/bin/configure-ib-network.sh
    content: |
      {{ lookup('template', 'templates/doca-ofed/configure-ib-network.sh.j2') | indent(12) }}
runcmd:
  - bash /usr/local/bin/configure-ib-network.sh || echo "IB network configuration failed (non-critical)"
```

The IB script has runtime guards (exits if no Mellanox hardware, exits if no IB_NIC_NAME). However, the **template rendering** at provision time references `hostvars['localhost']['read_mapping_file']['dict']` inside the script template.

**Impact:** If `read_mapping_file` is undefined in a no-IB deployment, template rendering fails during the provisioning phase, before the runtime guards can help.

**Recommended Fix:** Guard the template inclusion with a Jinja2 conditional:

```jinja2
{% if hostvars['localhost']['read_mapping_file'] is defined %}
write_files:
  - path: /usr/local/bin/configure-ib-network.sh
    ...
runcmd:
  - bash /usr/local/bin/configure-ib-network.sh || echo "..."
{% endif %}
```

Or use `| default({})` on the mapping file access inside `configure-ib-network.sh.j2`.

---

### A6. `storage_config_validator.py` — Missing Legacy Header Support (LOW)

**File:** `plugins/module_utils/orchestrator_validation/validators/storage_config_validator.py`

Pub's `_mapping_targets()` checks:

```python
if raw_header != list(CANONICAL_HEADERS):
    return None
```

But only imports `CANONICAL_HEADERS` (12-column). Legacy 11-column CSVs with `IB_IP` are not recognized, meaning storage-target validation is silently skipped for legacy mapping files.

**Impact:** Storage validation silently skipped for legacy CSV users. Other validators (`pxe_mapping_validator.py`, `omnia_config_validator.py`) correctly handle legacy conversion; this one was missed.

**Recommended Fix:** Import `LEGACY_HEADERS` and add the same conversion logic:

```python
from .pxe_mapping_validator import CANONICAL_HEADERS, LEGACY_HEADERS, read_mapping

# In _mapping_targets():
if raw_header == list(LEGACY_HEADERS):
    raw_header = list(CANONICAL_HEADERS)
    rows = [(n, vals + [""]) for n, vals in rows]
elif raw_header != list(CANONICAL_HEADERS):
    return None
```

---

## Section B: Improvements — Must Keep

These are changes where **pub is correct and staging is wrong**. These should be retained in pub and considered for backport to staging.

### B1. OpenCHAMI Reconciler — Ownership Labels Placement (API FIX)

**File:** `plugins/module_utils/openchami/reconciler.py`

| Staging (incorrect) | Pub (correct) |
|---|---|
| `{"metadata": {"name": ...}, "spec": ..., "labels": ownership}` | `{"metadata": {"name": ..., "labels": ownership}, "spec": ...}` |

Staging puts ownership labels at the **top level** of the payload. The OpenCHAMI/Fabrica resource envelope requires labels inside `metadata.labels`. Additionally, the reconciler's own `_has_ownership()` method reads from `resource["metadata"]["labels"]`, making staging's write and read paths inconsistent.

**Affected resources:** Metadata groups, ClusterDefaults, and InstanceInfo — all three reconciliation paths.

**Verdict:** Pub is correct. Keep and backport to staging.

---

### B2. PXE Mapping Permission Hardening (SECURITY)

**File:** `roles/orchestrator_setup/tasks/main.yml`

Pub adds:

```yaml
- name: Harden PXE mapping file permissions (0640)
  ansible.builtin.file:
    path: "{{ pxe_mapping_file_path }}"
    mode: "0640"
  when:
    - pxe_mapping_file_path | default('') | length > 0
    - pxe_mapping_file_path is file
```

Prevents validation failure when the mapping file has insecure `0644` permissions (e.g., after copy from discovery output).

**Verdict:** Keep and backport to staging.

---

### B3. Input File Permission Hardening (SECURITY)

**File:** `domain-init.sh`

Pub adds `harden_input_permissions()`:

```bash
harden_input_permissions() {
    local dest_dir="${ORCHESTRATOR_DATA_PATH}/input/${OMNIA_PROJECT_NAME}"
    [ -d "$dest_dir" ] || return 0
    chmod 0750 "$dest_dir"
    find "$dest_dir" -mindepth 1 -type d -exec chmod 0750 {} +
    find "$dest_dir" -type f -exec chmod g-w,o-rwx {} +
}
```

Sets directories to `0750` and removes group-write/other-access on files.

**Verdict:** Keep and backport to staging.

---

### B4. OpenLDAP Cleanup — Dry-Run Guards (CORRECTNESS)

**File:** `roles/cleanup/components/openldap/tasks/cleanup.yml`

Pub adds `not (dry_run | default(false) | bool)` guards on destructive operations:
- Stop/disable service
- Remove container
- Remove Quadlet file
- Remove data directory

Staging's "dry run" mode could still execute all these destructive actions.

**Verdict:** Keep and backport to staging.

---

### B5. Conditional `dbd_list[0]` Access (BUG FIX)

**File:** `roles/slurm_config/tasks/confs.yml`

| Staging (crashes if empty) | Pub (guarded) |
|---|---|
| `'AccountingStorageHost': dbd_list[0]` | `dbd_list[0] if dbd_list \| length > 0 else {}` |

**Verdict:** Keep and backport to staging.

---

### B6. `compiler_login_list | default([])` in Directory Setup (BUG FIX)

**File:** `roles/slurm_config/tasks/create_slurm_dir.yml`

Pub adds `default([])` to prevent failure when `compiler_login_list` is undefined.

**Verdict:** Keep and backport to staging.

---

### B7. Auto-Restart Slurmctld (IMPROVEMENT)

**File:** `roles/slurm_config/tasks/check_ctld_running.yml`

Pub adds automatic `slurmctld` restart if stopped/failed after config update (default: `restart_slurm_services=true`).

**Verdict:** Keep, but review restart policy for environments where intentional controller downtime is expected.

---

### B8. Credential Condition Simplification (NEUTRAL)

**File:** `roles/orchestrator_common/tasks/decrypt_include_encrypt.yml`

Pub simplifies two `when` conditions to a single OR expression. Same behavior, cleaner formatting.

**Verdict:** Keep (cosmetic).

---

## Section C: IPv6 Feature — New Files

These are new files added in pub for the IPv6/IPoIB dual-stack feature (ER-ORCH-005). They do not exist in staging and are pure additions.

### C1. New Ansible Modules

| File | Purpose |
|---|---|
| `plugins/modules/benchmark_ib_ipv6.py` | IPv6 performance benchmarks (allocation latency, throughput parity) |
| `plugins/modules/collect_ib_ipv6_evidence.py` | HCA model, firmware, driver, IB switch, OS/kernel evidence collection |
| `plugins/modules/render_ib_ipv6_config.py` | Renders NetworkManager/cloud-init/SMD config artifacts |
| `plugins/modules/validate_ib_ipv6_allocation.py` | Validates IPv6 allocations from PXE mapping (format, uniqueness, subnet) |
| `plugins/modules/verify_ib_ipv6_state.py` | Post-config verification (DAD, routes, reachability, OpenSM) |

### C2. New Module Utils

| File | Purpose |
|---|---|
| `module_utils/orchestrator_validation/renderers/__init__.py` | Package initializer |
| `module_utils/orchestrator_validation/renderers/address_verifier.py` | Address state verification engine (HEALTHY/DEGRADED/FAILED/RECOVERY) |
| `module_utils/orchestrator_validation/renderers/nm_renderer.py` | NetworkManager profile renderer for dual-stack/IPv6-only/IPv4-only |
| `module_utils/orchestrator_validation/validators/ib_ipv6_allocation_validator.py` | IPv6 allocation validation logic |

### C3. New Role

| Directory | Purpose |
|---|---|
| `roles/ib_ipv6_config/` | Complete IPoIB IPv6 config pipeline: validate, render, publish to SMD/BSS, verify |

### C4. New Playbooks

| File | Purpose |
|---|---|
| `playbooks/provision/configure_ib_ipv6.yml` | 4-stage IPv6 IPoIB configuration pipeline |
| `playbooks/validate/validate_ib_ipv6_release.yml` | Release evidence and benchmark playbook |

### C5. New Task File

| File | Purpose |
|---|---|
| `roles/slurm_config/tasks/inject_ib_nodeaddr.yml` | Injects IB addresses into Slurm NodeAddr/SlurmctldHost/EnableIPv6 |

### C6. New Documentation

| File | Purpose |
|---|---|
| `docs/ipv6-infiniband-configuration.md` | IPv6 IPoIB configuration guide (271 lines) — modes, prerequisites, hardware |
| `docs/ipv6-upgrade-guide.md` | Migration guide from IPv4-only to dual-stack (146 lines) |

---

## Section D: IPv6 Feature — Modified Files (Backward Compatible)

These files were modified to support IPv6 while maintaining legacy backward compatibility. Analysis confirms they **do not break** existing IPv4-only deployments using the legacy 11-column CSV or old `network_spec.yml`.

### D1. Validators and Schema

| File | Change | Legacy Compatible? |
|---|---|---|
| `pxe_mapping_validator.py` | 12-column canonical headers + `LEGACY_HEADERS` detection/conversion | **Yes** — exact legacy `IB_IP` header detected and converted to `IB_IPV4` + empty `IB_IPV6` |
| `omnia_config_validator.py` | Imports `LEGACY_HEADERS`/`CANONICAL_HEADERS`, converts before downstream use | **Yes** — `IB_IP` rows normalized before all consumers |
| `network_spec_validator.py` | New `ib_network_from_config()` falls back to `subnet`/`netmask_bits` | **Yes** — absent `ib_addr_mode` defaults to IPv4 behavior |
| `network_spec.json` | `oneOf` schema with legacy branch accepting old `subnet`/`netmask_bits` | **Yes** — `ib_addr_mode` is optional in legacy branch |
| `k8s_ha_validator.py` | `IB_IP` -> `IB_IPV4` in address tracking | **Yes** — `load_pxe_mapping_rows()` converts before this code runs |
| `orchestrator_messages.py` | References updated to `IB_IPV4`/`IB_IPV6`; 6 new IPv6 messages added | **Yes** — consistent with post-conversion field names |

### D2. Network Fact Propagation (Variable Rename)

All old `ib_network_subnet` / `ib_network_netmask_bits` references in staging have been **consistently replaced** with `ib_network_ipv4_subnet` / `ib_network_ipv4_netmask_bits` in pub. **No stale old-name references remain.**

| Staging Fact | Pub Fact | Files Updated |
|---|---|---|
| `ib_network_subnet` | `ib_network_ipv4_subnet` | `validate_preamble`, `include_software_config`, `provision_preamble` |
| `ib_network_netmask_bits` | `ib_network_ipv4_netmask_bits` | Same 3 files + `configure-ib-network.sh.j2` |
| *(new)* | `ib_network_ipv6_subnet` | All 3 fact-setting files |
| *(new)* | `ib_network_ipv6_netmask_bits` | All 3 fact-setting files |
| *(new)* | `ib_network_addr_mode` | All 3 fact-setting files + `configure-ib-network.sh.j2` + `inject_ib_nodeaddr.yml` |

All new facts use `| default('')` fallback from legacy field names, ensuring old `network_spec.yml` files continue to work.

### D3. Templates and Scripts

| File | Change | Legacy Compatible? |
|---|---|---|
| `configure-ib-network.sh.j2` | IPv6 mode branching; `IB_IPV4`/`IB_IPV6` maps; dmidecode SIGPIPE fix | **Yes** — IPv4-only mode preserves existing behavior; empty `IB_ADDR_MODE` treated as IPv4-only |
| `ms-group-default_x86_64.yaml.j2` | IB script injection via write_files/runcmd | **See A5** — needs guard for no-IB deployments |
| `ms-group-os_x86_64.yaml.j2` | Same IB script injection | **See A5** |
| `ms-group-os_aarch64.yaml.j2` | Same IB script injection | **See A5** |

### D4. Orchestrator Flow and Slurm

| File | Change | Legacy Compatible? |
|---|---|---|
| `orchestrator.yml` | Inserts `configure_ib_ipv6.yml` between provisioning and PXE boot | **Yes** — gated on `ib_addr_mode` |
| `confs.yml` | IB NodeAddr injection + conditional `dbd_list` + `compiler_login_list` default | **See A3** — needs PXE mapping guard |
| `build_slurm_conf.yml` | NodeAddr from PXE IB map for login/compiler nodes | **See A2** — needs `compiler_login_list` default |
| `create_slurm_dir.yml` | IB controller addresses + `compiler_login_list` default | **Yes** — `default(ctld_list)` fallback works |
| `check_ctld_running.yml` | Auto-restart slurmctld | **Yes** — See B7 |
| `read_node_homogeneous.yml` | gpu_params dropped | **See A4** — restore staging behavior |

### D5. Documentation and Samples

| File | Change |
|---|---|
| `CHANGELOG.md` | IPoIB IPv6 dual-stack release notes (ER-ORCH-005) |
| `docs/troubleshooting.md` | 12-column reference + 5 new IPv6/IB troubleshooting sections |
| `playbooks/pxeboot/README.md` | 12-column PXE format with `IB_IPV4`/`IB_IPV6` |
| `input/network_spec.yml` | Updated to new `ipv4_subnet`/`ipv6_subnet` format |
| `input/pxe_mapping_file.csv` | 12-column format with descriptive hostnames |
| `examples/pxe_mapping_file.csv` | 12-column format |
| `examples/pxe_mapping_file_slurm_service_k8s_hybrid.csv` | 12-column format |

---

## Section E: Summary Action Items

### Regressions to Fix (Priority Order)

| # | Issue | File | Severity | Fix |
|---|---|---|---|---|
| 1 | `defer_pxe_failure` default changed `false` -> `true` | `pxe_boot_reporting/tasks/main.yml` | **HIGH** | Restore `default(false)` |
| 2 | `compiler_login_list` loop without `default([])` | `slurm_config/tasks/build_slurm_conf.yml` | **HIGH** | Add `\| default([])` to loop |
| 3 | Unconditional `inject_ib_nodeaddr.yml` include | `slurm_config/tasks/confs.yml` | **MEDIUM** | Add `pxe_mapping_file_path` guard |
| 4 | `gpu_params` initialization removed | `slurm_config/tasks/read_node_homogeneous.yml` | **MEDIUM** | Restore staging `gpu_params` line |
| 5 | IB script template rendered without no-IB guard | 3x `ms-group-*.yaml.j2` templates | **MEDIUM** | Add Jinja2 conditional or `default({})` |
| 6 | `storage_config_validator.py` missing legacy headers | `storage_config_validator.py` | **LOW** | Add `LEGACY_HEADERS` conversion |

### Improvements to Keep (Do NOT Revert)

| # | Improvement | File | Reason |
|---|---|---|---|
| 1 | OpenCHAMI labels inside `metadata.labels` | `openchami/reconciler.py` | API correctness fix |
| 2 | PXE mapping permission hardening (0640) | `orchestrator_setup/tasks/main.yml` | Security |
| 3 | Input file permission hardening | `domain-init.sh` | Security |
| 4 | OpenLDAP dry-run guards | `cleanup/openldap/tasks/cleanup.yml` | Correctness |
| 5 | Conditional `dbd_list[0]` access | `slurm_config/tasks/confs.yml` | Bug fix |
| 6 | `compiler_login_list \| default([])` in dir setup | `slurm_config/tasks/create_slurm_dir.yml` | Bug fix |
| 7 | Auto-restart slurmctld after config update | `slurm_config/tasks/check_ctld_running.yml` | Operational improvement |
[root@oim omnia]# cat /root/rohith/omnia/IPV6_CHANGES_IMPACT_ANALYSIS.md
# IPv6 Feature Changes Impact Analysis

**Date:** 2025-07-17
**Scope:** Files in staging (`/root/staging/omnia/src/orchestrator/`) that were modified in pub/rhel10.2 (`/root/rohith/omnia/src/orchestrator/`) for the IPv6 IPoIB dual-stack feature (ER-ORCH-005).

**Purpose:** For each existing staging file that was changed for IPv6, determine whether the change impacts existing IPv4-only deployments.

**Test Configuration (Legacy IPv4-Only):**
- 11-column CSV with `IB_IP` header (no `IB_IPV4`/`IB_IPV6`)
- `network_spec.yml` with `subnet`/`netmask_bits` (no `ipv4_subnet`/`ib_addr_mode`)
- No IPv6 addresses configured anywhere

---

## Table of Contents

1. [Impact Summary Table](#1-impact-summary-table)
2. [BREAKING Changes](#2-breaking-changes)
3. [RISKY Changes](#3-risky-changes)
4. [SAFE Changes](#4-safe-changes)
5. [Recommendations](#5-recommendations)

---

## 1. Impact Summary Table

| # | File | Verdict | IPv4 Impact? | Details |
|---|---|---|---|---|
| 1 | `playbooks/orchestrator.yml` | **BREAKING** | YES | New IPoIB playbook imported without `when` guard; fails on missing prerequisites even when IPv6 is not configured |
| 2 | `slurm_config/tasks/confs.yml` | **RISKY** | Conditional | `inject_ib_nodeaddr.yml` included without `pxe_mapping_file_path` guard; can fail if variable is undefined |
| 3 | `slurm_config/tasks/create_slurm_dir.yml` | **RISKY** | Conditional | Uses `_ctld_ib_addrs` for `conf_server`; changes Slurm controller address from hostname to IB IP when IB mapping exists |
| 4 | `ms-group-default_x86_64.yaml.j2` | **RISKY** | Conditional | IB script unconditionally injected; template rendering may fail if `read_mapping_file` is undefined |
| 5 | `ms-group-os_x86_64.yaml.j2` | **RISKY** | Conditional | Same as above |
| 6 | `ms-group-os_aarch64.yaml.j2` | **RISKY** | Conditional | Same as above |
| 7 | `omnia_config_validator.py` | **RISKY** | Conditional | Adds mandatory K8s HA validation; existing K8s configs lacking `enable_k8s_ha`/`virtual_ip_address` now fail |
| 8 | `configure-ib-network.sh.j2` | SAFE | NO | IPv4 path preserved; legacy `IB_IP` fallback works; `ib_addr_mode=""` defaults to IPv4 |
| 9 | `pxe_mapping_validator.py` | SAFE | NO | Legacy 11-column `IB_IP` header detected and converted to canonical `IB_IPV4` + empty `IB_IPV6` |
| 10 | `network_spec_validator.py` | SAFE | NO | `ib_network_from_config()` falls back to `subnet`/`netmask_bits`; absent `ib_addr_mode` defaults to IPv4 |
| 11 | `network_spec.json` | SAFE | NO | `oneOf` schema with legacy branch accepting old `subnet`/`netmask_bits`; `ib_addr_mode` optional |
| 12 | `k8s_ha_validator.py` | SAFE | NO | No actual file diff; invocation change is in `omnia_config_validator.py` |
| 13 | `orchestrator_messages.py` | SAFE | NO | Error text updated `IB_IP` -> `IB_IPV4`; 6 new IPv6 messages added; no functional change |
| 14 | `include_software_config.yml` | SAFE | NO | `ib_network_ipv4_netmask_bits` falls back to `network_data.ib_network.netmask_bits` |
| 15 | `validate_preamble/tasks/main.yml` | SAFE | NO | Same fallback as above |
| 16 | `provision_preamble.yml` | SAFE | NO | Same fallback as above |
| 17 | `slurm_config/tasks/build_slurm_conf.yml` | SAFE | NO | `_pxe_ib_nodeaddr_map | default({})` resolves to `{'NodeName': item}` when maps undefined |
| 18 | `slurm_config/tasks/read_node_homogeneous.yml` | SAFE | NO | Removes `gpu_params` bookkeeping; no IPv4 networking impact |

---

## 2. BREAKING Changes

### 2.1 `playbooks/orchestrator.yml` — Unconditional IPoIB Playbook Import

**Staging:** After provisioning validation, proceeds directly to PXE boot.

**Pub:** Inserts a new playbook import between provisioning and PXE boot:

```yaml
# pub lines 260-266
- name: Configure IPoIB addressing
  ansible.builtin.import_playbook: provision/configure_ib_ipv6.yml
  tags:
    - execute
    - provision
    - ib_ipv6
```

The comment says *"runs only when ib_addr_mode is set"*, but **there is no `when:` condition** on the import.

**What happens with a legacy IPv4-only deployment:**

1. The playbook is statically imported and runs with `--tags execute` or `--tags provision`
2. Inside `configure_ib_ipv6.yml`, `_ib_ipv6_enabled` evaluates to `false` (no `ib_addr_mode` set)
3. A "Skipping" debug message fires, but **the role still executes**
4. The `ib_ipv6_config` role's `tasks/main.yml` runs and stats the PXE mapping file
5. If the PXE mapping file or allocation JSON is missing, **the role fails with an error**

```
TASK [ib_ipv6_config : Fail if PXE mapping file is missing]
fatal: [localhost]: FAILED! =>
  msg: "IPoIB IPv6 PXE mapping file not found. Path: ..."
```

**Impact:** Every IPv4-only orchestrator run that uses `--tags execute` or `--tags provision` will fail at this step.

**Root Cause:** The role does not check `_ib_ipv6_enabled` before running. The debug "Skipping" message is cosmetic — it doesn't actually skip anything.

**Recommended Fix:** Gate the role inclusion on the enabled flag:

```yaml
# Option A: Guard the role with when
roles:
  - role: ib_ipv6_config
    when: _ib_ipv6_enabled | default(false) | bool

# Option B: Use include_role instead of static role inclusion
tasks:
  - name: Configure IPoIB addressing
    ansible.builtin.include_role:
      name: ib_ipv6_config
    when: _ib_ipv6_enabled | default(false) | bool
```

---

## 3. RISKY Changes

### 3.1 `slurm_config/tasks/confs.yml` — Unconditional `inject_ib_nodeaddr.yml` Include

**Staging:** Builds `slurm.conf` directly from hardware-discovered `node_params`. No IB address injection.

**Pub:** Adds before `build_slurm_conf.yml`:

```yaml
# pub lines 235-240
- name: Inject IB NodeAddr into node_params
  ansible.builtin.include_tasks: inject_ib_nodeaddr.yml
  when:
    - node_params | length > 0
    - "'slurm' in conf_files"
```

**What happens with legacy IPv4-only:**

| Scenario | Result |
|---|---|
| `pxe_mapping_file_path` defined, file exists, has IB IPv4 addresses | `NodeAddr` added to `node_params`; `SlurmctldHost` uses IB IPv4 instead of hostname |
| `pxe_mapping_file_path` defined, file missing | Graceful skip ("no PXE mapping file") |
| `pxe_mapping_file_path` **undefined** | **FAILS** — Jinja2 cannot template `stat.path` with undefined variable |

Additionally, when the mapping exists and produces results:

```yaml
# SlurmctldHost changes from:
'SlurmctldHost': ctld_list              # e.g., ['controller']
# to:
'SlurmctldHost': _ctld_ib_list          # e.g., ['controller(192.168.0.10)']

# conf_server changes from:
--conf-server controller:6817
# to:
--conf-server 192.168.0.10:6817
```

This is an intentional behavioral change for IB-enabled deployments but **may be unexpected** for existing IPv4-only setups that previously used hostnames.

**Recommended Fix:**

```yaml
when:
  - node_params | length > 0
  - "'slurm' in conf_files"
  - hostvars['localhost']['pxe_mapping_file_path'] | default('') | length > 0
```

---

### 3.2 `slurm_config/tasks/create_slurm_dir.yml` — IB Controller Addresses

**Staging:**

```yaml
conf_server: "--conf-server {{ ctld_list | map(...) | join(',') }}"
```

**Pub:**

```yaml
conf_server: >-
  --conf-server {{ (_ctld_ib_addrs | default(ctld_list)) | map(...) | join(',') }}
```

**Impact:** When `_ctld_ib_addrs` is populated by `inject_ib_nodeaddr.yml`, slurmd configless clients contact the IB address instead of the hostname. When `_ctld_ib_addrs` is undefined, `default(ctld_list)` preserves staging behavior.

**Risk Level:** Low if `inject_ib_nodeaddr.yml` is properly guarded. If the injector ran and populated addresses, this is intentional behavior.

---

### 3.3 Metadata Templates — IB Script Injected Unconditionally (3 files)

**Files:**
- `roles/provision_common/templates/metadata_svc/ms-group-default_x86_64.yaml.j2`
- `roles/provision_common/templates/metadata_svc/ms-group-os_x86_64.yaml.j2`
- `roles/provision_common/templates/metadata_svc/ms-group-os_aarch64.yaml.j2`

**Staging:** Templates end with root user config (line 19). No IB script.

**Pub:** All three templates add:

```yaml
write_files:
  - path: /usr/local/bin/configure-ib-network.sh
    owner: root:root
    permissions: '{{ file_mode_755 }}'
    content: |
      {{ lookup('template', 'templates/doca-ofed/configure-ib-network.sh.j2') | indent(12) }}

runcmd:
  - bash /usr/local/bin/configure-ib-network.sh || echo "IB network configuration failed (non-critical)"
```

**What happens with legacy IPv4-only:**

| Scenario | Result |
|---|---|
| Node has Mellanox HW + IB mapping exists | Script runs, configures IPv4 IB (same as staging's direct IB config) |
| Node has Mellanox HW + no IB mapping | Script exits gracefully (no `IB_NIC_NAME`) |
| Node has no Mellanox HW | Script exits at `lspci` check |
| `read_mapping_file` hostvar **undefined** | **Template rendering fails** during provisioning phase |

**Root Cause:** The template `lookup()` renders `configure-ib-network.sh.j2`, which iterates over `hostvars['localhost']['read_mapping_file']['dict']`. If that hostvar is undefined, Jinja2 fails.

**Runtime Impact:** If the template renders successfully, the script has robust runtime guards and is non-fatal (`|| echo "..."`). The risk is at **template render time**, not runtime.

**Recommended Fix:**

```jinja2
{% if hostvars['localhost']['read_mapping_file'] is defined %}
      write_files:
        - path: /usr/local/bin/configure-ib-network.sh
          ...
      runcmd:
        - bash /usr/local/bin/configure-ib-network.sh || echo "..."
{% endif %}
```

---

### 3.4 `omnia_config_validator.py` — New K8s HA Validation

**Staging:** Validates K8s network CIDRs, overlap, and storage references. Does not invoke K8s HA validation.

**Pub:** After network validation, invokes:

```python
# pub lines 1088-1095
from .k8s_ha_validator import validate_deployed_cluster_ha

for deployed_cluster in deployed_clusters:
    errors.extend(
        validate_deployed_cluster_ha(
            deployed_cluster, input_project_dir, logger
        )
    )
```

**Impact:** Existing IPv4 K8s configurations that previously passed but lack `enable_k8s_ha` or `virtual_ip_address` now fail validation with:

```
enable_k8s_ha must be set to a boolean
virtual_ip_address must be set to an IPv4 address
```

**Note:** This is NOT an IPv6-related change. It was bundled into the same merge but affects pure IPv4 K8s deployments.

**Recommended Fix:** Either:
- Make K8s HA validation opt-in (only run when `enable_k8s_ha` is present)
- Or ensure all existing K8s configurations include the required HA fields

---

## 4. SAFE Changes

These files were modified for IPv6 but **do not impact** existing IPv4-only deployments using legacy CSV and old `network_spec.yml`.

### 4.1 `configure-ib-network.sh.j2` — IB Network Script

**What changed:**
- `NETMASK_BITS` reads `ib_network_ipv4_netmask_bits` (was `ib_network_netmask_bits`)
- Added `IPV6_NETMASK_BITS` and `IB_ADDR_MODE` variables
- IPv4 address map uses `node.IB_IPV4 | default(node.IB_IP | default(''))` — explicit legacy fallback
- Added `ADMIN_IB_IPV6_MAP` (empty for legacy CSV)
- IP configuration section branches on `IB_ADDR_MODE`:
  - `ipv6-only`: skips IPv4, configures IPv6
  - `ipv4-only` or empty: configures IPv4 only (same as staging)
  - `dual-stack`: configures both
- Added `dmidecode` SIGPIPE fix (robustness improvement, not IPv6-specific)

**Legacy IPv4-only path through pub code:**

```
IB_ADDR_MODE=""  (no ib_addr_mode in network_spec)
IB_IPV6=""       (no IB_IPV6 column in legacy CSV)
IB_IPV4=<IB_IP>  (fallback from undefined IB_IPV4 to IB_IP)
NETMASK_BITS=<legacy netmask_bits>  (fallback from ipv4_netmask_bits to netmask_bits)

-> IPv4 configured via NM or iproute2 (identical to staging)
-> IPv6 skipped (IB_ADDR_MODE="" && IB_IPV6="" triggers skip)
-> DNS configured if IB_IPV4 is non-empty (same condition as staging)
```

**Verdict:** SAFE. The legacy fallback chain ensures identical IPv4 behavior.

---

### 4.2 `pxe_mapping_validator.py` — PXE Mapping Validation

**What changed:**
- `CANONICAL_HEADERS`: 12-column with `IB_IPV4`, `IB_IPV6` (was 11-column with `IB_IP`)
- `LEGACY_HEADERS`: preserves the old 11-column definition
- `validate()`: detects legacy header and converts:
  - Renames `IB_IP` -> `IB_IPV4` in field list
  - Appends empty `IB_IPV6` to every row
- `_validate_addresses()`: validates `IB_IPV4` as IPv4 (was `IB_IP`)
- `_validate_ib_pair()`: mode-aware pairing; empty `ib_addr_mode` -> default IPv4 pairing
- `_validate_unique_values()`: checks `IB_IPV4` and `IB_IPV6` separately (was `IB_IP`)
- New `_load_ib_addr_mode()`: reads `ib_addr_mode` from `network_spec.yml`; returns `""` if absent

**Legacy path:** Exact 11-column header matches `LEGACY_HEADERS` -> converted to canonical -> all downstream validation uses `IB_IPV4` with the original `IB_IP` value. Empty `ib_addr_mode` -> IPv4 pairing rules apply (same as staging).

**Verdict:** SAFE. Legacy detection is exact and case-sensitive (staging also required exact headers, so no regression).

---

### 4.3 `network_spec_validator.py` — Network Spec Validation

**What changed:**
- Added `is_valid_ipv6()` helper
- Added `ib_network_from_config()`: reads `ipv4_subnet`/`ipv4_netmask_bits` first, falls back to `subnet`/`netmask_bits`
- Added `_validate_ib_ipv6_config()`: validates IPv6 subnet/netmask; requires them for `ipv6-only`/`dual-stack`; optional otherwise
- IB processing in `validate()`: reads `ib_addr_mode`, skips IPv4 validation for `ipv6-only`, runs IPv6 validation

**Legacy path:** No `ib_addr_mode` -> empty string -> not `"ipv6-only"` -> IPv4 validation runs using `ib_network_from_config()` which falls back to `subnet`/`netmask_bits` -> `_validate_ib_ipv6_config()` sees no IPv6 fields and returns without error.

**Verdict:** SAFE.

---

### 4.4 `network_spec.json` — JSON Schema

**What changed:** Single `ib_network` definition replaced with `oneOf`:
1. New format: `ipv4_subnet`/`ipv4_netmask_bits`/`ipv6_subnet`/`ipv6_netmask_bits`/`ib_addr_mode`
2. Legacy format: `subnet`/`netmask_bits` (+ optional `ib_addr_mode`)

**Legacy path:** Old `subnet`/`netmask_bits` matches the second `oneOf` branch. `ib_addr_mode` is optional in both branches.

**Verdict:** SAFE.

---

### 4.5 `orchestrator_messages.py` — Validation Messages

**What changed:**
- Header contract message: `"IB_NIC_NAME and IB_IP"` -> `"IB_NIC_NAME, IB_IPV4, and IB_IPV6"`
- Pair message: `"IB_IP"` -> `"IB_IPV4"`
- 6 new IPv6-specific messages added

**Legacy path:** Error text changes cosmetically but validation logic is unchanged. Legacy users may see `IB_IPV4` in error messages even though their CSV has `IB_IP`.

**Verdict:** SAFE (cosmetic text change only).

---

### 4.6 Network Fact Propagation (3 files)

**Files:**
- `roles/orchestrator_validations/tasks/include_software_config.yml`
- `roles/validate_preamble/tasks/main.yml`
- `playbooks/provision/provision_preamble.yml`

**What changed in all three:**

| Staging Fact | Pub Fact | Fallback |
|---|---|---|
| `ib_network_subnet` | `ib_network_ipv4_subnet` | `default(network_data.ib_network.subnet \| default(''))` |
| `ib_network_netmask_bits` | `ib_network_ipv4_netmask_bits` | `default(network_data.ib_network.netmask_bits \| default(''))` |
| *(none)* | `ib_network_ipv6_subnet` | `default('')` |
| *(none)* | `ib_network_ipv6_netmask_bits` | `default('')` |
| *(none)* | `ib_network_addr_mode` | `default('')` |

Guard conditions updated: `ib_network_netmask_bits is not defined` -> `ib_network_ipv4_netmask_bits is not defined`

**Legacy path:** Old `network_data.ib_network.netmask_bits` -> `ib_network_ipv4_netmask_bits` via fallback. All consumers updated to use new name. **No stale old-name references remain in pub.**

**Verdict:** SAFE. The fallback chain is complete and consistent.

---

### 4.7 `slurm_config/tasks/build_slurm_conf.yml` — NodeAddr for Login/Compiler Nodes

**What changed:** Login and compiler-login node entries now check for IB address maps:

```yaml
_login_entry: >-
  {{ {'NodeName': item} | combine({'NodeAddr': _pxe_ib_nodeaddr_map[item]})
     if (_pxe_ib_nodeaddr_map | default({})).get(item, '')
     else ({'NodeName': item} | combine({'NodeAddr': _ib_nodeaddr_map[item]})
           if (_ib_nodeaddr_map | default({})).get(item, '')
           else {'NodeName': item}) }}
```

**Legacy path when both maps are undefined:**

```
(_pxe_ib_nodeaddr_map | default({})).get(item, '') -> ''  (empty)
(_ib_nodeaddr_map | default({})).get(item, '') -> ''  (empty)
Result: {'NodeName': item}  (identical to staging)
```

**Verdict:** SAFE when maps are undefined (normal IPv4-only without IB injection).

---

### 4.8 `slurm_config/tasks/read_node_homogeneous.yml` — gpu_params Removed

**What changed:** `gpu_params` initialization line removed. `node_params` still includes `Gres` when defined.

**Verdict:** SAFE for IPv4 networking. No address, NodeAddr, or controller selection impact.

---

## 5. Recommendations

### 5.1 Must Fix Before Deployment

| Priority | Issue | File | Fix |
|---|---|---|---|
| **P0** | IPoIB playbook runs unconditionally; fails on missing prerequisites | `orchestrator.yml` + `configure_ib_ipv6.yml` | Add `when: _ib_ipv6_enabled \| default(false) \| bool` to the role inclusion |
| **P1** | `inject_ib_nodeaddr.yml` fails when `pxe_mapping_file_path` undefined | `confs.yml` | Add `hostvars['localhost']['pxe_mapping_file_path'] \| default('') \| length > 0` guard |
| **P1** | IB script template rendering fails when `read_mapping_file` undefined | 3x `ms-group-*.yaml.j2` | Wrap template inclusion in `{% if hostvars['localhost']['read_mapping_file'] is defined %}` |
| **P2** | K8s HA validation now mandatory; breaks existing K8s configs | `omnia_config_validator.py` | Make HA validation conditional on `enable_k8s_ha` being present |

### 5.2 Behavioral Changes to Document

| Change | Impact | Who Is Affected |
|---|---|---|
| Slurm `SlurmctldHost` uses IB address instead of hostname | Slurm controller reachable via IB only | IPv4-only deployments with IB mapping |
| Slurm `--conf-server` uses IB address | Configless slurmd contacts IB address | Same |
| Slurm `NodeAddr` set from PXE mapping | Compute/login nodes use IB for Slurm traffic | Same |
| IB config script runs on all provisioned nodes | Extra cloud-init step; exits gracefully if no Mellanox HW | All deployments |
| Error messages reference `IB_IPV4` instead of `IB_IP` | Users see new field name in validation errors | Legacy CSV users |

### 5.3 Test Matrix

| Test Case | Expected Result |
|---|---|
| Legacy 11-column CSV + old `network_spec.yml` + no `ib_addr_mode` | Full orchestrator run succeeds; IB configured via IPv4 |
| Same as above + `pxe_mapping_file_path` undefined | Orchestrator run succeeds; IB/Slurm IB injection skipped |
| Same as above + no Mellanox hardware | IB script exits gracefully; provisioning completes |
| New 12-column CSV + `ib_addr_mode: ipv4-only` | IPv4 IB configured; IPv6 skipped |
| New 12-column CSV + `ib_addr_mode: dual-stack` | Both IPv4 and IPv6 configured |
| New 12-column CSV + `ib_addr_mode: ipv6-only` | IPv4 skipped; IPv6 configured |
| K8s deployment without `enable_k8s_ha` / `virtual_ip_address` | Should not fail (needs fix) |
| Orchestrator run without IB (no `ib_network` in `network_spec.yml`) | All IB steps skipped gracefully |
