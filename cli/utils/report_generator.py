"""Security audit report generation in multiple formats"""

from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json


class ReportGenerator:
    """Generate security audit reports in multiple formats"""

    def __init__(self):
        """Initialize report generator"""
        pass

    def generate(self, audit_data: Dict, format: str = 'console') -> str:
        """
        Generate report in specified format

        Args:
            audit_data: Complete audit results
            format: Output format (console, json, html, pdf)

        Returns:
            Report content as string
        """
        if format == 'json':
            return self.generate_json(audit_data)
        elif format == 'html':
            return self.generate_html(audit_data)
        elif format == 'pdf':
            # PDF requires HTML first, then conversion
            html = self.generate_html(audit_data)
            return self._html_to_pdf(html)
        else:  # console
            return self.generate_console(audit_data)

    def generate_json(self, audit_data: Dict) -> str:
        """
        Generate JSON report

        Args:
            audit_data: Audit results

        Returns:
            JSON string
        """
        return json.dumps(audit_data, indent=2, default=str)

    def generate_console(self, audit_data: Dict) -> str:
        """
        Generate console-friendly report

        Args:
            audit_data: Audit results

        Returns:
            Formatted text report
        """
        lines = []
        lines.append("=" * 80)
        lines.append("VIBEWP SECURITY AUDIT REPORT")
        lines.append("=" * 80)
        lines.append(f"Generated: {audit_data.get('timestamp', 'N/A')}")
        lines.append(f"Score: {audit_data.get('overall_score', 0)}/100")
        lines.append("")

        # System audit summary
        if 'system' in audit_data:
            lines.append("SYSTEM SECURITY")
            lines.append("-" * 80)
            system = audit_data['system']

            for category in ['ssh', 'firewall', 'fail2ban', 'ports', 'services', 'users', 'updates', 'logs', 'filesystem']:
                if category in system:
                    findings = system[category].get('findings', [])
                    if findings:
                        lines.append(f"\n{category.upper()}: {len(findings)} issue(s)")
                        for finding in findings[:5]:  # Show first 5
                            lines.append(f"  [{finding['severity'].upper()}] {finding['title']}")
            lines.append("")

        # WordPress audit summary
        if 'wordpress' in audit_data:
            lines.append("WORDPRESS SECURITY")
            lines.append("-" * 80)
            wp = audit_data['wordpress']
            sites_audited = wp.get('sites_audited', 0)
            lines.append(f"Sites audited: {sites_audited}")

            if 'sites' in wp:
                for site_name, site_data in wp['sites'].items():
                    findings = site_data.get('findings', [])
                    if findings:
                        lines.append(f"\n{site_name}: {len(findings)} issue(s)")
                        for finding in findings[:3]:  # Show first 3 per site
                            lines.append(f"  [{finding['severity'].upper()}] {finding['title']}")
            lines.append("")

        # Vulnerability scan summary
        if 'vulnerabilities' in audit_data:
            lines.append("VULNERABILITY SCAN")
            lines.append("-" * 80)
            vuln = audit_data['vulnerabilities']

            if 'error' in vuln:
                lines.append(f"Error: {vuln['error']}")
            else:
                total_vulns = vuln.get('total_vulnerabilities', 0)
                lines.append(f"Total vulnerabilities: {total_vulns}")

                if 'sites' in vuln:
                    for site_name, site_vulns in vuln['sites'].items():
                        site_total = len(site_vulns.get('findings', []))
                        if site_total > 0:
                            lines.append(f"\n{site_name}: {site_total} vulnerability(ies)")
            lines.append("")

        # Lynis summary
        if 'lynis' in audit_data:
            lines.append("LYNIS SYSTEM AUDIT")
            lines.append("-" * 80)
            lynis = audit_data['lynis']

            if 'error' in lynis:
                lines.append(f"Error: {lynis['error']}")
            elif lynis.get('available'):
                lines.append(f"Hardening index: {lynis.get('hardening_index', 'N/A')}")
                lines.append(f"Tests performed: {lynis.get('tests_performed', 0)}")
                warnings = lynis.get('warnings', 0)
                suggestions = lynis.get('suggestions', 0)
                lines.append(f"Warnings: {warnings}, Suggestions: {suggestions}")
            else:
                lines.append("Lynis not installed (optional)")
            lines.append("")

        # Critical findings
        all_findings = self._collect_all_findings(audit_data)
        critical = [f for f in all_findings if f['severity'] == 'critical']
        high = [f for f in all_findings if f['severity'] == 'high']

        if critical or high:
            lines.append("CRITICAL & HIGH PRIORITY ISSUES")
            lines.append("-" * 80)

            for finding in critical[:10]:
                lines.append(f"\n[CRITICAL] {finding['title']}")
                lines.append(f"  Description: {finding['description']}")
                lines.append(f"  Impact: {finding['impact']}")
                lines.append(f"  Fix: {finding['remediation']}")
                if finding.get('auto_fix'):
                    lines.append(f"  Auto-fix: {finding['auto_fix']}")

            for finding in high[:10]:
                lines.append(f"\n[HIGH] {finding['title']}")
                lines.append(f"  Description: {finding['description']}")
                lines.append(f"  Fix: {finding['remediation']}")

            lines.append("")

        lines.append("=" * 80)
        lines.append("END OF REPORT")
        lines.append("=" * 80)

        return "\n".join(lines)

    def generate_html(self, audit_data: Dict) -> str:
        """
        Generate HTML report

        Args:
            audit_data: Audit results

        Returns:
            HTML string
        """
        score = audit_data.get('overall_score', 0)
        score_color = self._get_score_color(score)
        timestamp = audit_data.get('timestamp', 'N/A')

        html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>VibeWP Security Audit Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: #f5f5f5;
            padding: 20px;
            line-height: 1.6;
        }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 40px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
        .header {{ text-align: center; margin-bottom: 40px; border-bottom: 3px solid #333; padding-bottom: 20px; }}
        .header h1 {{ font-size: 32px; color: #333; margin-bottom: 10px; }}
        .header .timestamp {{ color: #666; font-size: 14px; }}
        .score-badge {{
            display: inline-block;
            padding: 20px 40px;
            background: {score_color};
            color: white;
            border-radius: 8px;
            font-size: 48px;
            font-weight: bold;
            margin: 20px 0;
        }}
        .section {{ margin-bottom: 40px; }}
        .section h2 {{
            font-size: 24px;
            color: #333;
            margin-bottom: 20px;
            padding-bottom: 10px;
            border-bottom: 2px solid #e0e0e0;
        }}
        .finding {{
            margin-bottom: 20px;
            padding: 15px;
            border-left: 4px solid #ccc;
            background: #f9f9f9;
            border-radius: 4px;
        }}
        .finding.critical {{ border-left-color: #d32f2f; background: #ffebee; }}
        .finding.high {{ border-left-color: #f57c00; background: #fff3e0; }}
        .finding.medium {{ border-left-color: #fbc02d; background: #fffde7; }}
        .finding.low {{ border-left-color: #388e3c; background: #e8f5e9; }}
        .finding-header {{ font-weight: bold; margin-bottom: 8px; font-size: 16px; }}
        .severity-badge {{
            display: inline-block;
            padding: 2px 8px;
            border-radius: 3px;
            font-size: 12px;
            font-weight: bold;
            margin-right: 8px;
            text-transform: uppercase;
        }}
        .severity-critical {{ background: #d32f2f; color: white; }}
        .severity-high {{ background: #f57c00; color: white; }}
        .severity-medium {{ background: #fbc02d; color: black; }}
        .severity-low {{ background: #388e3c; color: white; }}
        .finding-description {{ color: #555; margin: 8px 0; }}
        .finding-remediation {{
            color: #333;
            margin: 8px 0;
            padding: 8px;
            background: white;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }}
        .stat-card {{
            background: #f5f5f5;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .stat-number {{ font-size: 36px; font-weight: bold; color: #333; }}
        .stat-label {{ color: #666; font-size: 14px; margin-top: 5px; }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>VibeWP Security Audit Report</h1>
            <div class="timestamp">Generated: {timestamp}</div>
            <div class="score-badge">{score}/100</div>
        </div>
"""

        # Statistics
        all_findings = self._collect_all_findings(audit_data)
        critical_count = len([f for f in all_findings if f['severity'] == 'critical'])
        high_count = len([f for f in all_findings if f['severity'] == 'high'])
        medium_count = len([f for f in all_findings if f['severity'] == 'medium'])
        low_count = len([f for f in all_findings if f['severity'] == 'low'])

        html += f"""
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number">{len(all_findings)}</div>
                <div class="stat-label">Total Findings</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" style="color: #d32f2f;">{critical_count}</div>
                <div class="stat-label">Critical</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" style="color: #f57c00;">{high_count}</div>
                <div class="stat-label">High</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" style="color: #fbc02d;">{medium_count}</div>
                <div class="stat-label">Medium</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" style="color: #388e3c;">{low_count}</div>
                <div class="stat-label">Low</div>
            </div>
        </div>
"""

        # System section
        if 'system' in audit_data:
            html += self._generate_html_section("System Security", audit_data['system'])

        # WordPress section
        if 'wordpress' in audit_data:
            html += self._generate_html_wordpress_section(audit_data['wordpress'])

        # Vulnerabilities section
        if 'vulnerabilities' in audit_data:
            html += self._generate_html_vulnerabilities_section(audit_data['vulnerabilities'])

        # Lynis section
        if 'lynis' in audit_data and audit_data['lynis'].get('available'):
            html += self._generate_html_lynis_section(audit_data['lynis'])

        html += """
        <div class="footer">
            <p>Generated by VibeWP Security Auditor</p>
            <p>For more information, visit: https://github.com/vibery-studio/vibewp</p>
        </div>
    </div>
</body>
</html>
"""
        return html

    def save_to_file(self, content: str, filepath: str, format: str = 'txt'):
        """
        Save report to file

        Args:
            content: Report content
            filepath: Output file path
            format: File format (for proper extension handling)
        """
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)

        if format == 'json':
            mode = 'w'
        elif format == 'pdf':
            mode = 'wb'
            content = content.encode('utf-8') if isinstance(content, str) else content
        else:
            mode = 'w'

        with open(path, mode) as f:
            f.write(content)

    def _collect_all_findings(self, audit_data: Dict) -> List[Dict]:
        """Collect all findings from audit data"""
        findings = []

        # System findings
        if 'system' in audit_data:
            for category_data in audit_data['system'].values():
                if isinstance(category_data, dict) and 'findings' in category_data:
                    findings.extend(category_data['findings'])

        # WordPress findings
        if 'wordpress' in audit_data:
            if 'findings' in audit_data['wordpress']:
                findings.extend(audit_data['wordpress']['findings'])
            if 'sites' in audit_data['wordpress']:
                for site_data in audit_data['wordpress']['sites'].values():
                    if 'findings' in site_data:
                        findings.extend(site_data['findings'])

        # Vulnerability findings
        if 'vulnerabilities' in audit_data:
            if 'findings' in audit_data['vulnerabilities']:
                findings.extend(audit_data['vulnerabilities']['findings'])
            if 'sites' in audit_data['vulnerabilities']:
                for site_data in audit_data['vulnerabilities']['sites'].values():
                    if 'findings' in site_data:
                        findings.extend(site_data['findings'])

        # Lynis findings
        if 'lynis' in audit_data and 'findings' in audit_data['lynis']:
            findings.extend(audit_data['lynis']['findings'])

        return findings

    def _get_score_color(self, score: int) -> str:
        """Get color for score badge"""
        if score >= 80:
            return '#388e3c'  # green
        elif score >= 60:
            return '#fbc02d'  # yellow
        elif score >= 40:
            return '#f57c00'  # orange
        else:
            return '#d32f2f'  # red

    def _generate_html_section(self, title: str, data: Dict) -> str:
        """Generate HTML section for system audits"""
        html = f'<div class="section"><h2>{title}</h2>'

        for category, category_data in data.items():
            if isinstance(category_data, dict) and 'findings' in category_data:
                findings = category_data['findings']
                if findings:
                    html += f'<h3>{category.upper()}</h3>'
                    for finding in findings:
                        html += self._generate_html_finding(finding)

        html += '</div>'
        return html

    def _generate_html_wordpress_section(self, data: Dict) -> str:
        """Generate HTML section for WordPress audits"""
        html = '<div class="section"><h2>WordPress Security</h2>'
        html += f'<p>Sites audited: {data.get("sites_audited", 0)}</p>'

        if 'sites' in data:
            for site_name, site_data in data['sites'].items():
                findings = site_data.get('findings', [])
                if findings:
                    html += f'<h3>{site_name}</h3>'
                    for finding in findings:
                        html += self._generate_html_finding(finding)

        html += '</div>'
        return html

    def _generate_html_vulnerabilities_section(self, data: Dict) -> str:
        """Generate HTML section for vulnerabilities"""
        html = '<div class="section"><h2>Vulnerability Scan</h2>'

        if 'error' in data:
            html += f'<p style="color: #d32f2f;">Error: {data["error"]}</p>'
        else:
            html += f'<p>Total vulnerabilities: {data.get("total_vulnerabilities", 0)}</p>'

            if 'sites' in data:
                for site_name, site_data in data['sites'].items():
                    findings = site_data.get('findings', [])
                    if findings:
                        html += f'<h3>{site_name}</h3>'
                        for finding in findings:
                            html += self._generate_html_finding(finding)

        html += '</div>'
        return html

    def _generate_html_lynis_section(self, data: Dict) -> str:
        """Generate HTML section for Lynis"""
        html = '<div class="section"><h2>Lynis System Audit</h2>'
        html += f'<p>Hardening index: {data.get("hardening_index", "N/A")}</p>'
        html += f'<p>Tests performed: {data.get("tests_performed", 0)}</p>'
        html += f'<p>Warnings: {data.get("warnings", 0)}, Suggestions: {data.get("suggestions", 0)}</p>'

        if 'findings' in data:
            for finding in data['findings']:
                html += self._generate_html_finding(finding)

        html += '</div>'
        return html

    def _generate_html_finding(self, finding: Dict) -> str:
        """Generate HTML for single finding"""
        severity = finding.get('severity', 'medium')
        severity_class = f'severity-{severity}'

        html = f'<div class="finding {severity}">'
        html += f'<div class="finding-header">'
        html += f'<span class="{severity_class} severity-badge">{severity}</span>'
        html += f'{finding.get("title", "Unknown Issue")}'
        html += f'</div>'

        if 'description' in finding:
            html += f'<div class="finding-description">{finding["description"]}</div>'

        if 'impact' in finding:
            html += f'<div class="finding-description"><strong>Impact:</strong> {finding["impact"]}</div>'

        if 'remediation' in finding:
            html += f'<div class="finding-remediation"><strong>Fix:</strong> {finding["remediation"]}</div>'

        if finding.get('auto_fix'):
            html += f'<div class="finding-remediation"><strong>Auto-fix:</strong> {finding["auto_fix"]}</div>'

        html += '</div>'
        return html

    def _html_to_pdf(self, html: str) -> bytes:
        """
        Convert HTML to PDF (requires additional library)

        Args:
            html: HTML content

        Returns:
            PDF bytes

        Note:
            This is a placeholder. In production, use:
            - weasyprint
            - pdfkit
            - or similar HTML-to-PDF library
        """
        try:
            # Try weasyprint first (most reliable)
            from weasyprint import HTML
            return HTML(string=html).write_pdf()
        except ImportError:
            # Fallback: Return HTML with note
            error_note = "<!-- PDF generation requires 'weasyprint' package: pip install weasyprint -->"
            return (error_note + html).encode('utf-8')
