#
#  Project: MXCuBE
#  https://github.com/mxcube.
#
#  This file is part of MXCuBE software.
#
#  MXCuBE is free software: you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation, either version 3 of the License, or
#  (at your option) any later version.
#
#  MXCuBE is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with MXCuBE.  If not, see <http://www.gnu.org/licenses/>.

import logging
from AbstractDetector import AbstractDetector
from HardwareRepository.BaseHardwareObjects import HardwareObject


__credits__ = ["EMBL Hamburg"]
__version__ = "2.3."
__category__ = "General"


class EMBLDetector(AbstractDetector, HardwareObject):
    """Detector class. Contains all information about detector
       - states are 'OK', and 'BAD'
       - status is busy, exposing, ready, etc.
       - physical property is RH for pilatus, P for rayonix
    """

    def __init__(self, name):
        AbstractDetector.__init__(self)
        HardwareObject.__init__(self, name)

        self.temperature = 0
        self.humidity = 0
        self.tolerance = 0.1
        self.roi_mode = None
        self.roi_modes = []
        self.collect_name = None
        self.shutter_name = None
        self.temp_treshold = None
        self.hum_treshold = None
        self.exp_time_limits = None
        self.pixel_min = None
        self.pixel_max = None
        self.actual_frame_rate = None

        self.chan_beam_xy = None
        self.chan_temperature = None
        self.chan_humidity = None
        self.chan_status = None
        self.chan_roi_mode = None
        self.chan_frame_rate = None
        self.chan_actual_frame_rate = None

        self.distance_motor_hwobj = None

    def init(self):
        self.distance_motor_hwobj = self.getObjectByRole("distance_motor")

        self.chan_temperature = self.getChannelObject('chanTemperature')
        if self.chan_temperature is not None:
            self.chan_temperature.connectSignal(\
                "update", self.temperature_changed)
        else:
            logging.getLogger().error(\
                "Detector: Temperature channel not defined")

        self.chan_humidity = self.getChannelObject('chanHumidity')
        if self.chan_humidity is not None:
            self.chan_humidity.connectSignal(\
                "update", self.humidity_changed)
        else:
            logging.getLogger().error(\
                "Detector: Humidity channel not defined")

        self.chan_status = self.getChannelObject('chanStatus')
        if self.chan_status is not None:
            self.chan_status.connectSignal(\
                'update', self.status_changed)
        else:
            logging.getLogger().error("Detector: Status channel not defined")

        self.chan_roi_mode = self.getChannelObject('chanRoiMode')
        if self.chan_roi_mode is not None:
            self.chan_roi_mode.connectSignal('update', self.roi_mode_changed)
        else:
            logging.getLogger().error("Detector: ROI mode channel not defined")

        self.chan_frame_rate = self.getChannelObject('chanFrameRate')
        if self.chan_frame_rate is not None:
            self.chan_frame_rate.connectSignal('update', \
                 self.frame_rate_changed)
        else:
            logging.getLogger().error("Detector: Frame rate channel not defined")

        self.chan_actual_frame_rate = self.getChannelObject('chanActualFrameRate')
        if self.chan_actual_frame_rate is not None:
            self.chan_actual_frame_rate.connectSignal('update', self.actual_frame_rate_changed)

        self.chan_beam_xy = self.getChannelObject('chanBeamXY')

        self.collect_name = self.getProperty("collectName")
        self.shutter_name = self.getProperty("shutterName")
        self.tolerance = self.getProperty("tolerance")
        self.temp_treshold = self.getProperty("tempThreshold")
        self.hum_treshold = self.getProperty("humidityThreshold")
        self.pixel_min = self.getProperty("px_min")
        self.pixel_max = self.getProperty("px_max")
        self.roi_modes = eval(self.getProperty("roiModes"))

    def get_distance(self):
        """Returns detector distance in mm"""
        return self.distance_motor_hwobj.getPosition()

    def get_distance_limits(self):
        """Returns detector distance limits"""
        if self.distance_motor_hwobj is not None:
            return self.distance_motor_hwobj.getLimits()
        else:
            return self.default_distance_limits

    def has_shutterless(self):
        """Return True if has shutterless mode"""
        return self.getProperty("hasShutterless")

    def get_collect_name(self):
        """Returns collection name"""
        return self.collect_name

    def get_shutter_name(self):
        """Returns shutter name"""
        return self.shutter_name

    def temperature_changed(self, value):
        """Updates temperatur value"""
        if abs(self.temperature - value) > self.tolerance:
            self.temperature = value
            self.emit('temperatureChanged', (value, value < self.temp_treshold))
            self.status_changed('dummy')

    def humidity_changed(self, value):
        """Update humidity value"""
        if abs(self.humidity - value) > self.tolerance:
            self.humidity = value
            self.emit('humidityChanged', (value, value < self.hum_treshold))
            self.status_changed('dummy')

    def status_changed(self, status):
        """Status changed event"""
        status = "uninitialized"
        if self.chan_status is not None:
            status = self.chan_status.getValue()
        status_message = ""
        if self.temperature > self.temp_treshold:
            logging.getLogger().warning(\
                "Detector: Temperature %0.2f is greater than allowed %0.2f" %\
                (self.temperature, self.temp_treshold))
            status_message = "Detector temperature has exceeded threshold.\n"
        if self.humidity > self.hum_treshold:
            logging.getLogger().warning(\
                "Detector: Humidity %0.2f is greater than allowed %0.2f" %\
                (self.humidity, self.hum_treshold))
            status_message = status_message + \
                "Detector humidity has exceeded threshold.\n"
        if status == "calibrating":
            status_message = status_message + "Energy change in progress.\n"
            status_message = status_message + "Please wait...\n"
        elif status != "ready":
            status_message = status_message + "Detector is not ready.\n"
            status_message = status_message + \
                "Cannot start a collection at the moment."
        self.emit('statusChanged', (status, status_message, ))

    def roi_mode_changed(self, mode):
        """ROI mode change event"""
        self.roi_mode = self.roi_modes.index(mode)
        self.emit('detectorModeChanged', (self.roi_mode, ))

    def frame_rate_changed(self, frame_rate):
        """Updates frame rate"""
        if frame_rate is not None:
            self.exp_time_limits = (1 / float(frame_rate), 6000)
        self.emit('expTimeLimitsChanged', (self.exp_time_limits, ))

    def actual_frame_rate_changed(self, value):
        self.actual_frame_rate = value
        self.emit('frameRateChanged', value)

    def set_roi_mode(self, mode):
        """Sets roi mode

        :param mode: roi mode
        :type mode: str
        """
        self.chan_roi_mode.setValue(self.roi_modes[mode])

    def get_roi_mode(self):
        """Returns current ROI mode"""
        return self.roi_mode

    def get_roi_modes(self):
        """Returns a list with available ROI modes"""
        return self.roi_modes

    def get_exposure_time_limits(self):
        """Returns exposure time limits as list with two floats"""
        return self.exp_time_limits

    def get_beam_centre(self):
        """Returns beam center coordinates"""
        beam_x = 0
        beam_y = 0
        if self.chan_beam_xy is not None:
            value = self.chan_beam_xy.getValue()
            beam_x = value[0]
            beam_y = value[1]
        return beam_x, beam_y

    def update_values(self):
        """Reemits signals"""
        self.emit('detectorModeChanged', (self.roi_mode, ))
        temp = self.chan_temperature.getValue()
        self.emit('temperatureChanged', (temp, temp < self.temp_treshold))
        hum = self.chan_humidity.getValue()
        self.emit('humidityChanged', (hum, hum < self.hum_treshold))
        self.status_changed("")
        self.emit('expTimeLimitsChanged', (self.exp_time_limits, ))
        self.emit('frameRateChanged', self.actual_frame_rate)
