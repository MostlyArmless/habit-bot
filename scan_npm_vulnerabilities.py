#!/usr/bin/env python3
"""
NPM Vulnerability Scanner

Recursively scans repositories for compromised npm packages by analyzing:
- package-lock.json (npm)
- yarn.lock (Yarn)
- pnpm-lock.yaml (pnpm)
- npm-shrinkwrap.json (npm)
- package.json (to check if updates could pull vulnerable versions)
"""

import argparse
import csv
import json
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional
import yaml


@dataclass
class VulnerablePackage:
    """Represents a vulnerable package from the CSV."""
    name: str
    version: str

    def __hash__(self):
        return hash((self.name, self.version))


@dataclass
class Finding:
    """Represents a finding of a vulnerable package."""
    repo_path: str
    file_path: str
    package_name: str
    found_version: str
    expected_vulnerable_version: str
    file_type: str

    def __str__(self):
        return (f"[{self.file_type}] {self.repo_path}\n"
                f"  File: {self.file_path}\n"
                f"  Package: {self.package_name}@{self.found_version}\n"
                f"  Matches vulnerable version: {self.expected_vulnerable_version}\n")


class NPMVulnerabilityScanner:
    """Scanner for npm package vulnerabilities across multiple repositories."""

    def __init__(self, vulnerable_packages: List[VulnerablePackage], verbose: bool = False, pinned_only: bool = False):
        self.vulnerable_packages = vulnerable_packages
        self.vulnerable_map: Dict[str, Set[str]] = {}
        self.verbose = verbose
        self.pinned_only = pinned_only
        self._seen_findings: Set[tuple] = set()  # For deduplication

        # Build a map of package names to vulnerable versions
        for pkg in vulnerable_packages:
            if pkg.name not in self.vulnerable_map:
                self.vulnerable_map[pkg.name] = set()
            self.vulnerable_map[pkg.name].add(pkg.version)

        if self.verbose:
            print("\nVulnerable packages loaded:")
            for name, versions in sorted(self.vulnerable_map.items()):
                print(f"  {name}: {sorted(versions)}")
            print()

        self.findings: List[Finding] = []

    def scan_directory(self, root_path: Path) -> None:
        """Recursively scan a directory for repositories with npm packages."""
        print(f"Scanning directory: {root_path}")

        for dirpath, dirnames, filenames in os.walk(root_path):
            # Skip common directories that won't contain lock files
            dirnames[:] = [d for d in dirnames if d not in {
                'node_modules', '.git', '.github', 'dist', 'build',
                'coverage', '.venv', 'venv', '__pycache__'
            }]

            current_path = Path(dirpath)

            # Check for various lock files and package.json
            if 'package-lock.json' in filenames:
                if self.verbose:
                    print(f"  Examining: {current_path / 'package-lock.json'}")
                self.scan_package_lock(current_path / 'package-lock.json')

            if 'yarn.lock' in filenames:
                if self.verbose:
                    print(f"  Examining: {current_path / 'yarn.lock'}")
                self.scan_yarn_lock(current_path / 'yarn.lock')

            if 'pnpm-lock.yaml' in filenames:
                if self.verbose:
                    print(f"  Examining: {current_path / 'pnpm-lock.yaml'}")
                self.scan_pnpm_lock(current_path / 'pnpm-lock.yaml')

            if 'npm-shrinkwrap.json' in filenames:
                if self.verbose:
                    print(f"  Examining: {current_path / 'npm-shrinkwrap.json'}")
                self.scan_npm_shrinkwrap(current_path / 'npm-shrinkwrap.json')

            if 'package.json' in filenames:
                if self.verbose:
                    print(f"  Examining: {current_path / 'package.json'}")
                self.scan_package_json(current_path / 'package.json')

    def scan_package_lock(self, file_path: Path) -> None:
        """Scan package-lock.json for vulnerable packages."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Handle both lockfileVersion 1 and 2/3 formats
            if 'packages' in data:
                # Lockfile version 2 or 3
                for package_path, package_info in data.get('packages', {}).items():
                    if not package_path:  # Skip the root package
                        continue

                    # Extract package name and version
                    version = package_info.get('version')
                    name = package_info.get('name')

                    # If name is not in package info, parse from path
                    if not name:
                        # Remove 'node_modules/' prefix and handle scoped packages
                        clean_path = package_path.replace('node_modules/', '')
                        if clean_path.startswith('@'):
                            parts = clean_path.split('/')
                            if len(parts) >= 2:
                                name = f"{parts[0]}/{parts[1]}"
                        else:
                            name = clean_path.split('/')[0]

                    if name and version:
                        self.check_package(name, version, file_path, 'package-lock.json')

                    # Also check dependency versions within this package
                    # These can be exact versions or ranges
                    dependencies = package_info.get('dependencies', {})
                    for dep_name, dep_version_str in dependencies.items():
                        if dep_name in self.vulnerable_map:
                            is_exact = self.is_exact_version(dep_version_str)

                            # In pinned_only mode, only check exact versions
                            if self.pinned_only and not is_exact:
                                continue

                            if is_exact:
                                # Exact version - check directly
                                self.check_package(dep_name, dep_version_str, file_path, 'package-lock.json')
                            else:
                                # Version range - check if it could pull vulnerable versions
                                matching_vulns = []
                                for vuln_version in self.vulnerable_map[dep_name]:
                                    if self.version_range_includes(dep_version_str, vuln_version):
                                        matching_vulns.append(vuln_version)
                                        if self.verbose:
                                            print(f"      ⚠️  VULNERABLE: {name} requires {dep_name}@{dep_version_str} which could pull in {vuln_version}")

                                # Create ONE finding for all matching vulnerable versions
                                if matching_vulns:
                                    finding_key = (str(file_path), dep_name, dep_version_str)
                                    if finding_key not in self._seen_findings:
                                        self._seen_findings.add(finding_key)
                                        vuln_versions_str = ', '.join(sorted(matching_vulns))
                                        finding = Finding(
                                            repo_path=str(file_path.parent),
                                            file_path=str(file_path),
                                            package_name=dep_name,
                                            found_version=dep_version_str,
                                            expected_vulnerable_version=vuln_versions_str,
                                            file_type=f'package-lock.json (locked dependency range)'
                                        )
                                        self.findings.append(finding)

            if 'dependencies' in data:
                # Lockfile version 1
                self._scan_dependencies_recursive(data['dependencies'], file_path, 'package-lock.json')

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse {file_path}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Error scanning {file_path}: {e}", file=sys.stderr)

    def _scan_dependencies_recursive(self, dependencies: dict, file_path: Path, file_type: str) -> None:
        """Recursively scan dependencies object."""
        for name, info in dependencies.items():
            version = info.get('version', '')
            if version:
                self.check_package(name, version, file_path, file_type)

            # Recursively check nested dependencies
            if 'dependencies' in info:
                self._scan_dependencies_recursive(info['dependencies'], file_path, file_type)

    def scan_yarn_lock(self, file_path: Path) -> None:
        """Scan yarn.lock for vulnerable packages."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Parse Yarn 1.x (classic) format
            # Pattern 1: "package@^1.2.3":
            #   version "1.2.3"
            # Pattern 2: "package@^1.2.3":
            #   resolved "https://.../-/package-1.2.3.tgz"

            # Try to match entries with version field
            # Handle both scoped (@scope/package) and non-scoped packages
            pattern_v1_version = r'^"((?:@[^/\s]+/)?[^@"\s]+)@([^"]+)"[^:]*:\s*\n\s+version\s+"([^"]+)"'
            matches_v1_version = re.finditer(pattern_v1_version, content, re.MULTILINE)

            for match in matches_v1_version:
                name = match.group(1)
                version_range = match.group(2)
                resolved_version = match.group(3)
                self._check_yarn_entry(name, version_range, resolved_version, file_path)

            # Also match entries that only have resolved field (extract version from URL)
            # Format: package-1.2.3.tgz or @scope/package-1.2.3.tgz
            # Handle both scoped (@scope/package) and non-scoped packages
            pattern_v1_resolved = r'^"((?:@[^/\s]+/)?[^@"\s]+)@([^"]+)"[^:]*:\s*\n\s+resolved\s+"[^"]*?/(?:[^/]+-)?([0-9]+\.[0-9]+\.[0-9]+[^"]*?)\.tgz"'
            matches_v1_resolved = re.finditer(pattern_v1_resolved, content, re.MULTILINE)

            for match in matches_v1_resolved:
                name = match.group(1)
                version_range = match.group(2)
                resolved_version = match.group(3)
                self._check_yarn_entry(name, version_range, resolved_version, file_path)

            # Parse Yarn 2+ (Berry) format
            # Pattern: "package@npm:^1.2.3": or "@scope/package@npm:^1.2.3":
            #   version: 1.2.3
            #   dependencies:
            #     dep-name: "npm:^1.0.0"
            # Capture the full entry to also check dependencies
            # Handle both scoped (@scope/package) and non-scoped packages
            # Entry body stops at blank line or line starting without whitespace
            pattern_v2 = r'^"((?:@[^/]+/)?[^@"]+)@npm:([^"]+)":\s*\n  version:\s*([^\s]+)((?:\n  [^\n]+)*)'
            matches_v2 = re.finditer(pattern_v2, content, re.MULTILINE)

            for match in matches_v2:
                name = match.group(1)
                version_range = match.group(2)
                resolved_version = match.group(3)
                entry_body = match.group(4) if len(match.groups()) >= 4 else ''

                self._check_yarn_entry(name, version_range, resolved_version, file_path)

                # Also check dependency versions within this Yarn 2+ entry
                if entry_body:
                    # Parse dependencies in format: dep-name: "npm:^1.0.0" or dep-name: "npm:1.0.0"
                    dep_pattern = r'\s+([^:\s]+):\s*(?:"npm:([^"]+)"|npm:([^\s]+))'
                    dep_matches = re.finditer(dep_pattern, entry_body)
                    for dep_match in dep_matches:
                        dep_name = dep_match.group(1)
                        # Version can be in group 2 (quoted) or group 3 (unquoted)
                        dep_version_str = dep_match.group(2) or dep_match.group(3)

                        if dep_name in self.vulnerable_map:
                            is_exact = self.is_exact_version(dep_version_str)

                            # In pinned_only mode, only check exact versions
                            if self.pinned_only and not is_exact:
                                continue

                            if is_exact:
                                # Exact version - check directly
                                self.check_package(dep_name, dep_version_str, file_path, 'yarn.lock')
                            else:
                                # Version range - check if it could pull vulnerable versions
                                matching_vulns = []
                                for vuln_version in self.vulnerable_map[dep_name]:
                                    if self.version_range_includes(dep_version_str, vuln_version):
                                        matching_vulns.append(vuln_version)
                                        if self.verbose:
                                            print(f"      ⚠️  VULNERABLE: {name} requires {dep_name}@{dep_version_str} which could pull in {vuln_version}")

                                if matching_vulns:
                                    finding_key = (str(file_path), dep_name, dep_version_str)
                                    if finding_key not in self._seen_findings:
                                        self._seen_findings.add(finding_key)
                                        vuln_versions_str = ', '.join(sorted(matching_vulns))
                                        finding = Finding(
                                            repo_path=str(file_path.parent),
                                            file_path=str(file_path),
                                            package_name=dep_name,
                                            found_version=dep_version_str,
                                            expected_vulnerable_version=vuln_versions_str,
                                            file_type=f'yarn.lock (dependency range)'
                                        )
                                        self.findings.append(finding)

        except Exception as e:
            print(f"Warning: Error scanning {file_path}: {e}", file=sys.stderr)

    def _check_yarn_entry(self, name: str, version_range: str, resolved_version: str, file_path: Path) -> None:
        """Check a yarn.lock entry for vulnerabilities."""
        # Check the resolved (pinned) version
        self.check_package(name, resolved_version, file_path, 'yarn.lock')

        # Also check if the version range could allow vulnerable versions
        # Skip if pinned_only mode is enabled
        if not self.pinned_only and name in self.vulnerable_map:
            if self.verbose:
                print(f"    Checking {name}@{version_range} (resolved: {resolved_version}) against vulnerable versions: {self.vulnerable_map[name]}")

            matching_vulns = []
            for vuln_version in self.vulnerable_map[name]:
                includes = self.version_range_includes(version_range, vuln_version)
                if self.verbose:
                    print(f"      {version_range} includes {vuln_version}? {includes}")
                if includes:
                    matching_vulns.append(vuln_version)
                    if self.verbose:
                        print(f"      ⚠️  VULNERABLE: {name}@{version_range} could pull in {vuln_version} (currently: {resolved_version})")

            if matching_vulns:
                finding_key = (str(file_path), name, version_range)
                if finding_key not in self._seen_findings:
                    self._seen_findings.add(finding_key)
                    vuln_versions_str = ', '.join(sorted(matching_vulns))
                    finding = Finding(
                        repo_path=str(file_path.parent),
                        file_path=str(file_path),
                        package_name=name,
                        found_version=version_range,
                        expected_vulnerable_version=vuln_versions_str,
                        file_type=f'yarn.lock (version range, currently resolved to {resolved_version})'
                    )
                    self.findings.append(finding)

    def scan_pnpm_lock(self, file_path: Path) -> None:
        """Scan pnpm-lock.yaml for vulnerable packages."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if not data:
                return

            # Check packages section (pnpm v6+)
            if 'packages' in data:
                for package_key, package_info in data['packages'].items():
                    # Package key format: /package-name/1.2.3
                    # or: /@scope/package-name/1.2.3
                    match = re.match(r'^/?(@?[^/]+(?:/[^/]+)?)/([^/]+)', package_key)
                    if match:
                        name = match.group(1)
                        version = match.group(2)
                        self.check_package(name, version, file_path, 'pnpm-lock.yaml')

                        # Also check dependency versions within this package
                        if isinstance(package_info, dict):
                            dependencies = package_info.get('dependencies', {})
                            for dep_name, dep_version_str in dependencies.items():
                                if isinstance(dep_version_str, str) and dep_name in self.vulnerable_map:
                                    is_exact = self.is_exact_version(dep_version_str)

                                    # In pinned_only mode, only check exact versions
                                    if self.pinned_only and not is_exact:
                                        continue

                                    if is_exact:
                                        # Exact version - check directly
                                        self.check_package(dep_name, dep_version_str, file_path, 'pnpm-lock.yaml')
                                    else:
                                        # Version range - check if it could pull vulnerable versions
                                        matching_vulns = []
                                        for vuln_version in self.vulnerable_map[dep_name]:
                                            if self.version_range_includes(dep_version_str, vuln_version):
                                                matching_vulns.append(vuln_version)
                                                if self.verbose:
                                                    print(f"      ⚠️  VULNERABLE: {name} requires {dep_name}@{dep_version_str} which could pull in {vuln_version}")

                                        if matching_vulns:
                                            finding_key = (str(file_path), dep_name, dep_version_str)
                                            if finding_key not in self._seen_findings:
                                                self._seen_findings.add(finding_key)
                                                vuln_versions_str = ', '.join(sorted(matching_vulns))
                                                finding = Finding(
                                                    repo_path=str(file_path.parent),
                                                    file_path=str(file_path),
                                                    package_name=dep_name,
                                                    found_version=dep_version_str,
                                                    expected_vulnerable_version=vuln_versions_str,
                                                    file_type=f'pnpm-lock.yaml (locked dependency range)'
                                                )
                                                self.findings.append(finding)

            # Check dependencies section (older pnpm versions)
            if 'dependencies' in data:
                self._scan_pnpm_dependencies(data['dependencies'], file_path)

            if 'devDependencies' in data:
                self._scan_pnpm_dependencies(data['devDependencies'], file_path)

        except yaml.YAMLError as e:
            print(f"Warning: Failed to parse {file_path}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Error scanning {file_path}: {e}", file=sys.stderr)

    def _scan_pnpm_dependencies(self, dependencies: dict, file_path: Path) -> None:
        """Scan pnpm dependencies section."""
        for name, version_info in dependencies.items():
            if isinstance(version_info, str):
                # Direct version string
                version = version_info.split('(')[0].strip()  # Remove any parenthetical info
                self.check_package(name, version, file_path, 'pnpm-lock.yaml')
            elif isinstance(version_info, dict):
                # Nested dependency object
                version = version_info.get('version', '')
                if version:
                    self.check_package(name, version, file_path, 'pnpm-lock.yaml')

    def scan_npm_shrinkwrap(self, file_path: Path) -> None:
        """Scan npm-shrinkwrap.json (similar format to package-lock.json)."""
        self.scan_package_lock(file_path)  # Same format as package-lock.json

    def scan_package_json(self, file_path: Path) -> None:
        """
        Scan package.json to check if version ranges could include vulnerable versions.
        This helps identify packages that could pull in vulnerable versions on npm install/update.
        Skipped if pinned_only mode is enabled.
        """
        # Skip package.json scanning in pinned_only mode as it only contains version ranges
        if self.pinned_only:
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for dep_type in ['dependencies', 'devDependencies', 'peerDependencies', 'optionalDependencies']:
                dependencies = data.get(dep_type, {})
                for name, version_range in dependencies.items():
                    if name in self.vulnerable_map:
                        if self.verbose:
                            print(f"    Checking {name}@{version_range} against vulnerable versions: {self.vulnerable_map[name]}")

                        # Check if any vulnerable version could satisfy this range
                        matching_vulns = []
                        for vuln_version in self.vulnerable_map[name]:
                            includes = self.version_range_includes(version_range, vuln_version)
                            if self.verbose:
                                print(f"      {version_range} includes {vuln_version}? {includes}")
                            if includes:
                                matching_vulns.append(vuln_version)
                                if self.verbose:
                                    print(f"      ⚠️  VULNERABLE: {name}@{version_range} could pull in {vuln_version}")

                        if matching_vulns:
                            finding_key = (str(file_path), name, version_range, dep_type)
                            if finding_key not in self._seen_findings:
                                self._seen_findings.add(finding_key)
                                vuln_versions_str = ', '.join(sorted(matching_vulns))
                                finding = Finding(
                                    repo_path=str(file_path.parent),
                                    file_path=str(file_path),
                                    package_name=name,
                                    found_version=version_range,
                                    expected_vulnerable_version=vuln_versions_str,
                                    file_type=f'package.json ({dep_type})'
                                )
                                self.findings.append(finding)

        except json.JSONDecodeError as e:
            print(f"Warning: Failed to parse {file_path}: {e}", file=sys.stderr)
        except Exception as e:
            print(f"Warning: Error scanning {file_path}: {e}", file=sys.stderr)

    def is_exact_version(self, version_str: str) -> bool:
        """
        Check if a version string is an exact version (not a range).
        Returns True for versions like "1.0.6", "1.2.3"
        Returns False for ranges like "^1.0.0", "~1.2.3", ">=1.0.0", "*", etc.
        """
        version_str = version_str.strip()
        # Check for range indicators
        if any(version_str.startswith(prefix) for prefix in ['^', '~', '>', '<', '=', '*']):
            return False
        if '*' in version_str or 'x' in version_str.lower():
            return False
        if version_str in ['latest', 'next']:
            return False
        # Check if it looks like a version number (digits and dots)
        import re
        return bool(re.match(r'^v?\d+\.\d+\.\d+', version_str))

    def version_range_includes(self, version_range: str, specific_version: str) -> bool:
        """
        Check if a version range could include a specific version.
        This is a simplified check - for production use, consider using semver library.
        """
        # Remove leading 'v' if present
        specific_version = specific_version.lstrip('v')
        version_range = version_range.lstrip('v')

        # Handle exact versions
        if version_range == specific_version:
            return True

        # Handle common patterns
        if version_range.startswith('^'):
            # Caret range: ^1.2.3 allows >=1.2.3 <2.0.0
            base = version_range[1:]
            return self._check_caret_range(base, specific_version)

        if version_range.startswith('~'):
            # Tilde range: ~1.2.3 allows >=1.2.3 <1.3.0
            base = version_range[1:]
            return self._check_tilde_range(base, specific_version)

        if version_range.startswith('>=') or version_range.startswith('<=') or \
           version_range.startswith('>') or version_range.startswith('<'):
            # Range comparison
            return True  # Conservative: flag for manual review

        if '*' in version_range or 'x' in version_range.lower():
            # Wildcard version
            return True  # Conservative: flag for manual review

        if version_range == 'latest' or version_range == '*':
            return True

        # If we can't determine, be conservative and flag it
        return False

    def _check_caret_range(self, base: str, version: str) -> bool:
        """Check if version falls within caret range of base."""
        try:
            base_parts = [int(x) for x in base.split('.')]
            version_parts = [int(x) for x in version.split('.')]

            # Pad to same length
            while len(base_parts) < 3:
                base_parts.append(0)
            while len(version_parts) < 3:
                version_parts.append(0)

            # Major version must match
            if version_parts[0] != base_parts[0]:
                return False

            # If major is 0, minor must match
            if base_parts[0] == 0 and version_parts[1] != base_parts[1]:
                return False

            # Check if version >= base
            for i in range(3):
                if version_parts[i] > base_parts[i]:
                    return True
                if version_parts[i] < base_parts[i]:
                    return False

            return True  # Equal versions
        except:
            return True  # Conservative: flag for manual review

    def _check_tilde_range(self, base: str, version: str) -> bool:
        """Check if version falls within tilde range of base."""
        try:
            base_parts = [int(x) for x in base.split('.')]
            version_parts = [int(x) for x in version.split('.')]

            while len(base_parts) < 3:
                base_parts.append(0)
            while len(version_parts) < 3:
                version_parts.append(0)

            # Major and minor must match
            if version_parts[0] != base_parts[0] or version_parts[1] != base_parts[1]:
                return False

            # Patch must be >= base patch
            return version_parts[2] >= base_parts[2]
        except:
            return True  # Conservative: flag for manual review

    def check_package(self, name: str, version: str, file_path: Path, file_type: str) -> None:
        """Check if a package/version combination is vulnerable."""
        # Clean version string (remove 'v' prefix, remove git+https:// prefixes, etc.)
        clean_version = version.lstrip('v').split('#')[0]

        # Skip git URLs and other non-version strings
        if clean_version.startswith(('http://', 'https://', 'git://', 'git+', 'file:')):
            return

        if name in self.vulnerable_map:
            if self.verbose:
                print(f"    Checking locked package: {name}@{clean_version}")
            if clean_version in self.vulnerable_map[name]:
                if self.verbose:
                    print(f"      ⚠️  VULNERABLE: Exact match found!")
                finding = Finding(
                    repo_path=str(file_path.parent),
                    file_path=str(file_path),
                    package_name=name,
                    found_version=clean_version,
                    expected_vulnerable_version=clean_version,
                    file_type=file_type
                )
                self.findings.append(finding)

    def generate_report(self, output_file: Optional[Path] = None) -> None:
        """Generate a report of all findings."""
        if not self.findings:
            print("\n✅ No vulnerable packages found!")
            return

        print(f"\n🚨 Found {len(self.findings)} vulnerable package(s):\n")
        print("=" * 80)

        report_lines = []
        report_lines.append(f"NPM Vulnerability Scan Report")
        report_lines.append("=" * 80)
        report_lines.append(f"Total findings: {len(self.findings)}\n")

        # Group findings by repository
        findings_by_repo: Dict[str, List[Finding]] = {}
        for finding in self.findings:
            if finding.repo_path not in findings_by_repo:
                findings_by_repo[finding.repo_path] = []
            findings_by_repo[finding.repo_path].append(finding)

        for repo_path in sorted(findings_by_repo.keys()):
            findings = findings_by_repo[repo_path]
            report_lines.append(f"\nRepository: {repo_path}")
            report_lines.append(f"  Findings: {len(findings)}")

            for finding in findings:
                report_lines.append(f"    - {finding.package_name}@{finding.found_version}")
                report_lines.append(f"      File: {Path(finding.file_path).name} ({finding.file_type})")

            print(f"\nRepository: {repo_path}")
            print(f"  Findings: {len(findings)}")
            for finding in findings:
                print(f"    - {finding.package_name}@{finding.found_version}")
                print(f"      File: {Path(finding.file_path).name} ({finding.file_type})")

        print("\n" + "=" * 80)

        # Write report to file if specified
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(report_lines))
            print(f"\n📄 Report saved to: {output_file}")


def _parse_versions(version_columns: list) -> List[str]:
    """
    Parse versions from CSV columns.
    Supports:
    - Multiple versions in separate columns: ['1.0.0', '1.0.1', '1.0.2']
    - Comma-separated versions in one column: ['1.0.0, 1.0.1, 1.0.2']
    - Mix of both
    """
    versions = []
    for col in version_columns:
        col = col.strip()
        if not col:
            continue
        # Split by comma in case multiple versions are in one field
        for version in col.split(','):
            version = version.strip()
            if version:
                versions.append(version)
    return versions


def load_vulnerable_packages(csv_path: Path) -> List[VulnerablePackage]:
    """Load vulnerable packages from CSV file."""
    packages: List[VulnerablePackage] = []

    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)

            # Read first row to check if it's a header
            first_row = next(reader, None)
            if not first_row:
                return packages

            # Check if first row looks like a header (contains common header terms)
            first_row_lower = [cell.lower().strip() for cell in first_row]
            header_terms = {'package', 'name', 'version', 'package_name', 'package-name'}
            is_header = any(term in header_terms for term in first_row_lower)

            # If first row is not a header, process it as data
            if not is_header and len(first_row) >= 2:
                name = first_row[0].strip()
                # Support multiple versions: either in additional columns or comma-separated
                versions = _parse_versions(first_row[1:])
                for version in versions:
                    if name and version:
                        packages.append(VulnerablePackage(name=name, version=version))

            # Process remaining rows
            for row in reader:
                if len(row) >= 2:
                    name = row[0].strip()
                    # Support multiple versions: either in additional columns or comma-separated
                    versions = _parse_versions(row[1:])
                    for version in versions:
                        if name and version:
                            packages.append(VulnerablePackage(name=name, version=version))

        print(f"Loaded {len(packages)} vulnerable package(s) from {csv_path}")
        return packages

    except Exception as e:
        print(f"Error loading CSV file: {e}", file=sys.stderr)
        sys.exit(1)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Scan repositories for vulnerable npm packages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Scan current directory using vulnerabilities.csv
  %(prog)s vulnerabilities.csv

  # Scan specific directory with verbose logging
  %(prog)s vulnerabilities.csv --directory /path/to/repos --verbose

  # Only report exact/pinned infected versions (ignore version ranges)
  %(prog)s vulnerabilities.csv --pinned-only

  # Save report to file
  %(prog)s vulnerabilities.csv --output report.txt

CSV Format:
  The CSV file should contain package names and versions.
  Multiple versions can be specified in several ways:

  Option 1 - One version per row:
    package_name,version
    lodash,4.17.20
    axios,0.21.1

  Option 2 - Multiple versions comma-separated:
    package_name,versions
    lodash,4.17.20,4.17.21,4.17.22
    axios,"0.21.1, 0.21.2, 0.21.3"

  Option 3 - Multiple versions in separate columns:
    package_name,version1,version2,version3
    lodash,4.17.20,4.17.21,4.17.22
        """
    )

    parser.add_argument(
        'csv_file',
        type=Path,
        help='CSV file containing vulnerable packages (name, version)'
    )

    parser.add_argument(
        '--directory', '-d',
        type=Path,
        default=Path.cwd(),
        help='Root directory to scan (default: current directory)'
    )

    parser.add_argument(
        '--output', '-o',
        type=Path,
        help='Output file for the report (optional)'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose logging to show each file examined'
    )

    parser.add_argument(
        '--pinned-only',
        action='store_true',
        help='Only report exact/pinned infected versions, ignore version ranges that could pull vulnerable versions'
    )

    args = parser.parse_args()

    # Validate inputs
    if not args.csv_file.exists():
        print(f"Error: CSV file not found: {args.csv_file}", file=sys.stderr)
        sys.exit(1)

    if not args.directory.exists():
        print(f"Error: Directory not found: {args.directory}", file=sys.stderr)
        sys.exit(1)

    # Load vulnerable packages
    vulnerable_packages = load_vulnerable_packages(args.csv_file)

    if not vulnerable_packages:
        print("Error: No vulnerable packages loaded from CSV", file=sys.stderr)
        sys.exit(1)

    # Run scanner
    scanner = NPMVulnerabilityScanner(vulnerable_packages, verbose=args.verbose, pinned_only=args.pinned_only)
    scanner.scan_directory(args.directory)
    scanner.generate_report(args.output)

    # Exit with error code if vulnerabilities found
    sys.exit(1 if scanner.findings else 0)


if __name__ == '__main__':
    main()

