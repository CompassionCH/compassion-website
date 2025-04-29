odoo.define('my_compassion.my2_date_picker', function (require) {
    'use strict';

    var Widget = require('web.Widget');
    var core = require('web.core');

    var DateRangePicker = Widget.extend({
        start: function() {
            this._super.apply(this, arguments);
            this._createDatePicker();
            return this;
        },

        _createDatePicker: function() {
            // Create the structure
            var html = `
                <div class="date-range-picker d-flex justify-content-between align-items-end mb-3">
                    <div class="start-date mr-3">
                        <h6>Start Date</h6>
                        <div class="d-flex">
                            <select class="form-control start-month mr-2" style="width: 140px;"></select>
                            <select class="form-control start-year" style="width: 100px;"></select>
                        </div>
                    </div>
                    <div class="end-date">
                        <h6>End Date</h6>
                        <div class="d-flex">
                            <select class="form-control end-month mr-2" style="width: 140px;"></select>
                            <select class="form-control end-year" style="width: 100px;"></select>
                        </div>
                    </div>
                </div>`;

            this.$el.html(html);

            // Populate dropdowns
            this._populateMonths();
            this._populateYears();

            // Bind events
            this.$('.start-month, .start-year, .end-month, .end-year').on('change', this._onDateChange.bind(this));
        },

        _populateMonths: function() {
            var months = ['January', 'February', 'March', 'April', 'May', 'June',
                         'July', 'August', 'September', 'October', 'November', 'December'];

            var monthsHtml = months.map(function(month, index) {
                return `<option value="${index + 1}">${month}</option>`;
            }).join('');

            this.$('.start-month, .end-month').html(monthsHtml);
        },

        _populateYears: function() {
            var currentYear = new Date().getFullYear();
            var years = Array.from({length: 10}, (_, i) => currentYear - i);

            var yearsHtml = years.map(function(year) {
                return `<option value="${year}">${year}</option>`;
            }).join('');

            this.$('.start-year, .end-year').html(yearsHtml);
        },

        _onDateChange: function() {
            var startMonth = this.$('.start-month').val();
            var startYear = this.$('.start-year').val();
            var endMonth = this.$('.end-month').val();
            var endYear = this.$('.end-year').val();

            if (startMonth && startYear && endMonth && endYear) {
                this.trigger_up('date_changed', {
                    start_date: `${startYear}-${startMonth}-01`,
                    end_date: `${endYear}-${endMonth}-31`
                });
            }
        }
    });

    core.serviceRegistry.add('my_compassion.my2_date_picker', DateRangePicker);
    return DateRangePicker;
});