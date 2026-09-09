"""Report generation for evaluation results.

Produces JSON and HTML reports with metrics, per-question breakdown, and visualizations.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

from evaluation.metrics.quality_gate import format_gate_result


def save_json_report(
    evaluation_report: dict,
    gate_result: dict,
    output_path: str,
) -> str:
    """Save evaluation results as JSON.
    
    Args:
        evaluation_report: Report from evaluate_dataset()
        gate_result: Result from apply_quality_gate()
        output_path: Where to save JSON file
    
    Returns:
        Path to saved file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    report = {
        "evaluation": evaluation_report,
        "quality_gate": gate_result,
        "timestamp": datetime.now().isoformat(),
    }
    
    with open(output_file, "w") as f:
        json.dump(report, f, indent=2)
    
    return str(output_file)


def generate_html_report(
    evaluation_report: dict,
    gate_result: dict,
    output_path: str,
) -> str:
    """Generate interactive HTML report.
    
    Args:
        evaluation_report: Report from evaluate_dataset()
        gate_result: Result from apply_quality_gate()
        output_path: Where to save HTML file
    
    Returns:
        Path to saved file
    """
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)
    
    # Extract data for report
    overall_stats = evaluation_report.get("overall_stats", {})
    metrics = evaluation_report.get("metrics", {})
    gate_status = gate_result.get("gate_status", "UNKNOWN")
    metric_details = gate_result.get("metric_details", {})
    per_question_results = evaluation_report.get("per_question_results", [])
    
    # Generate HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>RAG Evaluation Report</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ 
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            background: #f5f5f5;
            color: #333;
            line-height: 1.6;
        }}
        .container {{ max-width: 1400px; margin: 0 auto; padding: 20px; }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 8px;
            margin-bottom: 30px;
        }}
        .header h1 {{ font-size: 2.5em; margin-bottom: 10px; }}
        .header .timestamp {{ font-size: 0.9em; opacity: 0.9; }}
        .status-card {{
            padding: 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            text-align: center;
        }}
        .status-pass {{
            background: #d4edda;
            border: 2px solid #28a745;
            color: #155724;
        }}
        .status-fail {{
            background: #f8d7da;
            border: 2px solid #dc3545;
            color: #721c24;
        }}
        .status-badge {{
            font-size: 2em;
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .metrics-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .metric-card {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            border-left: 4px solid #667eea;
        }}
        .metric-card.pass {{ border-left-color: #28a745; }}
        .metric-card.fail {{ border-left-color: #dc3545; }}
        .metric-name {{ font-weight: bold; margin-bottom: 10px; }}
        .metric-value {{ 
            font-size: 1.8em; 
            font-weight: bold;
            margin-bottom: 10px;
        }}
        .metric-threshold {{ 
            font-size: 0.9em; 
            color: #666;
        }}
        .metric-status {{
            display: inline-block;
            padding: 5px 10px;
            border-radius: 4px;
            font-size: 0.85em;
            font-weight: bold;
        }}
        .metric-status.pass {{
            background: #d4edda;
            color: #155724;
        }}
        .metric-status.fail {{
            background: #f8d7da;
            color: #721c24;
        }}
        .summary-stats {{
            background: white;
            padding: 20px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }}
        .stats-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 20px;
        }}
        .stat-box {{
            text-align: center;
            padding: 15px;
            background: #f8f9fa;
            border-radius: 4px;
        }}
        .stat-value {{ font-size: 1.8em; font-weight: bold; color: #667eea; }}
        .stat-label {{ font-size: 0.9em; color: #666; margin-top: 5px; }}
        .questions-table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            margin-top: 20px;
            border-radius: 8px;
            overflow: hidden;
        }}
        .questions-table th {{
            background: #667eea;
            color: white;
            padding: 15px;
            text-align: left;
            font-weight: bold;
        }}
        .questions-table td {{
            padding: 12px 15px;
            border-bottom: 1px solid #eee;
        }}
        .questions-table tr:hover {{ background: #f8f9fa; }}
        .status-badge-pass {{ color: #28a745; font-weight: bold; }}
        .status-badge-fail {{ color: #dc3545; font-weight: bold; }}
        .metric-score {{
            display: inline-block;
            padding: 3px 8px;
            border-radius: 3px;
            font-size: 0.85em;
            margin: 2px;
        }}
        .metric-score.good {{ background: #d4edda; color: #155724; }}
        .metric-score.bad {{ background: #f8d7da; color: #721c24; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1> RAG Quality Gate Evaluation Report</h1>
            <div class="timestamp">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC</div>
        </div>
        
        <div class="status-card status-{'pass' if gate_status == 'PASS' else 'fail'}">
            <div class="status-badge">{' PASS' if gate_status == 'PASS' else ' FAIL'}</div>
            <div>Quality Gate Status</div>
        </div>
        
        <div class="summary-stats">
            <h2 style="margin-bottom: 20px;">Overview</h2>
            <div class="stats-row">
                <div class="stat-box">
                    <div class="stat-value">{overall_stats.get('total_questions', 0)}</div>
                    <div class="stat-label">Total Questions</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{overall_stats.get('passed_questions', 0)}</div>
                    <div class="stat-label">Passed</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{overall_stats.get('failed_questions', 0)}</div>
                    <div class="stat-label">Failed</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value">{(overall_stats.get('passed_questions', 0) / max(overall_stats.get('total_questions', 1), 1) * 100):.1f}%</div>
                    <div class="stat-label">Pass Rate</div>
                </div>
            </div>
        </div>
        
        <h2 style="margin: 30px 0 20px 0;">Metric Scores</h2>
        <div class="metrics-grid">
"""
    
    # Add metric cards
    for metric_name, detail in metric_details.items():
        status = detail.get("status", "UNKNOWN").lower()
        score = detail.get("score")
        threshold = detail.get("threshold")
        
        if score is not None:
            score_str = f"{score:.3f}"
        else:
            score_str = "N/A"
        
        html_content += f"""
            <div class="metric-card {status}">
                <div class="metric-name">{metric_name.replace('_', ' ').title()}</div>
                <div class="metric-value">{score_str}</div>
                <div class="metric-threshold">Threshold: {threshold:.2f}</div>
                <span class="metric-status {status}">{status.upper()}</span>
            </div>
"""
    
    html_content += """
        </div>
        
        <h2 style="margin: 30px 0 20px 0;">Per-Question Results</h2>
        <table class="questions-table">
            <thead>
                <tr>
                    <th>ID</th>
                    <th>Question</th>
                    <th>Status</th>
                    <th>Key Metrics</th>
                </tr>
            </thead>
            <tbody>
"""
    
    # Add per-question rows
    for result in per_question_results:
        q_id = result.get("q_id", "?")
        question = result.get("question", "")[:80]
        status = result.get("overall_question_status", "?")
        
        # Show top 3 metrics
        top_metrics = []
        for name, score in sorted(result.get("metrics", {}).items())[:3]:
            metric_status = "good" if score >= 0.75 else "bad"
            top_metrics.append(f'<span class="metric-score {metric_status}">{name[:10]}: {score:.2f}</span>')
        
        html_content += f"""
                <tr>
                    <td><strong>{q_id}</strong></td>
                    <td>{question}...</td>
                    <td><span class="status-badge-{status.lower()}">{status}</span></td>
                    <td>{' '.join(top_metrics)}</td>
                </tr>
"""
    
    html_content += """
            </tbody>
        </table>
    </div>
</body>
</html>
"""
    
    with open(output_path, "w") as f:
        f.write(html_content)
    # Return the path to the generated HTML report
    return str(output_path)


def print_report_summary(
    evaluation_report: dict,
    gate_result: dict,
) -> None:
    """Print human-readable report summary to console.
    
    Args:
        evaluation_report: Report from evaluate_dataset()
        gate_result: Result from apply_quality_gate()
    """
    print(format_gate_result(gate_result))
    
    stats = evaluation_report.get("overall_stats", {})
    print(f"Questions Evaluated: {stats.get('total_questions', 0)}")
    print(f"  Passed: {stats.get('passed_questions', 0)}")
    print(f"  Failed: {stats.get('failed_questions', 0)}")
    
    if stats.get("total_questions", 0) > 0:
        pass_rate = (
            stats.get("passed_questions", 0) / stats.get("total_questions", 1) * 100
        )
        print(f"  Pass Rate: {pass_rate:.1f}%")
