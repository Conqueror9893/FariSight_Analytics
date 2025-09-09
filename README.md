FariSight

A demo system showcasing AI-driven, real-time dashboards and automated reporting for Bank ABC.

Features
Synthetic transaction data generator

FastAPI backend for transactions & KPI metrics

Real-time dashboard (Streamlit)

AI NL → SQL querying (LangChain)

Reporting: PDF/Excel exports

Alerts: Thresholds, Slack/email notifications

Project Structure

├── data/            # Transaction generator
├── backend/         # FastAPI service
├── dashboard/       # Streamlit UI
├── requirements.txt # Python deps

Setup
Create and activate virtual environment

python -m venv farienv
./farienv/Scripts/activate
Install dependencies

pip install -r requirements.txt
Running the Project
1. Start Data Generator

python ./data/generator.py
2. Start Backend API

uvicorn backend.app:app --host 0.0.0.0 --reload --port 8001
3. Launch Dashboard
(Add instructions if Streamlit app present, e.g.,)


streamlit run dashboard/app.py
Reporting & Alerts
Download PDF/Excel report via dashboard
Ask queries to the model.

Threshold alerts show in dashboard, send Slack/email notifications