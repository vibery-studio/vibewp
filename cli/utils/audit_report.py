"""Security audit report generation with multiple output formats"""

from typing import Dict, List, Optional
from datetime import datetime
from pathlib import Path
import json

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.layout import Layout
from rich import box
from jinja2 import Environment, FileSystemLoader


class ReportGenerator:
    """Generate security audit reports in multiple formats"""

    SEVERITY_WEIGHTS = {
        'critical': 10,
        'high': 7,
        'medium': 4,
        'low': 2
    }

    SEVERITY_COLORS = {
        'critical': 'red',
        'high': 'orange1',
        'medium': 'yellow',
        'low': 'blue'
    }

    def __init__(self):
        """Initialize report generator"""
        self.console = Console()

        # Setup Jinja2 templates
        template_dir = Path(__file__).parent.parent.parent / "templates"
        self.jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))

    def generate(
        self,
        system_results: Dict,
        wordpress_results: Dict,
        output_format: str = 'console',
        output_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Generate security audit report

        Args:
            system_results: Results from SystemAuditor.audit_all()
            wordpress_results: Results from WordPressAuditor.audit_all_sites()
            output_format: Format - 'console', 'json', 'html', or 'pdf'
            output_path: File path for json/html/pdf output

        Returns:
            Path to generated file (for json/html/pdf), None for console
        """
        # Aggregate all findings
        all_findings = self._aggregate_findings(system_results, wordpress_results)

        # Calculate security score
        overall_score = self._calculate_overall_score(all_findings)

        # Group findings by severity
        findings_by_severity = self._group_by_severity(all_findings)

        # Prepare report data
        report_data = {
            'timestamp': datetime.utcnow().isoformat() + 'Z',
            'overall_score': overall_score,
            'total_findings': len(all_findings),
            'findings_by_severity': findings_by_severity,
            'severity_counts': self._count_severities(all_findings),
            'system_results': system_results,
            'wordpress_results': wordpress_results,
            'all_findings': all_findings
        }

        # Generate report in requested format
        if output_format == 'console':
            self._generate_console_report(report_data)
            return None
        elif output_format == 'json':
            return self._generate_json_report(report_data, output_path)
        elif output_format == 'html':
            return self._generate_html_report(report_data, output_path)
        elif output_format == 'pdf':
            return self._generate_pdf_report(report_data, output_path)
        else:
            raise ValueError(f"Unsupported output format: {output_format}")

    def _aggregate_findings(self, system_results: Dict, wordpress_results: Dict) -> List[Dict]:
        """Aggregate all findings from system and WordPress audits"""
        all_findings = []

        # System findings
        for category, data in system_results.items():
            if category == 'timestamp':
                continue

            if isinstance(data, dict) and 'findings' in data:
                for finding in data['findings']:
                    finding['category'] = f'System: {category.title()}'
                    all_findings.append(finding)

        # WordPress findings
        if 'sites' in wordpress_results:
            for site_name, site_data in wordpress_results['sites'].items():
                if 'findings' in site_data:
                    for finding in site_data['findings']:
                        finding['category'] = f'WordPress: {site_name}'
                        all_findings.append(finding)

        return all_findings

    def _calculate_overall_score(self, findings: List[Dict]) -> int:
        """
        Calculate overall security score (0-100)

        Args:
            findings: List of all security findings

        Returns:
            Security score from 0 to 100
        """
        if not findings:
            return 100

        # Calculate total penalty based on severity
        total_penalty = 0
        for finding in findings:
            severity = finding.get('severity', 'low')
            total_penalty += self.SEVERITY_WEIGHTS.get(severity, 2)

        # Base score of 100, subtract penalties
        # Scale: each critical = -10, high = -7, medium = -4, low = -2
        score = 100 - total_penalty

        # Clamp between 0-100
        return max(0, min(100, score))

    def _group_by_severity(self, findings: List[Dict]) -> Dict[str, List[Dict]]:
        """Group findings by severity level"""
        grouped = {
            'critical': [],
            'high': [],
            'medium': [],
            'low': []
        }

        for finding in findings:
            severity = finding.get('severity', 'low')
            if severity in grouped:
                grouped[severity].append(finding)

        return grouped

    def _count_severities(self, findings: List[Dict]) -> Dict[str, int]:
        """Count findings by severity"""
        counts = {
            'critical': 0,
            'high': 0,
            'medium': 0,
            'low': 0
        }

        for finding in findings:
            severity = finding.get('severity', 'low')
            if severity in counts:
                counts[severity] += 1

        return counts

    def _generate_console_report(self, report_data: Dict) -> None:
        """Generate and print console report using Rich"""
        self.console.print("\n")

        # Header panel
        score = report_data['overall_score']
        score_color = self._get_score_color(score)

        header = Panel(
            f"[bold white]Security Score: [{score_color}]{score}/100[/{score_color}][/bold white]\n"
            f"[dim]Total Findings: {report_data['total_findings']}[/dim]",
            title="[bold cyan]Security Audit Report[/bold cyan]",
            border_style="cyan",
            box=box.DOUBLE
        )
        self.console.print(header)

        # Severity summary
        self._print_severity_summary(report_data['severity_counts'])

        # Findings by severity
        findings_by_severity = report_data['findings_by_severity']

        for severity in ['critical', 'high', 'medium', 'low']:
            findings = findings_by_severity[severity]
            if findings:
                self._print_severity_section(severity, findings)

        # Footer
        self.console.print(
            f"\n[dim]Report generated: {report_data['timestamp']}[/dim]\n"
        )

    def _print_severity_summary(self, severity_counts: Dict[str, int]) -> None:
        """Print severity summary table"""
        table = Table(
            title="Findings by Severity",
            box=box.ROUNDED,
            show_header=True,
            header_style="bold"
        )

        table.add_column("Severity", style="bold")
        table.add_column("Count", justify="center")
        table.add_column("Status", justify="center")

        for severity in ['critical', 'high', 'medium', 'low']:
            count = severity_counts[severity]
            color = self.SEVERITY_COLORS[severity]
            status = "✓" if count == 0 else "✗"
            status_color = "green" if count == 0 else color

            table.add_row(
                f"[{color}]{severity.upper()}[/{color}]",
                f"[{color}]{count}[/{color}]",
                f"[{status_color}]{status}[/{status_color}]"
            )

        self.console.print("\n", table)

    def _print_severity_section(self, severity: str, findings: List[Dict]) -> None:
        """Print findings for a specific severity level"""
        color = self.SEVERITY_COLORS[severity]

        panel = Panel(
            self._format_findings_list(findings),
            title=f"[bold {color}]{severity.upper()} Severity ({len(findings)} findings)[/bold {color}]",
            border_style=color,
            box=box.ROUNDED
        )

        self.console.print("\n", panel)

    def _format_findings_list(self, findings: List[Dict]) -> str:
        """Format findings list for display"""
        lines = []

        for finding in findings:
            lines.append(f"[bold]{finding.get('title', 'Unknown')}[/bold]")
            lines.append(f"  ID: {finding.get('id', 'N/A')}")
            lines.append(f"  Category: {finding.get('category', 'Unknown')}")
            lines.append(f"  Description: {finding.get('description', 'N/A')}")
            lines.append(f"  Impact: {finding.get('impact', 'N/A')}")
            lines.append(f"  [cyan]Remediation:[/cyan] {finding.get('remediation', 'N/A')}")

            if finding.get('auto_fix'):
                lines.append(f"  [green]Auto-fix:[/green] {finding['auto_fix']}")

            lines.append("")  # Blank line between findings

        return "\n".join(lines)

    def _get_score_color(self, score: int) -> str:
        """Get color based on security score"""
        if score >= 90:
            return "green"
        elif score >= 70:
            return "yellow"
        elif score >= 50:
            return "orange1"
        else:
            return "red"

    def _generate_json_report(self, report_data: Dict, output_path: Optional[str]) -> str:
        """Generate JSON report file"""
        if not output_path:
            output_path = f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        # Make data JSON-serializable
        json_data = {
            'timestamp': report_data['timestamp'],
            'overall_score': report_data['overall_score'],
            'total_findings': report_data['total_findings'],
            'severity_counts': report_data['severity_counts'],
            'findings_by_severity': report_data['findings_by_severity'],
            'system_results': report_data['system_results'],
            'wordpress_results': report_data['wordpress_results']
        }

        with open(output_path, 'w') as f:
            json.dump(json_data, f, indent=2)

        return output_path

    def _generate_html_report(self, report_data: Dict, output_path: Optional[str]) -> str:
        """Generate HTML report file"""
        if not output_path:
            output_path = f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"

        # Load template
        template = self.jinja_env.get_template('audit_report.html.j2')

        # Add score color to report data
        report_data['score_color'] = self._get_score_color_html(report_data['overall_score'])

        # Render template
        html_content = template.render(**report_data)

        # Write to file
        with open(output_path, 'w') as f:
            f.write(html_content)

        return output_path

    def _get_score_color_html(self, score: int) -> str:
        """Get HTML color based on security score"""
        if score >= 90:
            return "#10b981"  # green
        elif score >= 70:
            return "#f59e0b"  # yellow
        elif score >= 50:
            return "#f97316"  # orange
        else:
            return "#ef4444"  # red

    def _generate_pdf_report(self, report_data: Dict, output_path: Optional[str]) -> str:
        """
        Generate PDF report file using reportlab

        Args:
            report_data: Report data dictionary
            output_path: Output file path

        Returns:
            Path to generated PDF file
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import letter, A4
            from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
            from reportlab.lib.units import inch
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
            from reportlab.lib.enums import TA_CENTER, TA_LEFT
        except ImportError:
            raise ImportError(
                "reportlab is required for PDF generation. "
                "Install it with: pip install reportlab"
            )

        if not output_path:
            output_path = f"security_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        # Create PDF document
        doc = SimpleDocTemplate(output_path, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=16,
            textColor=colors.HexColor('#1e40af'),
            spaceAfter=12
        )

        # Title
        story.append(Paragraph("Security Audit Report", title_style))
        story.append(Spacer(1, 0.2 * inch))

        # Score and summary
        score = report_data['overall_score']
        score_color = self._get_reportlab_color(score)

        score_data = [
            ['Security Score', f"{score}/100"],
            ['Total Findings', str(report_data['total_findings'])],
            ['Critical', str(report_data['severity_counts']['critical'])],
            ['High', str(report_data['severity_counts']['high'])],
            ['Medium', str(report_data['severity_counts']['medium'])],
            ['Low', str(report_data['severity_counts']['low'])],
        ]

        score_table = Table(score_data, colWidths=[3 * inch, 2 * inch])
        score_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e40af')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))

        story.append(score_table)
        story.append(Spacer(1, 0.3 * inch))

        # Findings by severity
        for severity in ['critical', 'high', 'medium', 'low']:
            findings = report_data['findings_by_severity'][severity]
            if not findings:
                continue

            # Severity heading
            story.append(Paragraph(
                f"{severity.upper()} Severity ({len(findings)} findings)",
                heading_style
            ))
            story.append(Spacer(1, 0.1 * inch))

            # Findings table
            for finding in findings:
                finding_data = [
                    ['ID', finding.get('id', 'N/A')],
                    ['Title', finding.get('title', 'Unknown')],
                    ['Category', finding.get('category', 'Unknown')],
                    ['Description', finding.get('description', 'N/A')],
                    ['Impact', finding.get('impact', 'N/A')],
                    ['Remediation', finding.get('remediation', 'N/A')],
                ]

                if finding.get('auto_fix'):
                    finding_data.append(['Auto-fix', finding['auto_fix']])

                finding_table = Table(finding_data, colWidths=[1.5 * inch, 5 * inch])
                finding_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#e5e7eb')),
                    ('TEXTCOLOR', (0, 0), (0, -1), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('LEFTPADDING', (0, 0), (-1, -1), 6),
                    ('RIGHTPADDING', (0, 0), (-1, -1), 6),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                ]))

                story.append(finding_table)
                story.append(Spacer(1, 0.15 * inch))

            story.append(Spacer(1, 0.2 * inch))

        # Footer
        story.append(Spacer(1, 0.3 * inch))
        footer_text = f"Report generated: {report_data['timestamp']}"
        story.append(Paragraph(footer_text, styles['Normal']))

        # Build PDF
        doc.build(story)

        return output_path

    def _get_reportlab_color(self, score: int):
        """Get reportlab color based on security score"""
        from reportlab.lib import colors

        if score >= 90:
            return colors.HexColor('#10b981')
        elif score >= 70:
            return colors.HexColor('#f59e0b')
        elif score >= 50:
            return colors.HexColor('#f97316')
        else:
            return colors.HexColor('#ef4444')
