import './bucket_agg';
import './metric_agg';

import angular from 'angular';
import _ from 'lodash';
import * as queryDef from './query_def';
import { QueryCtrl } from 'app/plugins/sdk';

export class ElasticQueryCtrl extends QueryCtrl {
  static templateUrl = 'partials/query.editor.html';

  esVersion: any;
  rawQueryOld: string;

  /** @ngInject */
  constructor($scope, $injector, private $rootScope, private uiSegmentSrv) {
    super($scope, $injector);

    this.esVersion = this.datasource.esVersion;
    this.queryUpdated();
  }

  getFields(type) {
    const jsonStr = angular.toJson({ find: 'fields', type: type });
    return this.datasource
      .metricFindQuery(jsonStr)
      .then(this.uiSegmentSrv.transformToSegments(false))
      .catch(this.handleQueryError.bind(this));
  }

  queryUpdated() {
    const newJson = angular.toJson(this.datasource.queryBuilder.build(this.target), true);
    if (this.rawQueryOld && newJson !== this.rawQueryOld) {
      this.refresh();
    }

    this.rawQueryOld = newJson;
    this.$rootScope.appEvent('elastic-query-updated');
  }

  getCollapsedText() {
    const metricAggs = this.target.metrics;
    const bucketAggs = this.target.bucketAggs;
    const metricAggTypes = queryDef.getMetricAggTypes(this.esVersion);
    const bucketAggTypes = queryDef.bucketAggTypes;
    let text = '';

    if (this.target.query) {
      text += 'Query: ' + this.target.query + ', ';
    }

    text += 'Metrics: ';

    _.each(metricAggs, (metric, index) => {
      const aggDef = _.find(metricAggTypes, { value: metric.type });
      text += aggDef.text + '(';
      if (aggDef.requiresField) {
        text += metric.field;
      }
      text += '), ';
    });

    _.each(bucketAggs, (bucketAgg, index) => {
      if (index === 0) {
        text += ' Group by: ';
      }

      const aggDef = _.find(bucketAggTypes, { value: bucketAgg.type });
      text += aggDef.text + '(';
      if (aggDef.requiresField) {
        text += bucketAgg.field;
      }
      text += '), ';
    });

    if (this.target.alias) {
      text += 'Alias: ' + this.target.alias;
    }

    return text;
  }

  handleQueryError(err) {
    this.error = err.message || 'Failed to issue metric query';
    return [];
  }
}
