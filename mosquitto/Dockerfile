FROM eclipse-mosquitto:2

# Copy the mosquitto configuration
COPY config/mosquitto.conf /mosquitto/config/mosquitto.conf

# Expose MQTT and WebSocket ports
EXPOSE 1883 9001

# Use the default entrypoint from the base image
CMD ["/usr/sbin/mosquitto", "-c", "/mosquitto/config/mosquitto.conf"]
