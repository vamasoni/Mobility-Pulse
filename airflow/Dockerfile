FROM apache/airflow:2.10.4-python3.11
USER root
RUN apt-get update && apt-get install -y --no-install-recommends gcc libgomp1 && rm -rf /var/lib/apt/lists/*
USER airflow
WORKDIR /opt/mobility-pulse
COPY requirements-airflow.txt /tmp/requirements-airflow.txt
RUN pip install --no-cache-dir --constraint "https://raw.githubusercontent.com/apache/airflow/constraints-2.10.4/constraints-3.11.txt" -r /tmp/requirements-airflow.txt
