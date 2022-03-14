/*
 * View model for OctoPrint-StatusOLED Settings
 *
 * Author: Matt Bielich
 * License: AGPLv3
 */
$(function() {
    const PLUGIN_IDENTIFIER = "StatusOLED";
    const DISPLAY_SETTINGS_TAB_ID = "#tabStatusOLED_Display";
    const DEFAULT_SAMPLE_TEXTS = [
        "The quick brown fox jumps over the lazy dog.",
        "Previous message...",
        "Lorem ipsum dolor sit amet, consectetur adipiscing elit",
        "sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.",
        "Ut enim ad minim veniam,",
        "quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
        "Duis aute irure dolor in reprehenderit in voluptate velit esse cillum dolore eu fugiat nulla pariatur.",
        "Excepteur sint occaecat cupidatat non proident,",
        "sunt in culpa qui officia deserunt mollit anim id est laborum."
    ];

    function StatusOLEDSettingsViewModel(parameters) {
        var self = this;

        self.settingsVM = parameters[0];
        self.loginStateVM = parameters[1];
        self.accessVM = parameters[2];
        self.settings = null;

        self.hw_enabled = ko.observable();
        self.hw_rotated_180 = ko.observable();
        self.sw_enabled = ko.observable();
        self.sw_color = ko.observable();
        self.sw_color_value = ko.pureComputed({
            read: function () {
                return self.sw_color().replace("#", "");
            },
            write: function (value) {
                val = "#" + value.replace("#", "");
                self.sw_color(val);
            },
            owner: self
        });
        self.font_name = ko.observable();
        self.font_size = ko.observable();
        self.sec_font_name = ko.observable();
        self.sec_font_size = ko.observable();
        self.anim_loops = ko.observable();
        self.anim_speed = ko.observable();
        self.progbar_enabled = ko.observable();
        self.progbar_outline = ko.observable();
        self.progbar_size = ko.observable();
        self.sample_text = ko.observable(DEFAULT_SAMPLE_TEXTS.join("\n"));
        self.imageLoader = new Image();
        self.displayTabLoaded = ko.observable();
        self.imageLoader.onload = function() {
            self.sample_img(self.imageLoader.src);
        }
        self.sample_img = ko.observable("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAAAgAQAAAADyWU2IAAAAV0lEQVR4nGNgGImAzwCF+4CBDcZkYmBgYGB4eFzi27EDDAwMDAwsEOFlM2ythJFUMPxiQNUiATeCgZGBgYGB4ec1AZkcw5PyDcg2MaLwGBgY+El3PF0BANAXDN4diusOAAAAAElFTkSuQmCC");

        self.sample_img_loader = ko.computed(function() {
            self.displayTabLoaded();
            var url = `api/plugin/${PLUGIN_IDENTIFIER}?sample=${Date.now()}&font_name=${encodeURIComponent(self.font_name())}&font_size=${encodeURIComponent(self.font_size())}&sec_font_name=${encodeURIComponent(self.sec_font_name())}&sec_font_size=${encodeURIComponent(self.sec_font_size())}&anim_loops=${encodeURIComponent(self.anim_loops())}&anim_speed=${encodeURIComponent(self.anim_speed())}&text=${encodeURIComponent(self.sample_text())}&progbar_enabled=${encodeURIComponent(self.progbar_enabled())}&progbar_outline=${encodeURIComponent(self.progbar_outline())}&progbar_size=${encodeURIComponent(self.progbar_size())}`;
            self.imageLoader.src = url;
            return url;
        });

        self.is_debug = false;

        $(document).on('shown.bs.tab', function (event) {
            if (event && event.target && event.target.hash === DISPLAY_SETTINGS_TAB_ID) {
                // fetch a new sample when the tab loads
                self.displayTabLoaded.notifySubscribers();
            }
        });

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== PLUGIN_IDENTIFIER || !self.sw_enabled() || !data.isSample) { return; }
            var tab = $("#settings_plugin_StatusOLED.tab-pane.active li.active a[data-toggle=tab]")[0]
            if (!tab || tab.hash !== DISPLAY_SETTINGS_TAB_ID) { return; }
            self.sample_img(data.display);
        }

        /* Settings Binding/Reset/Storage */

        self.onBeforeBinding = function() {
            self.resetLocalSettings();
        }

        self.onSettingsBeforeSave = function () {
            self.initSettings();

            // Persist the local settings for next time
            self.settings.hardware_display.enabled(self.hw_enabled());
            self.settings.hardware_display.rotated_180(self.hw_rotated_180());
            self.settings.software_display.enabled(self.sw_enabled());
            self.settings.software_display.color(self.sw_color_value());
            self.settings.display.font.name(self.font_name());
            self.settings.display.font.size(self.font_size());
            self.settings.display.secondary_font.name(self.sec_font_name());
            self.settings.display.secondary_font.size(self.sec_font_size());
            self.settings.display.animation.loops(self.anim_loops());
            self.settings.display.animation.speed(self.anim_speed());
            self.settings.display.progress_bar.enabled(self.progbar_enabled());
            self.settings.display.progress_bar.outline(self.progbar_outline());
            self.settings.display.progress_bar.size(self.progbar_size());
        };

        self.onSettingsHidden = function() {
            self.resetLocalSettings();
        }

        self.initSettings = function() {
            if (!self.settings) {
                self.settings = self.settingsVM.settings.plugins.StatusOLED;
            }
        }

        self.resetLocalSettings = function() {
            self.initSettings();

            // Read in settings to local copy
            self.hw_enabled(self.settings.hardware_display.enabled());
            self.hw_rotated_180(self.settings.hardware_display.rotated_180());
            self.sw_enabled(self.settings.software_display.enabled());
            self.sw_color_value(self.settings.software_display.color());
            self.font_name(self.settings.display.font.name());
            self.font_size(self.settings.display.font.size());
            self.sec_font_name(self.settings.display.secondary_font.name());
            self.sec_font_size(self.settings.display.secondary_font.size());
            self.anim_loops(self.settings.display.animation.loops());
            self.anim_speed(self.settings.display.animation.speed());
            self.progbar_enabled(self.settings.display.progress_bar.enabled());
            self.progbar_outline(self.settings.display.progress_bar.outline());
            self.progbar_size(self.settings.display.progress_bar.size());

            self.is_debug = self.settings.debug && self.settings.debug();
        }
    }

    OCTOPRINT_VIEWMODELS.push({
        construct: StatusOLEDSettingsViewModel,
        dependencies: [ "settingsViewModel", "loginStateViewModel", "accessViewModel" ],
        elements: [ "#settings_plugin_StatusOLED" ]
    });
});
