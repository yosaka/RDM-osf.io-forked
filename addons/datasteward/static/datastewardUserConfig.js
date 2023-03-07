/**
* Module that controls the DataSteward user settings. Includes Knockout view-model
* for syncing data.
*/

var ko = require('knockout');
var $ = require('jquery');
var Raven = require('raven-js');
var bootbox = require('bootbox');
require('js/osfToggleHeight');

var language = require('js/osfLanguage').Addons.dataverse;
var osfHelpers = require('js/osfHelpers');
var addonSettings = require('js/addonSettings');

var $modal = $('#datastewardModal');
var $resultModal = $('#datastewardResultModal');
var _ = require('js/rdmGettext')._;

function ViewModel(url) {
    var self = this;

    self.properName = 'DataSteward';
    self.dialog_closed_by_user = ko.observable(false);

    // Whether the initial data has been loaded
    self.addon_enabled = ko.observable(false);
    self.loaded = ko.observable(false);
    self.is_processing = ko.observable(false);
    self.is_process_failed = ko.observable(false);
    self.skipped_projects = ko.observable([]);

    // Flashed messages
    self.message = ko.observable('');
    self.messageClass = ko.observable('text-info');

    $modal.on("hidden.bs.modal", function () {
        if (self.dialog_closed_by_user()) {
            self.addon_enabled(!self.addon_enabled());
            self.dialog_closed_by_user(false);
        } else {
            self.is_processing(false);
            $resultModal.modal('show');
        }
    });

    $resultModal.on("hidden.bs.modal", function () {
        if (self.is_process_failed()) {
            self.addon_enabled(!self.addon_enabled());
            self.is_process_failed(false);
        }
        self.skipped_projects([]);
    });

    /** Reset all fields from Dataverse host selection modal */
    self.clearModal = function() {
        $modal.modal('hide');
        self.dialog_closed_by_user(true);
    };

    self.clearResultModal = function() {
        $resultModal.modal('hide');
    }

    /** Enable add on **/
    self.enableAddon = function() {
        self.is_processing(true);
        var data = {
            'enabled': self.addon_enabled()
        };
        $.ajax({
            url: url,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data)
        }).done(function (response) {
            $modal.modal('hide');
        }).fail(function (xhr, textStatus, error) {
            self.is_process_failed(true);
            $modal.modal('hide');
        });
    };

    /** Disable add on **/
    self.disableAddon = function() {
        self.is_processing(true);
        var data = {
            'enabled': self.addon_enabled()
        };
        $.ajax({
            url: url,
            type: 'POST',
            contentType: 'application/json',
            data: JSON.stringify(data)
        }).done(function (response) {
            var skipped_projects = response.skipped_projects;
            self.skipped_projects(skipped_projects);
            $modal.modal('hide');
        }).fail(function (xhr, textStatus, error) {
            self.is_processing(false);
            self.changeMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Could not disable DataSteward add-on', {
                extra: {
                    url: url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    };

    /** Change the flashed status message */
    self.changeMessage = function(text, css, timeout) {
        self.message(text);
        var cssClass = css || 'text-info';
        self.messageClass(cssClass);
        if (timeout) {
            // Reset message after timeout period
            setTimeout(function() {
                self.message('');
                self.messageClass('text-info');
            }, timeout);
        }
    };

    // Update observables with data from the server
    self.fetch = function() {
        $.ajax({
            url: url,
            type: 'GET',
            dataType: 'json'
        }).done(function (response) {
            var enabled = response.enabled;
            self.addon_enabled(enabled);
            self.loaded(true);
        }).fail(function (xhr, textStatus, error) {
            self.changeMessage(language.userSettingsError, 'text-danger');
            Raven.captureMessage('Could not GET DataSteward settings', {
                extra: {
                    url: url,
                    textStatus: textStatus,
                    error: error
                }
            });
        });
    };

    self.toggleCheckbox = function() {
        $modal.modal('show');
    };

    self.clickCSV = function () {
        var skipped_projects = self.skipped_projects();
        if (!skipped_projects) {
            return;
        }

        var rows = skipped_projects.map(project => [
            project['guid'],
            project['name']
        ]);

        exportToCsv('skipped_projects.csv', rows);
    }

    function exportToCsv(filename, rows) {
        var processRow = function (row) {
            var finalVal = '';
            for (var j = 0; j < row.length; j++) {
                var innerValue = row[j] === null ? '' : row[j].toString();
                if (row[j] instanceof Date) {
                    innerValue = row[j].toLocaleString();
                };
                var result = innerValue.replace(/"/g, '""');
                if (result.search(/("|,|\n)/g) >= 0)
                    result = '"' + result + '"';
                if (j > 0)
                    finalVal += ',';
                finalVal += result;
            }
            return finalVal + '\n';
        };

        var csvFile = '';
        for (var i = 0; i < rows.length; i++) {
            csvFile += processRow(rows[i]);
        }

        var blob = new Blob([csvFile], { type: 'text/csv;charset=utf-8;' });
        if (navigator.msSaveBlob) { // IE 10+
            navigator.msSaveBlob(blob, filename);
        } else {
            var link = document.createElement("a");
            if (link.download !== undefined) { // feature detection
                // Browsers that support HTML5 download attribute
                var url = URL.createObjectURL(blob);
                link.setAttribute("href", url);
                link.setAttribute("download", filename);
                link.style.visibility = 'hidden';
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
                URL.revokeObjectURL(url);
            }
        }
    }
}

function DataStewardUserConfig(selector, url) {
    // Initialization code
    var self = this;
    self.selector = selector;
    self.url = url;
    // On success, instantiate and bind the ViewModel
    self.viewModel = new ViewModel(url);
    osfHelpers.applyBindings(self.viewModel, self.selector);
}

module.exports = {
    DataStewardViewModel: ViewModel,
    DataStewardUserConfig: DataStewardUserConfig    // for backwards-compat
};
