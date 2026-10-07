  # Final Corrected Gap Analysis — sujal_rhel10.2 vs 2.2 (Multi-Domain Architecture)

   **Baseline:** `/root/sujal_10.2/omnia` (branch: `sujal_rhel10.2`)
   **Compared against:** `/root/omnia_2.2_test/omnia-containers` (branch: `automation-v2.2.0.0`)
   **Excludes:** Upgrade (155 tests) and Rollback (18 tests) — not required

   ---

   ## Key Architectural Change: 2.2 Monolith → 2.3 Multi-Domain

   In 2.2, all 977 tests lived in one `molecule/` tree. In 2.3, tests are distributed across **8 domain test suites**:

   | 2.3 Domain | Test Location | Tests | Scope |
   |------------|--------------|------:|-------|
   | Orchestrator | `test/orchestrator/` | 375 | Node provisioning, PXE, Slurm, K8s, storage, cloud-init, DNS, cleanup |
   | Discovery | `test/discovery/` | 85 | BMC discovery, PXE mapping, OME inventory |
   | Build Stream | `test/build_stream/` | 174 | Pipeline lifecycle, GitLab, catalog, deploy triggers |
   | Telemetry | `test/telemetry/` | 157 | Vector, Kafka, VictoriaMetrics/Logs, iDRAC, LDMS, PowerScale, UFM, VAST sources |
   | Image Build Manager | `test/image_build_manager/` | 150 | Image/catalog generation, S3/registry, multi-arch builds |
   | Repo Manager | `test/repo_manager/` | 131 | Pulp, repository sync, catalog, user registry |
   | Utils | `test/utils/` | 98 | Setup, install OS/ISO, log collection, Slurm config util |
   | Main | `test/main/` | 95 | omnia.sh/CLI, domain init, diagnostics, lifecycle |

   **GRAND TOTAL 2.3: 1,265 test functions**
   **GRAND TOTAL 2.2: 977 test functions**

   ---

   ## Corrected Mapping: Where 2.2 Tests Actually Went

   Many tests previously marked "MISSING" from orchestrator were **relocated to their correct 2.3 domain**, not deleted.

   ### 2.2 `molecule/provision/` (97 tests) → Multi-Domain Split

   | 2.2 Provision Area | Tests | 2.3 Owner | 2.3 Coverage | Status |
   |--------------------|------:|-----------|-------------|--------|
   | test_cloudinit (1) | 1 | Orchestrator | `test_node_cloud_init` | EQUIVALENT (split into ping/SSH/cloud-init) |
   | test_ssh (4) | 4 | Orchestrator | `test_node_ssh`, `test_node_hostname_ssh` | EQUIVALENT (2 of 4; "from core" context removed) |
   | test_coredns (20) | 20 | Orchestrator | `coredns_coredhcp/` 9 tests | PARTIAL (core 9 covered; 11 edge-case DNS missing) |
   | test_slurm (14) | 14 | Orchestrator | `slurm_cluster/`, `slurm_ldap/`, `slurm_openmpi/`, `slurm_ucx/` | EQUIVALENT (13 of 14; PAM session termination missing) |
   | test_k8s (6) | 6 | Orchestrator + Telemetry | `kubernetes_cluster/`, `kubernetes_storage/` + `test/telemetry/` | EQUIVALENT (split across domains)|
   | test_minimal_os (19) | 19 | Orchestrator | `minimal_os/` 8 tests | PARTIAL (8 of 19; see detail below) |
   | test_provision_output (2) | 2 | Orchestrator | `test_metadata_service_groups`, `test_boot_service_configurations` | EQUIVALENT (refactored from file-based to API-based) |
   | test_kernel_version_override (7) | 7 | Image Build + Orchestrator | `test_boot_image_identity` partial | PARTIAL (contract checks exist, override-specific absent) |
   | test_packages (8) | 8 | Image Build + Build Stream + Repo Manager | Image verification + pipeline stages + Pulp | SPLIT (artifact-side covered; live-node per-FG absent) |
   | test_vector_telemetry (15) | 15 | Telemetry | `test/telemetry/fvt/deploy/` (157 tests) | EQUIVALENT (moved to telemetry domain, greatly expanded) |
   | test_multi_subnet (1) | 1 | Orchestrator | `test_coredhcp_multisubnet_running_image` | PARTIAL (image/config check only, explicit cross-subnet SSH missing) |

   ### 2.2 `molecule/telemetry/` (177 tests) → `test/telemetry/` (157 tests)

   | Status | Detail |
   |--------|--------|
   | COVERED | Entire telemetry domain relocated to `test/telemetry/` with 157 tests covering all sources (iDRAC, LDMS, OME, PowerScale, UFM, VAST), sinks (Kafka, VictoriaMetrics, VictoriaLogs), and resilience/reboot/poweroff scenarios |

   ### 2.2 `molecule/build_stream/` (67 tests) → `test/build_stream/` (174 tests)

   | Status | Detail |
   |--------|--------|
   | EXCEEDED | 67 → 174 tests. Includes auto/manual pipelines, cadence, deploy, cleanup, retention, security, resilience, API auth |

   ### 2.2 `molecule/local_repo/` (26 tests) → `test/repo_manager/` (131 tests)

   | Status | Detail |
   |--------|--------|
   | EXCEEDED | 26 → 131 tests. Pulp, catalog, sync, user registry, policies, security, negative validation |

   ### 2.2 `molecule/build_image_*` + `install_os_arm_node` (26 tests) → `test/image_build_manager/` (150 tests)

   | Status | Detail |
   |--------|--------|
   | EXCEEDED | 26 → 150 tests. Catalog reuse, S3 layout, registry, image verification, FG packages, arch selection |

   ### 2.2 `molecule/omnia_sh_*` (12 tests) → `test/main/` (95 tests)

   | Status | Detail |
   |--------|--------|
   | EXCEEDED | 12 → 95 tests. CLI, diagnostics, domain init, setup, permissions, idempotency |

   ### 2.2 `molecule/oim_cleanup/` (9 tests) → `test/main/` + `test/orchestrator/cleanup/`

   | Status | Detail |
   |--------|--------|
   | COVERED | Orchestrator cleanup has 7 tests; Main covers broader OIM lifecycle cleanup |

   ### 2.2 `molecule/gitlab_*` (23 tests) → `test/build_stream/` (included in 174)

   | Status | Detail |
   |--------|--------|
   | COVERED | GitLab install/cleanup folded into build_stream infrastructure lifecycle tests |

   ### 2.2 `molecule/one_shot_log_extraction/` (12 tests) → `test/utils/` (98 tests)

   | Status | Detail |
   |--------|--------|
   | EXCEEDED | 12 → 98 tests. Log collection, backup, install OS/ISO, setup, Slurm config util |

   ### 2.2 `molecule/discovery/` (9 tests) → `test/discovery/` (85 tests)

   | Status | Detail |
   |--------|--------|
   | EXCEEDED | 9 → 85 tests. Schema validation, config validation, OME inventory, PXE mapping, credentials, cleanup, idempotency, performance |

   ---

   ## Orchestrator-Only Summary Table (Corrected)

   | Orchestrator Area | 2.2 | 2.3 | Status | Gap |
   |-------------------|-----|-----|--------|-----|
   | Precheck (environment/storage/deps) | 15 | 8 | Covered | NONE |
   | Precheck Storage Config Validation | 0 | 5 | NEW in 2.3 | — |
   | Precheck OIM Readiness | 6 | 17 | EXCEEDED | NONE |
   | Prepare (OpenCHAMI/network/OpenLDAP) | 19 | 14 | Covered | NONE |
   | Provision — desired state (SMD/BSS) | 10 | 10 | Covered | NONE |
   | Provision — boot image identity | 0 | 2 | NEW in 2.3 | — |
   | Connectivity + Cloud-init + Arch + OS | 6 | 5 | Covered | NONE |
   | Minimal OS (post-boot validation) | 19 | 8 | PARTIAL | MODERATE |
   | Mount Config (NFS + PV + all paths) | 27 | 17 | Covered | NONE |
   | Slurm Cluster (membership/services) | 32 | 9 | Covered | NONE |
   | Slurm Jobs (root) | 12 | 7 | Covered | NONE |
   | Slurm LDAP Auth + Jobs + PAM | 14 | 15 | EXCEEDED | NONE |
   | Slurm OpenMPI | 2 | 2 | Covered | NONE |
   | Slurm Recovery (reboot) | 14 | 1* | Covered | NONE |
   | Slurm GPU | 3 | 3 | Covered | NONE |
   | DCGM (daemon/CUDA/NFS/version/neg) | 15 | 18 | EXCEEDED | NONE |
   | InfiniBand | 8 | 2 | Covered | NONE |
   | UCX | 1 | 1 | Covered | NONE |
   | Slurm Lifecycle (add/remove node) | 2 | 2 | Covered | NONE |
   | VAST Storage | 17 | 17 | Covered | NONE |
   | PowerVault | 29 | 30 | EXCEEDED | NONE |
   | CoreDNS/CoreDHCP | 20 | 9 | PARTIAL | LOW |
   | Kubernetes (cluster/etcd/storage/recv) | 59 | 18 | Mostly covered | LOW |
   | Apptainer | 30 | 32 | EXCEEDED | NONE |
   | HPC Benchmarks | 19 | 19 | Covered | NONE |
   | Additional Cloud-Init | 42 | 25 | PARTIAL | MODERATE |
   | Cleanup (orchestrator) | 9 | 7 | Mostly covered | LOW |
   | NFT (new in 2.3) | 0 | 14 | NEW | — |
   | UT Contracts (new in 2.3) | 0 | 82 | NEW | — |

   \* 1 comprehensive 6-phase mega-test = equivalent to 2.2's 14 granular tests

   ---

   ## Remaining Gaps — Orchestrator Only

   ### Priority 1: Minimal OS — Missing Coverage (MODERATE)

   **2.2 Tests:** 19 | **2.3 Tests:** 8 | **Gap:** 11 tests

   | 2.2 Test | What It Validates | 2.3 Status |
   |----------|-------------------|------------|
   | `test_base_packages` | Required base packages installed | `test_minimal_os_base_packages` — COVERED |
   | `test_ldms_packages` | LDMS packages/binary installed | `test_minimal_os_ldms_packages` — COVERED |
   | `test_excluded_packages` | Workload packages absent | `test_minimal_os_excluded_packages` — COVERED |
   | `test_network_identity` | Hostname/IP match | `test_minimal_os_network_identity` — COVERED |
   | `test_handoff_services` | Required services running | `test_minimal_os_required_services` — COVERED |
   | `test_package_manager` | dnf/yum functional | `test_minimal_os_package_manager` — COVERED |
   | `test_architecture_x86_64` | Live arch matches FG | `test_node_architecture` in connectivity/ — COVERED (renamed) |
   | `test_architecture_aarch64` | Live arch matches FG | `test_node_architecture` in connectivity/ — COVERED (renamed) |
   | `test_functional_group_schema` | FG definitions valid | MISSING — no runtime FG schema FVT |
   | `test_additional_packages` | Configured extra packages installed | MISSING — Image Build validates definitions, no live-node check |
   | `test_additional_packages_fallback` | Absent config handled correctly | MISSING |
   | `test_ssh_access` | Root SSH + authorized key exists | PARTIAL — SSH tested, key content not verified |
   | `test_ssh_key_access` | Key authentication proven | PARTIAL — SSH works, but no key-content assertion |
   | `test_ldms_service_state` | LDMS installed but inactive at handoff | MISSING FVT — **helper exists** (`check_minimal_os_ldms_service_state`), justneeds test wrapper |
   | `test_architecture_mismatch_detection` | Arch mismatch detected | PARTIAL — validation exists, no negative injection test |
   | `test_missing_image_detection` | Missing image detected | PARTIAL — `test_boot_image_identity` fails on missing; 2.2 test was weak |
   | `test_invalid_packages_handling` | Invalid packages rejected | MISSING — 2.2 test was non-asserting |
   | `test_network_isolation` | Default route on management network | MISSING |
   | `test_no_embedded_credentials` | No plaintext secrets in image | MISSING — NFT has credential permission checks, no image scan |

   **Genuinely missing (requires new code):** ~6 tests
   **Helper exists, needs FVT wrapper:** 1 test (LDMS service state)
   **Weak/non-asserting in 2.2 (low priority):** 3 tests
   **Already covered under different name:** 2 tests (architecture)

   ### Priority 2: Additional Cloud-Init — Idempotency/Compat (MODERATE)

   **2.2 Tests:** 42 | **2.3 Tests:** 4 FVT + 21 UT = 25 | **Gap:** ~17 tests

   **Present in 2.3:**
   - 4 FVT: SMD groups, metadata groups, write_files, runcmd
   - 21 UT: validation, errors, prohibited keys, multi-error (covers all 15 negative tests from 2.2)

   **Missing from 2.3 (all orchestrator domain):**

   | Missing Test | Category |
   |-------------|----------|
   | `test_smd_group_idempotency` | Idempotency |
   | `test_bss_registration_idempotency` | Idempotency |
   | `test_full_pipeline_idempotency` | Idempotency |
   | `test_common_template_rendering` | Template/BSS |
   | `test_per_fg_template_rendering` | Template/BSS |
   | `test_conditional_rendering` | Template/BSS |
   | `test_bss_common_registration` | Template/BSS |
   | `test_bss_per_fg_registration` | Template/BSS |
   | `test_merge_behavior` | Template/BSS |
   | `test_rhel_compatibility` | Compatibility |
   | `test_multiple_fgs_compatibility` | Compatibility |
   | `test_upgrade_mode_compatibility` | Compatibility |
   | `test_end_to_end_common_only` | Node verification |
   | `test_end_to_end_per_fg_only` | Node verification |
   | `test_end_to_end_combined` | Node verification |
   | `test_end_to_end_multiple_fgs` | Node verification |
   | `test_end_to_end_mixed_directives` | Node verification |

   ### Priority 3: CoreDNS Edge Cases (LOW)

   **2.2 Tests:** 20 | **2.3 Tests:** 9 | **Gap:** ~11 tests

   **Covered in 2.3 (9):**
   - Container state (enabled/disabled), forward resolution, reverse resolution, multi-subnet image, idempotency, compute resolv.conf, compute getent, n
   ode addition pipeline, SMD unreachable cached resolution

   **Missing edge cases:**
   - Slurm-specific DNS resolution
   - K8s CoreDNS HPC-domain forwarding
   - DNS query latency/performance
   - SMD TLS communication
   - Invalid domain format rejection
   - PXE hostname NID format
   - Compute /etc/hosts peer entries

   ### Priority 4: Kubernetes Granularity (LOW)

   **2.2 Tests:** 59 | **2.3 Tests:** 18 | **Gap:** ~8-10 tests

   Core coverage present. Missing:
   - BOSS card detection / etcd local disk partition checks
   - NFS telemetry PVC bound checks
   - K8s reboot recovery (4 tests in 2.2)
   - Etcd reboot recovery (7 tests in 2.2)

   ### Priority 5: Cleanup Firewall/Chronyd (LOW)

   **Missing:** 2 tests (firewall ports, chronyd cleanup)
   **Note:** These map to **main** domain in 2.3, not orchestrator

   ### Priority 6: Slurm — PAM Session Termination (LOW)

   **Missing:** 1 test (`test_pam_slurm_adopt_session_termination`)

   ---

   ## Cross-Domain Gaps (Not Orchestrator)

   These were previously counted as "orchestrator gaps" but belong to other 2.3 domains:

   | Gap | Correct 2.3 Owner | Tests | Status |
   |-----|-------------------|------:|--------|
   | Vector telemetry (15 tests) | Telemetry | 15 | COVERED — telemetry has 157 tests |
   | Kernel override S3/BSS (7 tests) | Image Build + Orchestrator | 7 | PARTIAL — contract checks exist, override-specific absent |
   | Per-FG live package verification (4 tests) | Image Build + Orchestrator | 4 | PARTIAL — artifact-side covered, live-node absent |
   | Repo SSL/sync policy (2 tests) | Repo Manager | 2 | COVERED — repo_manager has 131 tests |
   | Build stream job stage (1 test) | Build Stream | 1 | COVERED — build_stream has 174 tests |
   | OIM cleanup (9 tests) | Main | 9 | COVERED — main has 95 tests |

   ---

   ## Areas With Zero Gap (No Action Required)

   | Area | Why No Gap |
   |------|------------|
   | Precheck | 30 tests (8 FVT + 17 OIM readiness + 5 storage validation) |
   | Mount Config | 12 FVT tests cover both NFS and PowerVault paths |
   | Slurm Cluster | 9 tests cover membership, services, SSH, config |
   | Slurm Jobs | 7 root job tests |
   | Slurm LDAP | 15 tests EXCEED 2.2's 14 |
   | Slurm OpenMPI | 2 tests match 2.2 |
   | Slurm Recovery | 1 mega-test covers all 14 scenarios from 2.2 |
   | Slurm GPU | 3 tests match 2.2 |
   | DCGM | 18 tests EXCEED 2.2's 15 |
   | InfiniBand | 2 tests cover config + connectivity |
   | UCX | 1 test matches 2.2 |
   | Slurm Lifecycle | 2 tests (add/remove node) |
   | VAST Storage | 17 tests match 2.2 (implemented this session) |
   | PowerVault | 30 tests EXCEED 2.2's 29 |
   | Apptainer | 32 tests EXCEED 2.2's 30 |
   | HPC Benchmarks | 19 tests match 2.2 |
   | Discovery | 85 tests FAR EXCEED 2.2's 9 |
   | Telemetry | 157 tests cover 2.2's 177 (domain restructured) |
   | Build Stream | 174 tests EXCEED 2.2's 67 |
   | Repo Manager | 131 tests EXCEED 2.2's 26 |
   | Image Build | 150 tests EXCEED 2.2's 26 |
   | Main | 95 tests EXCEED 2.2's 12 |
   | Utils | 98 tests EXCEED 2.2's 12 |

   ---

   ## Priority Action List (Orchestrator Only)

   | Pri | Gap | Missing | Severity | Action |
   |-----|-----|---------|----------|--------|
   | 1 | Minimal OS remaining coverage | ~6 new + 1 wrapper | MODERATE | Add LDMS state wrapper, additional packages, network isolation, credential scan|
   | 2 | Additional cloud-init idempotency/compat/template | ~17 | MODERATE | Add idempotency, template rendering, BSS registration, compatibility, e2enode verification tests |
   | 3 | CoreDNS edge cases | ~7 | LOW | Add Slurm DNS, K8s forwarding, latency, NID format, /etc/hosts |
   | 4 | Kubernetes reboot/etcd granularity | ~8-10 | LOW | Add K8s/etcd reboot recovery, BOSS card, NFS PVC checks |
   | 5 | Slurm PAM session termination | 1 | LOW | Add PAM adopt session termination test |

   **TOTAL REMAINING ORCHESTRATOR GAPS: ~40-42 tests**

   ---

   ## Cross-Domain Action Items

   | Pri | Gap | Owner | Missing | Action |
   |-----|-----|-------|---------|--------|
   | 1 | Kernel override end-to-end | Image Build + Orchestrator | ~5 | Image Build validates selected kernel in build_status.yml; Orchestrator validates BSS + live nodes match contract |
   | 2 | Live per-FG package verification | Orchestrator (consuming Image Build contract) | ~4 | New orchestrator suite: positive/negative per-FG package checks on provisioned nodes |

   ---

   ## Corrected Totals

   | Metric | Previous Analysis | Corrected |
   |--------|------------------|-----------|
   | Orchestrator remaining gaps | ~67-71 | ~40-42 |
   | "COMPLETELY ABSENT" areas | 4 | 0 |
   | Areas incorrectly marked missing | mount_config NFS, VAST, Vector telemetry, repo/build_stream tests | All relocated to correct domains |
   | Total 2.3 test functions | 460 (orchestrator + discovery only) | **1,265** (all 8 domains) |
   | Total 2.2 test functions | 977 | 977 |
   | Net change | -517 | **+288 (29% increase)** |

 
