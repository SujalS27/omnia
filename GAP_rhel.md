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
