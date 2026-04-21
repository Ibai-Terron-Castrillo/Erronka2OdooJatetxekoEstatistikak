FROM odoo:16.0

LABEL MAINTAINER Daniel Moreno <hola@bigodoo.com>
USER root

# Install matplotlib for PDF charts
RUN pip3 install matplotlib

USER odoo

