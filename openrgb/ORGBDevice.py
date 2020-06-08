from .consts import ORGBDeviceType, ORGBZoneType
from .binreader import Blob

# This are internal. As a library user you shouldn't ever have to construct
# these.


def _set_batch(function, device, n_leds, colors, interpolate):
    if type(colors) is list:
        if interpolate is True:
            buf = []
            for led in range(n_leds):
                buf.append(
                    colors[int(len(colors) * led/n_leds)]
                )
            function(buf, device.id)
        else:
            function(colors, device.id)
    else:
        function([colors]*n_leds, device.id)


class ORGBMode(object):
    def __init__(self,
                 idx,
                 name,
                 value,
                 flags,
                 speed_min,
                 speed_max,
                 colors_min,
                 colors_max,
                 speed,
                 direction,
                 color_mode,
                 colors,
                 owner=None
                 ):
        self.id = idx
        self.name = name
        self.value = value
        self.flags = flags
        self.speed_min = speed_min
        self.speed_max = speed_max
        self.colors_min = colors_min
        self.colors_max = colors_max
        self.speed = speed
        self.direction = direction
        self.color_mode = color_mode
        self.colors = colors
        self.owner = owner

    def active(self):
        if self.owner is None:
            return
        # We belong to an ORGBDevice, which belongs to the main OpenRGB class.
        device = self.owner
        con = device.owner
        con.set_update_mode(self, device_id=device.id)

    # serialize this for the wire.
    def __bytes__(self):
        blob = Blob()
        blob.int(self.id)
        blob.string(self.name)
        blob.int(self.value)
        blob.uint(self.flags)
        blob.uint(self.speed_min)
        blob.uint(self.speed_max)
        blob.uint(self.colors_min)
        blob.uint(self.colors_max)

        # settings
        blob.uint(self.speed)
        blob.uint(self.direction)
        blob.uint(self.color_mode)

        blob.ushort(len(self.colors))
        for color in self.colors:
            blob.color(color)

        return blob.data

    def __getitem__(self, item):
        return self.__dict__[item]


class ORGBZone(object):
    def __init__(self,
                 idx,
                 name,
                 zonetype,
                 leds_min,
                 leds_max,
                 leds_count,
                 owner=None
                 ):
        self.id = idx
        self.name = name
        self.type = zonetype
        self.leds_min = leds_min
        self.leds_max = leds_max
        self.leds_count = leds_count
        self.owner = owner

    def set(self, colors, interpolate=False):
        device = self.owner
        con = device.owner
        n_leds = self.leds_count
        _set_batch(
            lambda c, did: con.update_zone_leds(self.id, c, did),
            device,
            n_leds,
            colors,
            interpolate
        )

    def __getitem__(self, item):
        return self.__dict__[item]


class ORGBLED(object):
    def __init__(self, idx, name, value, owner=None):
        self.id = idx
        self.name = name
        self.value = value
        self.owner = owner

    def set(self, color):
        device = self.owner
        con = device.owner
        con.update_single_led(self.id, color, device_id=device.id)

    def __getitem__(self, item):
        return self.__dict__[item]


class ORGBDevice:
    """
    ORGB is used to read device responses from the OpenRGB SDK server

    :attribute type: Device Type.
    :attribute name: Name of the device
    :attribute desc: Description of the device
    :attribute version: Device Version
    :attribute serial: Device Serial
    :attribute location: Device location
    :attribute active_mode: Devices Active Mode
    :attribute modes: List of modes
    :attribute zones: List of zones
    :attribute leds: List of LEDs
    :attribute colors: List of colors

    """

    def __init__(self, data, device_id=0, owner=None):
        self.owner = owner
        # hacky stupid way of doing this.
        self.id = device_id
        blob = Blob(data)
        length = blob.uint()
        if length != len(data):
            raise Exception('Length incorrect?')

        self.type = ORGBDeviceType(blob.uint())
        self.name = blob.string()
        self.desc = blob.string()
        self.version = blob.string()
        self.serial = blob.string()

        self.location = blob.string()

        n_modes = blob.ushort()
        self.active_mode = blob.uint()

        self.modes = []
        for mode_idx in range(n_modes):
            modename = blob.string()
            value = blob.int()
            flags = blob.uint()
            speed_min = blob.uint()
            speed_max = blob.uint()
            colors_min = blob.uint()
            colors_max = blob.uint()
            speed = blob.uint()
            direction = blob.uint()
            color_mode = blob.uint()

            color_len = blob.ushort()
            colors = []
            for color_index in range(color_len):
                colors.append(blob.color())

            new_mode = ORGBMode(
                mode_idx,
                modename,
                value,
                flags,
                speed_min,
                speed_max,
                colors_min,
                colors_max,
                speed,
                direction,
                color_mode,
                colors,
                owner=self
            )
            self.modes.append(new_mode)

        n_zones = blob.ushort()
        self.zones = []
        for zone_idx in range(n_zones):
            zonename = blob.string()
            zonetype = ORGBZoneType(blob.int())
            leds_min = blob.uint()
            leds_max = blob.uint()
            leds_count = blob.uint()

            matrix_size = blob.ushort()
            blob.skip(matrix_size)

            new_zone = ORGBZone(
                zone_idx,
                zonename,
                zonetype,
                leds_min,
                leds_max,
                leds_count,
                owner=self
            )

            self.zones.append(new_zone)

        n_leds = blob.ushort()
        self.leds = []
        for led_idx in range(n_leds):
            led_name = blob.string()
            led_value = blob.color()

            new_led = ORGBLED(
                led_idx,
                led_name,
                led_value,
                owner=self
            )

            self.leds.append(new_led)

        n_colors = blob.ushort()
        self.colors = []
        for color_idx in range(n_colors):
            self.colors.append(blob.color())

    def set(self, colors, interpolate=False):
        con = self.owner
        n_leds = len(self.leds)
        _set_batch(con.update_led, self, n_leds, colors, interpolate)

    def __repr__(self):
        return '{} - {}'.format(self.name, self.type)
