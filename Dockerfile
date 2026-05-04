FROM odoo:16.0

USER root

# Install matplotlib for PDF charts
RUN pip3 install matplotlib

USER odoo

