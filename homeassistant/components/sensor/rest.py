"""
homeassistant.components.sensor.rest
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
The rest sensor will consume JSON responses sent by an exposed REST API.

For more details about this platform, please refer to the documentation at
https://home-assistant.io/components/sensor.rest/
"""
from datetime import timedelta
import logging
import requests

from homeassistant.const import CONF_VALUE_TEMPLATE
from homeassistant.util import template, Throttle
from homeassistant.helpers.entity import Entity

_LOGGER = logging.getLogger(__name__)

DEFAULT_NAME = 'REST Sensor'
DEFAULT_METHOD = 'GET'

# Return cached results if last scan was less then this time ago
MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=60)


# pylint: disable=unused-variable
def setup_platform(hass, config, add_devices, discovery_info=None):
    """ Get the REST sensor. """

    use_get = False
    use_post = False

    resource = config.get('resource', None)
    method = config.get('method', DEFAULT_METHOD)
    payload = config.get('payload', None)
    verify_ssl = config.get('verify_ssl', True)

    if method == 'GET':
        use_get = True
    elif method == 'POST':
        use_post = True

    try:
        if use_get:
            response = requests.get(resource, timeout=10, verify=verify_ssl)
        elif use_post:
            response = requests.post(resource, data=payload, timeout=10,
                                     verify=verify_ssl)
        if not response.ok:
            _LOGGER.error('Response status is "%s"', response.status_code)
            return False
    except requests.exceptions.MissingSchema:
        _LOGGER.error('Missing resource or schema in configuration. '
                      'Add http:// to your URL.')
        return False
    except requests.exceptions.ConnectionError:
        _LOGGER.error('No route to resource/endpoint. '
                      'Please check the URL in the configuration file.')
        return False

    if use_get:
        rest = RestDataGet(resource, verify_ssl)
    elif use_post:
        rest = RestDataPost(resource, payload, verify_ssl)

    add_devices([RestSensor(hass,
                            rest,
                            config.get('name', DEFAULT_NAME),
                            config.get('unit_of_measurement'),
                            config.get(CONF_VALUE_TEMPLATE))])


# pylint: disable=too-many-arguments
class RestSensor(Entity):
    """ Implements a REST sensor. """

    def __init__(self, hass, rest, name, unit_of_measurement, value_template):
        self._hass = hass
        self.rest = rest
        self._name = name
        self._state = 'n/a'
        self._unit_of_measurement = unit_of_measurement
        self._value_template = value_template
        self.update()

    @property
    def name(self):
        """ The name of the sensor. """
        return self._name

    @property
    def unit_of_measurement(self):
        """ Unit the value is expressed in. """
        return self._unit_of_measurement

    @property
    def state(self):
        """ Returns the state of the device. """
        return self._state

    def update(self):
        """ Gets the latest data from REST API and updates the state. """
        self.rest.update()
        value = self.rest.data

        if 'error' in value:
            self._state = value['error']
        else:
            if self._value_template is not None:
                value = template.render_with_possible_json_value(
                    self._hass, self._value_template, value, 'N/A')
            self._state = value


# pylint: disable=too-few-public-methods
class RestDataGet(object):
    """ Class for handling the data retrieval with GET method. """

    def __init__(self, resource, verify_ssl):
        self._resource = resource
        self._verify_ssl = verify_ssl
        self.data = dict()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """ Gets the latest data from REST service with GET method. """
        try:
            response = requests.get(self._resource, timeout=10,
                                    verify=self._verify_ssl)
            if 'error' in self.data:
                del self.data['error']
            self.data = response.text
        except requests.exceptions.ConnectionError:
            _LOGGER.error("No route to resource/endpoint.")
            self.data['error'] = 'N/A'


# pylint: disable=too-few-public-methods
class RestDataPost(object):
    """ Class for handling the data retrieval with POST method. """

    def __init__(self, resource, payload, verify_ssl):
        self._resource = resource
        self._payload = payload
        self._verify_ssl = verify_ssl
        self.data = dict()

    @Throttle(MIN_TIME_BETWEEN_UPDATES)
    def update(self):
        """ Gets the latest data from REST service with POST method. """
        try:
            response = requests.post(self._resource, data=self._payload,
                                     timeout=10, verify=self._verify_ssl)
            if 'error' in self.data:
                del self.data['error']
            self.data = response.text
        except requests.exceptions.ConnectionError:
            _LOGGER.error("No route to resource/endpoint.")
            self.data['error'] = 'N/A'
