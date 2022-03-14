# coding=utf-8
from __future__ import absolute_import

from octoprint_StatusOLED import (
    settings,
    displays
)

import octoprint.plugin

import flask
import time
import re

class StatusOledPlugin(
    octoprint.plugin.SettingsPlugin,
    octoprint.plugin.StartupPlugin,
    octoprint.plugin.TemplatePlugin,
    octoprint.plugin.AssetPlugin,
    octoprint.plugin.SimpleApiPlugin,
    octoprint.plugin.EventHandlerPlugin,
    octoprint.plugin.ProgressPlugin
):
    ##~~ Initialization
    def __init__(self):
        super(StatusOledPlugin, self).__init__()

        self._img = None
        self.hw_display = None
        self.sw_display = None

    ##~~ SettingsPlugin mixin

    def get_settings_defaults(self):
        return settings.DEFAULT_SETTINGS

    def on_settings_initialized(self):
        self._sample_img = displays.DisplayImage(
            self._settings.get(["display", "font", "name"]),
            self._settings.get_int(["display", "font", "size"]),
            self._settings.get(["display", "secondary_font", "name"]),
            self._settings.get_int(["display", "secondary_font", "size"]),
            self._settings.get_int(["display", "animation", "loops"]),
            self._settings.get_int(["display", "animation", "speed"]),
            self._settings.get_boolean(["display", "progress_bar", "enabled"]),
            self._settings.get_boolean(["display", "progress_bar", "outline"]),
            self._settings.get_int(["display", "progress_bar", "size"]),
        )
        self._sample_display = displays.SoftwareDisplay(
            self._sample_img,
            self.sendSampleDisplayToFrontend,
            True
        )

        self._img = displays.DisplayImage(
            self._settings.get(["display", "font", "name"]),
            self._settings.get_int(["display", "font", "size"]),
            self._settings.get(["display", "secondary_font", "name"]),
            self._settings.get_int(["display", "secondary_font", "size"]),
            self._settings.get_int(["display", "animation", "loops"]),
            self._settings.get_int(["display", "animation", "speed"]),
            self._settings.get_boolean(["display", "progress_bar", "enabled"]),
            self._settings.get_boolean(["display", "progress_bar", "outline"]),
            self._settings.get_int(["display", "progress_bar", "size"]),
            self._printer
        )

        self.hw_display = displays.HardwareDisplay(
            self._img,
            self._settings.get_boolean(["hardware_display", "enabled"]),
            self._settings.get_boolean(["hardware_display", "rotated_180"])
        )
        self.sw_display = displays.SoftwareDisplay(
            self._img,
            self.sendDisplayToFrontend,
            self._settings.get_boolean(["software_display", "enabled"])
        )

        debugEnabled = self._settings.get_boolean(["debug"])
        self._img.debug(debugEnabled)
        self.hw_display.debug(debugEnabled)
        self.sw_display.debug(debugEnabled)

    def on_settings_save(self, data):
        octoprint.plugin.SettingsPlugin.on_settings_save(self, data)
        self._img.set_settings(
            self._settings.get(["display", "font", "name"]),
            self._settings.get_int(["display", "font", "size"]),
            self._settings.get(["display", "secondary_font", "name"]),
            self._settings.get_int(["display", "secondary_font", "size"]),
            self._settings.get_int(["display", "animation", "loops"]),
            self._settings.get_int(["display", "animation", "speed"]),
            self._settings.get_boolean(["display", "progress_bar", "enabled"]),
            self._settings.get_boolean(["display", "progress_bar", "outline"]),
            self._settings.get_int(["display", "progress_bar", "size"])
        )
        self.hw_display.set_settings(
            self._settings.get_boolean(["hardware_display", "enabled"]),
            self._settings.get_boolean(["hardware_display", "rotated_180"])
        )
        self.sw_display.set_settings(
            self._settings.get_boolean(["software_display", "enabled"])
        )

    def _update_active_displays(self):
        [display.update() for display in [self.hw_display, self.sw_display] if display is not None and display.is_enabled()]

    def _clear_all_displays(self):
        [display.clear() for display in [self.hw_display, self.sw_display] if display is not None]

    ##~~ TemplatePlugin mixin

    def get_template_vars(self):
        return {
            "display_width": displays.PIOLED_WIDTH,
            "display_height": displays.PIOLED_HEIGHT,
            "anim_speed_xslow": displays.ANIMATION_SPEED_XSLOW,
            "anim_speed_xfast": displays.ANIMATION_SPEED_XFAST,
            "debug": self._settings.get_boolean(["debug"])
        }

    def get_template_configs(self):
        return []

    ##~~ StartupPlugin mixin

    def on_after_startup(self):
        self._update_active_displays()
        pass

    ##~~ SimpleApiPlugin
    def on_api_get(self, request):
        if self._img is None:
            return
        
        img = self._img
        args = request.args
        if "sample" in args and "font_name" in args and "font_size" in args:
            sec_font_name = args["sec_font_name"] if "sec_font_name" in args else None
            sec_font_size = args["sec_font_size"] if "sec_font_size" in args else None
            anim_loops = int(args["anim_loops"]) if "anim_loops" in args else None
            anim_speed = int(args["anim_speed"]) if "anim_speed" in args else None
            progbar_enabled = (args["progbar_enabled"].lower() in ["true"]) if "progbar_enabled" in args else False
            progbar_outline = (args["progbar_outline"].lower() in ["true"]) if "progbar_outline" in args else None
            progbar_size = int(args["progbar_size"]) if "progbar_size" in args else None
            img = self._sample_img
            if img is None:
                return
            img.set_settings(
                args["font_name"],
                args["font_size"],
                sec_font_name,
                sec_font_size,
                anim_loops,
                anim_speed,
                progbar_enabled,
                progbar_outline,
                progbar_size
            )
            img.show_text(args["text"] if "text" in args else "", self._sample_display.update)
            img.show_progress((time.localtime(time.time()).tm_sec) / 60.0 * 100)
        return flask.send_file(img.get_alpha_buffer(), mimetype="image/png", cache_timeout=0)

    ##~~ AssetPlugin

    def get_assets(self):
        return dict(
            js=["js/navbar.js", "js/settings.js"],
            css=["css/navbar.css", "css/settings.css"]
        )

    ##~~ ProgressPlugin
    def on_print_progress(self, storage, path, progress):
        self._img.show_progress(progress)
        self._update_active_displays()

    ##~~ Frontend Message Sending Helper
    def sendDisplayToFrontend(self, data, is_sample = False):
        if data is None:
            return
        self._plugin_manager.send_plugin_message(self._identifier, { "display": data, "isSample": is_sample })

    def sendSampleDisplayToFrontend(self, data):
        self.sendDisplayToFrontend(data, True)

    ##~~ GCode Phase hook

    def sent_m117(self, comm_instance, phase, cmd, cmd_type, gcode, *args, **kwargs):
        if gcode and gcode.upper() == "M117":
            text = ""
            match = re.search("M117\s+(.*)", cmd, re.I)
            if match is not None:
                text = match.group(1)
            if text == "":
                self._logger.info("Handling empty M117 command, clearing display")
                self._clear_all_displays()
            else:
                self._logger.info("Handling M117 command to display '%s'" % text)
                self._img.show_text(text, self._update_active_displays)
                self._img.show_progress()
                self._update_active_displays()

    ##~~ EventHandlerPlugin

    def on_event(self, event, payload):
        if event == "Shutdown":
            self._clear_all_displays()

	##~~ Softwareupdate hook

    def get_update_information(self):
        """
        Softwareupdate hook, standard library hook to handle software update and plugin version info
        """

        return dict(
            display_panel=dict(
                displayName="StatusOLED",
                displayVersion=self._plugin_version,

                # version check: github repository
                type="github_release",
                user="stealthmonkey99",
                repo="OctoPrint-StatusOLED",
                current=self._plugin_version,

                # update method: pip
                pip="https://github.com/stealthmonkey99/OctoPrint-StatusOLED/archive/{target_version}.zip"
            )
        )

# If you want your plugin to be registered within OctoPrint under a different name than what you defined in setup.py
# ("OctoPrint-PluginSkeleton"), you may define that here. Same goes for the other metadata derived from setup.py that
# can be overwritten via __plugin_xyz__ control properties. See the documentation for that.
__plugin_name__ = "StatusOLED Plugin"

# Set the Python version your plugin is compatible with below. Recommended is Python 3 only for all new plugins.
# OctoPrint 1.4.0 - 1.7.x run under both Python 3 and the end-of-life Python 2.
# OctoPrint 1.8.0 onwards only supports Python 3.
__plugin_pythoncompat__ = ">=3,<4"  # Only Python 3

def __plugin_load__():
    global __plugin_implementation__
    __plugin_implementation__ = StatusOledPlugin()

    global __plugin_hooks__
    __plugin_hooks__ = {
        "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information,
        "octoprint.comm.protocol.gcode.sent": __plugin_implementation__.sent_m117
    }
