FROM grafana/grafana:11.1.0

ENV GF_SECURITY_ADMIN_USER=admin
ENV GF_SECURITY_ADMIN_PASSWORD=health
ENV GF_DASHBOARDS_DEFAULT_HOME_DASHBOARD_PATH=/etc/grafana/provisioning/dashboards/dashs/specific-metrics.json

COPY provisioning/ /etc/grafana/provisioning/
