# Phase 5: Flatpak Packaging & Final Release

## Summary
Create production-ready Flatpak package and prepare for distribution. This phase includes manifest optimization, metadata generation, final integration testing, and release documentation. All tests run immediately after each task.

**Estimated Duration:** 2 days  
**Target Distribution:** Flatpak (multi-distro)

---

## Goals
- Optimize Flatpak manifest for production release
- Generate AppStream metadata for Software Center integration
- Conduct final integration testing across distributions
- Prepare release documentation and notes

---

## Tasks

### 1. Optimize Flatpak manifest
**Goal:** Create a minimal, secure, and portable Flatpak build configuration.

**Manifest Requirements:**
- Define required runtime dependencies:
  - Python 3 (with pip)
  - paramiko (SSH library)
  - PyQt6 (GUI framework)
  - keyring + libportal (secure credential storage)
  - cryptography (for encrypted file fallback)
- Set sandbox permissions correctly for keyring access via libportal
- Bundle application icons and metadata
- Test on:
  - Fedora 39/40
  - Ubuntu 24.04
  - Arch Linux (via Flatpak)

**Testing Requirements:**
- Build manifest completes without errors
- App launches inside Flatpak sandbox successfully
- Keyring access works via flatpak portal
- All features functional within sandbox constraints

---

### 2. Create AppStream metadata
**Goal:** Enable proper Software Center integration and discovery.

**Requirements:**
- Generate `appstream.xml` for Software Center integration
- Include category tags: "System Tools", "Utilities"
- Add screenshots (if available)
- Set correct package versioning scheme
- Provide app ID that is reverse-DNS format

**File Location:** `/flatpak/appstream.xml` or embedded in manifest

---

### 3. Final integration testing
**Goal:** Verify the complete Flatpak build works across target distributions.

**Test Checklist:**
- [ ] Install Flatpak from local build and verify functionality
- [ ] Test upgrade path from development version to release
- [ ] Verify sandbox isolation is maintained
- [ ] Confirm keyring access works correctly in production build
- [ ] Test on Fedora 39/40, Ubuntu 24.04, Arch Linux
- [ ] Verify desktop integration (app launcher icons work)

**Testing Requirements:**
- End-to-end workflow test: Set up server config → Start script → Stop script
- Verify error handling still works in production build
- Test with both keyring and encrypted file backends

---

### 4. Release documentation
**Goal:** Prepare comprehensive release notes and distribution guides.

**Required Documents:**
- **Updated README.md** with:
  - Installation instructions for all distros (Fedora, Ubuntu, Arch)
  - Flatpak-specific setup steps
  - Feature list
  - Requirements

- **Release notes / Changelog:**
  - List of changes from development to release
  - Known issues or limitations
  - Version number

- **FlatHub submission prep** (optional):
  - If uploading to FlatHub, prepare metadata files
  - Review FlatHub guidelines for requirements

---

## Milestones for Phase 5

- [ ] **Flatpak manifest optimized:** Minimal dependencies, correct sandbox permissions
- [ ] **AppStream metadata complete:** App appears in Software Centers correctly
- [ ] **Final integration testing passed:** All target distros tested successfully
- [ ] **Release documentation complete:** README and release notes published
- [ ] **Production-ready Flatpak built:** Ready for distribution

---

## Deliverables
- Optimized `/flatpak/org.ai-managers.AIModelServerManager.yml` – Production Flatpak manifest
- `/flatpak/appstream.xml` – AppStream metadata
- Final `/README.md` with installation instructions for all distros
- `/NEWS.md` or `/RELEASE_NOTES.md` – Changelog/release notes
- Tested `.flatpak` package files ready for distribution
- Optional: FlatHub submission files

---

## Release Sign-off Checklist

**Before release:**
- [ ] All tests pass (unit, integration, flatpak compatibility)
- [ ] Security audit passed in Phase 4
- [ ] Documentation complete and reviewed
- [ ] Tested on at least 3 different distributions
- [ ] Upgrade path from dev version works
- [ ] Keyring access verified working in production build

**Release actions:**
- Tag release commit/version
- Build final Flatpak package
- Publish to GitHub releases (optional)
- Upload to FlatHub (optional)
- Announce release via appropriate channels

---

## Next Steps (After Phase 5)
Project is complete and ready for distribution. Monitor user reports and continue iterative development as needed.
