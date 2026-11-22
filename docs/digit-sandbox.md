# Local DIGIT sandbox

The pilot targets DIGIT 2.9 LTS and the Citizen Complaint Resolution System. The workbench's built-in fixture remains available while the Linux container runtime is set up.

## Check laptop readiness

From the workbench repository in PowerShell:

```powershell
.\scripts\Test-DigitSandbox.ps1
```

The upstream [CRS local setup](https://github.com/egovernments/Citizen-Complaint-Resolution-System/tree/master/local-setup) documents a Docker Compose stack for API and smoke testing and recommends 8 GB allocated to Docker. For a Windows laptop using WSL 2, [Microsoft's WSL setup](https://learn.microsoft.com/en-us/windows/wsl/install) requires an administrator PowerShell and a restart. [Docker's Windows setup](https://docs.docker.com/desktop/setup/install/windows-install/) covers the Linux container engine.

## Pin and verify the baseline

1. Fetch the upstream CRS repository locally. Record the exact CRS commit, the Compose file used, each resolved image digest, the core release, and the seeded tenant. The upstream [DIGIT Core release history](https://github.com/egovernments/Digit-Core/releases) identifies the 2.9 LTS line. Compare the actual Compose images with the [published 2.9 builds](https://docs.digit.org/local-governance/urban/release-notes/mdms-configuration-and-service-build-updates) before labeling the sandbox 2.9 LTS. The upstream default branch is a separate moving baseline.
2. Boot the pinned Compose stack and confirm the upstream health checks. Open the employee and citizen screens and capture a baseline complaint submission and resolution.
3. Export the synthetic tenant's effective complaint subtype master data and localization records. Determine the exact schema and localization convention used by the running PGR build before mapping the workbench change.
4. Apply the missed-pickup change to that sandbox. Verify the new option and label in the citizen UI, submit the complaint, check that employees can see and act on it, and confirm that the baseline complaint subtype remains available.

Only record a live sandbox pass after those checks run against the real deployment.
