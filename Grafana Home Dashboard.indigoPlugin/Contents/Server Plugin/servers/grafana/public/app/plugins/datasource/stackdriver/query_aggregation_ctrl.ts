import angular from 'angular';
import _ from 'lodash';
import * as options from './constants';
import kbn from 'app/core/utils/kbn';

export class StackdriverAggregation {
  constructor() {
    return {
      templateUrl: 'public/app/plugins/datasource/stackdriver/partials/query.aggregation.html',
      controller: 'StackdriverAggregationCtrl',
      restrict: 'E',
      scope: {
        target: '=',
        alignmentPeriod: '<',
        refresh: '&',
      },
    };
  }
}

export class StackdriverAggregationCtrl {
  alignmentPeriods: any[];
  aggOptions: any[];
  alignOptions: any[];
  target: any;

  /** @ngInject */
  constructor(private $scope) {
    this.$scope.ctrl = this;
    this.target = $scope.target;
    this.alignmentPeriods = options.alignmentPeriods;
    this.aggOptions = options.aggOptions;
    this.alignOptions = options.alignOptions;
    this.setAggOptions();
    this.setAlignOptions();
    const self = this;
    $scope.$on('metricTypeChanged', () => {
      self.setAggOptions();
      self.setAlignOptions();
    });
  }

  setAlignOptions() {
    this.alignOptions = !this.target.valueType
      ? []
      : options.alignOptions.filter(i => {
          return (
            i.valueTypes.indexOf(this.target.valueType) !== -1 && i.metricKinds.indexOf(this.target.metricKind) !== -1
          );
        });
    if (!this.alignOptions.find(o => o.value === this.target.aggregation.perSeriesAligner)) {
      this.target.aggregation.perSeriesAligner = this.alignOptions.length > 0 ? this.alignOptions[0].value : '';
    }
  }

  setAggOptions() {
    this.aggOptions = !this.target.metricKind
      ? []
      : options.aggOptions.filter(i => {
          return (
            i.valueTypes.indexOf(this.target.valueType) !== -1 && i.metricKinds.indexOf(this.target.metricKind) !== -1
          );
        });

    if (!this.aggOptions.find(o => o.value === this.target.aggregation.crossSeriesReducer)) {
      this.deselectAggregationOption('REDUCE_NONE');
    }

    if (this.target.aggregation.groupBys.length > 0) {
      this.aggOptions = this.aggOptions.filter(o => o.value !== 'REDUCE_NONE');
      this.deselectAggregationOption('REDUCE_NONE');
    }
  }

  formatAlignmentText() {
    const selectedAlignment = this.alignOptions.find(ap => ap.value === this.target.aggregation.perSeriesAligner);
    return `${kbn.secondsToHms(this.$scope.alignmentPeriod)} interval (${selectedAlignment.text})`;
  }

  deselectAggregationOption(notValidOptionValue: string) {
    const newValue = this.aggOptions.find(o => o.value !== notValidOptionValue);
    this.target.aggregation.crossSeriesReducer = newValue ? newValue.value : '';
  }
}

angular.module('grafana.controllers').directive('stackdriverAggregation', StackdriverAggregation);
angular.module('grafana.controllers').controller('StackdriverAggregationCtrl', StackdriverAggregationCtrl);
