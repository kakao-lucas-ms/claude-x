"""Security module for detecting sensitive information in code."""

import re
from typing import List, Tuple


class SecurityScanner:
    """Scans code for sensitive information patterns."""

    # Sensitive patterns to detect
    SENSITIVE_PATTERNS = [
        (r'(?i)(api[_-]?key|apikey)\s*[=:]\s*["\']?[\w-]+', "API Key"),
        (r'(?i)(secret|password|passwd|pwd)\s*[=:]\s*["\']?[\w-]+', "Secret/Password"),
        (r'(?i)(token|auth[_-]?token)\s*[=:]\s*["\']?[\w-]+', "Auth Token"),
        (r'(?i)bearer\s+[\w-]+', "Bearer Token"),
        (r'sk-[a-zA-Z0-9]{48}', "OpenAI API Key"),
        (r'ghp_[a-zA-Z0-9]{36}', "GitHub Personal Access Token"),
        (r'gho_[a-zA-Z0-9]{36}', "GitHub OAuth Token"),
        (r'github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}', "GitHub PAT"),
        (r'glpat-[a-zA-Z0-9_\-]{20,}', "GitLab Personal Access Token"),
        (r'AKIA[0-9A-Z]{16}', "AWS Access Key ID"),
        (r'(?i)aws[_-]?secret[_-]?access[_-]?key["\']?\s*[=:]\s*["\']?[a-zA-Z0-9/+=]{40}', "AWS Secret Access Key"),
        (r'mongodb(\+srv)?://[^:]+:[^@]+@', "MongoDB Connection String"),
        (r'postgres(ql)?://[^:]+:[^@]+@', "PostgreSQL Connection String"),
        (r'mysql://[^:]+:[^@]+@', "MySQL Connection String"),
        (r'-----BEGIN (RSA |DSA |EC )?PRIVATE KEY-----', "Private Key"),
    ]

    def __init__(self):
        """Initialize security scanner."""
        self.compiled_patterns = [
            (re.compile(pattern, re.MULTILINE), label)
            for pattern, label in self.SENSITIVE_PATTERNS
        ]

    def scan_code(self, code: str) -> List[Tuple[str, str]]:
        """Scan code for sensitive information.

        Args:
            code: Code content to scan

        Returns:
            List of (pattern_label, matched_value) tuples
        """
        findings = []

        for pattern, label in self.compiled_patterns:
            matches = pattern.finditer(code)
            for match in matches:
                matched_text = match.group(0)
                findings.append((label, matched_text[:50]))  # Truncate for safety

        return findings

    def has_sensitive_data(self, code: str) -> bool:
        """Quick check if code contains sensitive data.

        Args:
            code: Code content

        Returns:
            True if sensitive patterns found
        """
        return len(self.scan_code(code)) > 0

    def get_warning_message(self, findings: List[Tuple[str, str]]) -> str:
        """Generate warning message for findings.

        Args:
            findings: List of (label, matched_value) tuples

        Returns:
            Formatted warning message
        """
        if not findings:
            return ""

        lines = ["⚠️  Sensitive information detected:"]
        for label, matched_text in findings:
            lines.append(f"  - {label}: {matched_text}...")

        lines.append("\nRecommendation: Review before committing or sharing.")
        return "\n".join(lines)
