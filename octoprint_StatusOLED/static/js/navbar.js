/*
 * View model for OctoPrint-StatusOLED NavBar display
 *
 * Author: Matt Bielich
 * License: AGPLv3
 */
$(function() {
    const PLUGIN_IDENTIFIER = "StatusOLED";

    function StatusOLEDNavBarViewModel(parameters) {
        var self = this;

        self.settingsVM = parameters[0];

        self.enabled = ko.observable();
        self.color = ko.observable();

        self.imageLoader = new Image();
        self.imageLoader.onload = function() {
            self.img(self.imageLoader.src);
        }
        self.img = ko.observable("data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAIAAAAAgAQAAAADyWU2IAAAAV0lEQVR4nGNgGImAzwCF+4CBDcZkYmBgYGB4eFzi27EDDAwMDAwsEOFlM2ythJFUMPxiQNUiATeCgZGBgYGB4ec1AZkcw5PyDcg2MaLwGBgY+El3PF0BANAXDN4diusOAAAAAElFTkSuQmCC");

        self.onBeforeBinding = function() {
            self.resetLocalSettings();

            if (self.enabled()) {
                setTimeout(function() {
                    self.imageLoader.src = `api/plugin/${PLUGIN_IDENTIFIER}`;
                }, 0);
            }
        }

        self.onSettingsHidden = function () {
            self.resetLocalSettings();
        }

        self.resetLocalSettings = function() {
            var settings = self.settingsVM.settings.plugins.StatusOLED;
            self.enabled(settings.software_display.enabled());
            self.color("#" + settings.software_display.color());
        }

        self.onDataUpdaterPluginMessage = function(plugin, data) {
            if (plugin !== PLUGIN_IDENTIFIER || !self.enabled() || data.isSample) { return; }
            self.img(data.display);
        }
    }

    // This is how our plugin registers itself with the application, by adding some configuration
    // information to the global variable OCTOPRINT_VIEWMODELS
    OCTOPRINT_VIEWMODELS.push([
        // This is the constructor to call for instantiating the plugin
        StatusOLEDNavBarViewModel,

        // This is a list of dependencies to inject into the plugin, the order which you request
        // here is the order in which the dependencies will be injected into your view model upon
        // instantiation via the parameters argument
        ["settingsViewModel"],

        // Finally, this is the list of selectors for all elements we want this view model to be bound to.
        ["#navbar_plugin_StatusOLED"]
    ]);
});