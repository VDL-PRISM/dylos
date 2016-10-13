import json
import logging
import os
import socket
import time

import paho.mqtt.client as mqtt
import yaml

from sensors import setup_air_quality, setup_temp_sensor, setup_lcd_sensor

LOGGER = logging.getLogger(__name__)


def run(config_file):
    LOGGER.info("Reading from config")
    config = yaml.load(config_file)
    mqtt_config = config['mqtt']

    LOGGER.info("Starting air quality sensor")
    air_sensor = setup_air_quality(config['serial']['port'],
                                   config['serial']['baudrate'])

    LOGGER.info("Starting temperature sensor")
    temp_sensor = setup_temp_sensor()

    LOGGER.info("Starting LCD screen")
    lcd = setup_lcd_sensor()

    while True:
        try:
            LOGGER.info("Getting host name")
            hostname = socket.gethostname()
            LOGGER.info("Hostname: %s", hostname)

            LOGGER.info("Connecting to MQTT broker")
            client = mqtt.Client(client_id=hostname, clean_session=False)
            client.username_pw_set(mqtt_config['username'], mqtt_config['password'])
            client.connect(mqtt_config['broker'], mqtt_config['port'])
        except Exception as e:
            # Keep going no matter of the exception -- hopefully it will fix itself
            LOGGER.exception("An exception occurred!")
            LOGGER.warn("Sleeping for 10 seconds and trying again...")
            time.sleep(10)
            continue

        break

    def on_publish(client, userdata, mid):
        LOGGER.info("Published MID: %s", mid)
    client.on_publish = on_publish

    # Read from sensors and publish data forever
    client.loop_start()
    sequence_number = 0

    while True:
        try:
            LOGGER.info("Getting new data")
            air_data = air_sensor()
            temp_data = temp_sensor()
            now = time.time()
            sequence_number += 1

            # combine data together
            data = {"sampletime": now,
                    "sequence": sequence_number,
                    "monitorname": hostname}
            data.update(air_data)
            data.update(temp_data)

            lcd("S: {}  L: {}".format(air_data['small'], air_data['large']),
                "{}".format(now) if temp_data['temperature'] is None
                else "{} C  {} RH".format(temp_data['temperature'], temp_data['humidity']))

            # Send to MQTT
            LOGGER.info("Publishing new data: %s", data)
            client.publish(mqtt_config['topic'] + hostname, json.dumps(data),
                           mqtt_config['qos'])

        except KeyboardInterrupt:
            client.loop_stop()
            break
        except Exception as e:
            # Keep going no matter of the exception -- hopefully it will fix itself
            LOGGER.exception("An exception occurred!")
            pass
