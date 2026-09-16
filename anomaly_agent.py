import pandas as pd
import os
import smtplib
from dotenv import load_dotenv
from email.message import EmailMessage
from pathlib import Path

# -----------------------------
# Configuration
# -----------------------------
BASE_DIR = Path(__file__).resolve().parent
DATA_FILE = BASE_DIR / "data" / "shree_market.csv"
REPORT_FILE = BASE_DIR / "reports.xlsx"
ENV_FILE = BASE_DIR / "Credencial101.env"

METRICS = [
    "traffic",
    "orders",
    "revenue",
    "marketing_cost",
    "refunds",
    "Conversion rate",
]

WINDOW = 7
Z_THRESHOLD = 3


# -----------------------------
# Load configuration
# -----------------------------
load_dotenv(ENV_FILE)

sender_email = os.getenv("SENDER_EMAIL")
receiver_email = os.getenv("RECEIVER_EMAIL")
app_password = os.getenv("APP_PASSWORD")
if not sender_email or not receiver_email or not receiver_email :
    raise ValueError(" Email Credentials Are  missing from Credential101")

# -----------------------------
# Load and prepare data
# -----------------------------
if not DATA_FILE.exists():
    raise FileNotFoundError(f"DATA_FILE is Not Found:{DATA_FILE}")
df = pd.read_csv(DATA_FILE)
df["date"] = pd.to_datetime(df["date"])
required_columns = METRICS + ["date"]
missing_columns =[
    col for col in required_columns 
    if col not in df.columns
    
]
if  missing_columns :
    raise ValueError(f"Missing Columns :{missing_columns}" )
df.set_index("date", inplace=True)


# -----------------------------
# Calculate rolling baseline
# Previous 7 observations are used
# as the baseline for each day.
# -----------------------------
mean_rolling = pd.DataFrame(index=df.index)

for metric in METRICS:
    mean_rolling[metric] = df[metric].rolling(WINDOW).mean().shift(1)


# -----------------------------
# Calculate rolling Z-scores
# -----------------------------
z_score = pd.DataFrame(index=df.index)

for metric in METRICS:
    mean = df[metric].rolling(WINDOW).mean().shift(1)
    std = df[metric].rolling(WINDOW).std().shift(1)
    z = (df[metric] - mean) / std
    z_score[metric] = z


# -----------------------------
# Detect anomalies
# -----------------------------
anomalies = z_score.abs() > Z_THRESHOLD
anomaly_dates = anomalies.any(axis=1)
anomaly_flags = anomalies.loc[anomaly_dates]


# -----------------------------
# Build anomaly records
# -----------------------------
anomaly_records = []

for date in anomaly_flags.index:
    metrices = anomaly_flags.loc[date].index[
        anomaly_flags.loc[date] == True
    ]

    for metric in metrices:
        actual_value = df.loc[date, metric]
        z = z_score.loc[date, metric]

        if z > 0:
            direction = "HIGH"
        else:
            direction = "LOW"

        anomaly_records.append(
            [date, metric, actual_value, z, direction]
        )


final_dataframe = pd.DataFrame(
    anomaly_records,
    columns=["date", "metric", "actual_value", "z_score", "verdict"],
)


# -----------------------------
# Add baseline and deviation
# -----------------------------
final_dataframe["baseline"] = [
    mean_rolling.loc[row["date"], row["metric"]]
    for _, row in final_dataframe.iterrows()
]

final_dataframe["DIFFERENCE"] = (
    final_dataframe["actual_value"] - final_dataframe["baseline"]
)

final_dataframe["percentage_deviation"] = (
    final_dataframe["DIFFERENCE"] / final_dataframe["baseline"]
) * 100


# -----------------------------
# Assign severity
# -----------------------------
for i in range(len(final_dataframe)):
    z = abs(final_dataframe.loc[i, "z_score"])

    if 3 <= z < 5:
        severity = "Moderate"
    elif 5 <= z < 10:
        severity = "High"
    else:
        severity = "Critical"

    final_dataframe.loc[i, "Severity"] = severity


# -----------------------------
# Add business explanation
# -----------------------------
for i in range(len(final_dataframe)):
    metric = final_dataframe.loc[i, "metric"]
    deviation = abs(final_dataframe.loc[i, "percentage_deviation"])
    direction = (
        "Above"
        if final_dataframe.loc[i, "verdict"] == "HIGH"
        else "Below"
    )
    severity = final_dataframe.loc[i, "Severity"]

    final_dataframe.loc[i, "Explanation"] = (
        f"{metric} was {deviation:.2f}% {direction} its baseline. "
        f"Severity : {severity}"
    )


# -----------------------------
# Generate Excel report
# -----------------------------
report = final_dataframe[
    [
        "date",
        "metric",
        "actual_value",
        "baseline",
        "percentage_deviation",
        "Severity",
        "Explanation",
    ]
]

report.to_excel(REPORT_FILE, index=False)


# -----------------------------
# Filter critical anomalies
# -----------------------------
critical_final_dataframe = final_dataframe[
    final_dataframe["Severity"] == "Critical"
]
ALERT_HISTORY_FILE = BASE_DIR / "alert_history.csv"

if ALERT_HISTORY_FILE.exists():
    alert_history = pd.read_csv(ALERT_HISTORY_FILE)
else:
    alert_history = pd.DataFrame(columns=["date", "metric"])

# -----------------------------
# Send email only if critical
# anomalies exist
# -----------------------------
if len(alert_history) > 0:
    critical_final_dataframe = critical_final_dataframe.copy()
    critical_final_dataframe["date"] = critical_final_dataframe["date"].astype(str)
    alert_history["date"] = alert_history["date"].astype(str)

    critical_final_dataframe = critical_final_dataframe[
        ~critical_final_dataframe.set_index(["date", "metric"]).index.isin(
            alert_history.set_index(["date", "metric"]).index
        )
    ]
if len(critical_final_dataframe) > 0:

    email_body = ""

    for _, row in critical_final_dataframe.iterrows():
        email_body += (
            f"{row['date'].strftime('%Y-%m-%d')} | "
            f"{row['metric']} {row['actual_value']:.2f} | "
            f"baseline: {row['baseline']:.2f} | "
            f"percentage_deviation: {row['percentage_deviation']:.2f}% | "
            f"Severity: {row['Severity']}\n"
        )

    try:
        msg = EmailMessage()
        msg["From"] = sender_email
        msg["To"] = receiver_email
        msg["Subject"] = "Critical Anomaly Alert"
        msg.set_content(email_body)

        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)
        server.quit()

        print("Critical anomaly email sent successfully.")
        if len(alert_history) == 0:
            alert_history = critical_final_dataframe[["date", "metric"]].copy()
        else:
            alert_history = pd.concat(
        [
            alert_history,
            critical_final_dataframe[["date", "metric"]]
        ],
        ignore_index=True
    )

        alert_history.drop_duplicates(
        subset=["date", "metric"],
        inplace=True
)

        alert_history.to_csv(ALERT_HISTORY_FILE, index=False)

    except Exception as e:
        print("Email sending Failed:", e)

else:
    print("NO CRITICAL ANOMALY FOUND")


print(f"Report saved to: {REPORT_FILE}")
