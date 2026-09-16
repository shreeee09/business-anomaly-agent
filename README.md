# Business Anomaly Agent

An automated business anomaly detection system that analyzes daily business metrics, identifies unusual behavior, explains anomalies in business terms, generates a report, and sends email alerts for critical anomalies.

## Project Overview

The Business Anomaly Agent analyzes historical business data and detects significant deviations from normal business behavior.

The system currently monitors:

- Traffic
- Orders
- Revenue
- Marketing Cost
- Refunds
- Conversion Rate

The project uses statistical anomaly detection based on a rolling 7-day baseline and Z-score analysis.

## How It Works

The agent follows this workflow:

1. Load business data from CSV
2. Validate the dataset
3. Calculate a previous 7-day rolling baseline
4. Calculate Z-scores for business metrics
5. Detect anomalies using a Z-score threshold
6. Determine whether the metric is HIGH or LOW
7. Calculate the difference from the baseline
8. Calculate percentage deviation
9. Assign anomaly severity
10. Generate a business explanation
11. Generate an Excel report
12. Check alert history
13. Send email alerts for new critical anomalies
14. Store sent alerts in the alert history

## Anomaly Detection

For each metric, the system calculates:

### Rolling Baseline

The baseline is the average value of the previous 7 days.

The current day's value is not included in its own baseline.

### Z-Score

The Z-score measures how far the current value is from its historical baseline in terms of standard deviations.

An anomaly is detected when:

`|Z-score| > 3`

## Severity Levels

| Z-Score | Severity |
|---|---|
| 3 to <5 | Moderate |
| 5 to <10 | High |
| >=10 | Critical |

## Business Explanation

For detected anomalies, the system calculates the percentage deviation from the baseline and generates an explanation such as:

`marketing_cost was 11.27% Above its baseline. Severity: Moderate.`

This converts statistical output into information that can be understood from a business perspective.

## Alert System

Email alerts are sent only for **Critical** anomalies.

The system also maintains an `alert_history.csv` file containing previously sent alerts.

Before sending an alert, the agent checks the history using:

- Date
- Metric

This prevents the same critical anomaly from generating repeated emails.

## Error Handling

The agent validates important inputs before processing:

- Email credentials
- Data file existence
- Required dataset columns

Errors are handled using exception handling around the email process.

## Output

The agent generates an Excel report containing:

- Date
- Metric
- Actual Value
- Baseline
- Percentage Deviation
- Severity
- Business Explanation

## Project Structure

```text
business-anomaly-agent/
│
├── anomaly_agent.py
├── README.md
├── requirements.txt
├── .gitignore
│
├── data/
│   └── shree_market.csv
│
├── reports.xlsx
├── alert_history.csv
├── agent_output.log
├── agent_error.log
│
└── Credencial101.env
