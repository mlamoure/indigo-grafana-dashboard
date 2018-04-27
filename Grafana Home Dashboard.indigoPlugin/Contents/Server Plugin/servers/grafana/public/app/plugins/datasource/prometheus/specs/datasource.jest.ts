import _ from 'lodash';
import moment from 'moment';
import q from 'q';
import { PrometheusDatasource, prometheusSpecialRegexEscape, prometheusRegularEscape } from '../datasource';

describe('PrometheusDatasource', () => {
  let ctx: any = {};
  let instanceSettings = {
    url: 'proxied',
    directUrl: 'direct',
    user: 'test',
    password: 'mupp',
    jsonData: {},
  };

  ctx.backendSrvMock = {};

  ctx.templateSrvMock = {
    replace: a => a,
  };
  ctx.timeSrvMock = {};

  beforeEach(() => {
    ctx.ds = new PrometheusDatasource(instanceSettings, q, ctx.backendSrvMock, ctx.templateSrvMock, ctx.timeSrvMock);
  });

  describe('Datasource metadata requests', () => {
    it('should perform a GET request with the default config', () => {
      ctx.backendSrvMock.datasourceRequest = jest.fn();
      ctx.ds.metadataRequest('/foo');
      expect(ctx.backendSrvMock.datasourceRequest.mock.calls.length).toBe(1);
      expect(ctx.backendSrvMock.datasourceRequest.mock.calls[0][0].method).toBe('GET');
    });

    it('should still perform a GET request with the DS HTTP method set to POST', () => {
      ctx.backendSrvMock.datasourceRequest = jest.fn();
      const postSettings = _.cloneDeep(instanceSettings);
      postSettings.jsonData.httpMethod = 'POST';
      const ds = new PrometheusDatasource(postSettings, q, ctx.backendSrvMock, ctx.templateSrvMock, ctx.timeSrvMock);
      ds.metadataRequest('/foo');
      expect(ctx.backendSrvMock.datasourceRequest.mock.calls.length).toBe(1);
      expect(ctx.backendSrvMock.datasourceRequest.mock.calls[0][0].method).toBe('GET');
    });
  });

  describe('When performing performSuggestQuery', () => {
    it('should cache response', async () => {
      ctx.backendSrvMock.datasourceRequest.mockReturnValue(
        Promise.resolve({
          status: 'success',
          data: { data: ['value1', 'value2', 'value3'] },
        })
      );

      let results = await ctx.ds.performSuggestQuery('value', true);

      expect(results).toHaveLength(3);

      ctx.backendSrvMock.datasourceRequest.mockReset();
      results = await ctx.ds.performSuggestQuery('value', true);

      expect(results).toHaveLength(3);
    });
  });

  describe('When converting prometheus histogram to heatmap format', () => {
    beforeEach(() => {
      ctx.query = {
        range: { from: moment(1443454528000), to: moment(1443454528000) },
        targets: [{ expr: 'test{job="testjob"}', format: 'heatmap', legendFormat: '{{le}}' }],
        interval: '60s',
      };
    });

    it('should convert cumullative histogram to ordinary', () => {
      const resultMock = [
        {
          metric: { __name__: 'metric', job: 'testjob', le: '10' },
          values: [[1443454528.0, '10'], [1443454528.0, '10']],
        },
        {
          metric: { __name__: 'metric', job: 'testjob', le: '20' },
          values: [[1443454528.0, '20'], [1443454528.0, '10']],
        },
        {
          metric: { __name__: 'metric', job: 'testjob', le: '30' },
          values: [[1443454528.0, '25'], [1443454528.0, '10']],
        },
      ];
      const responseMock = { data: { data: { result: resultMock } } };

      const expected = [
        {
          target: '10',
          datapoints: [[10, 1443454528000], [10, 1443454528000]],
        },
        {
          target: '20',
          datapoints: [[10, 1443454528000], [0, 1443454528000]],
        },
        {
          target: '30',
          datapoints: [[5, 1443454528000], [0, 1443454528000]],
        },
      ];

      ctx.ds.performTimeSeriesQuery = jest.fn().mockReturnValue(responseMock);
      return ctx.ds.query(ctx.query).then(result => {
        let results = result.data;
        return expect(results).toEqual(expected);
      });
    });

    it('should sort series by label value', () => {
      const resultMock = [
        {
          metric: { __name__: 'metric', job: 'testjob', le: '2' },
          values: [[1443454528.0, '10'], [1443454528.0, '10']],
        },
        {
          metric: { __name__: 'metric', job: 'testjob', le: '4' },
          values: [[1443454528.0, '20'], [1443454528.0, '10']],
        },
        {
          metric: { __name__: 'metric', job: 'testjob', le: '+Inf' },
          values: [[1443454528.0, '25'], [1443454528.0, '10']],
        },
        {
          metric: { __name__: 'metric', job: 'testjob', le: '1' },
          values: [[1443454528.0, '25'], [1443454528.0, '10']],
        },
      ];
      const responseMock = { data: { data: { result: resultMock } } };

      const expected = ['1', '2', '4', '+Inf'];

      ctx.ds.performTimeSeriesQuery = jest.fn().mockReturnValue(responseMock);
      return ctx.ds.query(ctx.query).then(result => {
        let seriesLabels = _.map(result.data, 'target');
        return expect(seriesLabels).toEqual(expected);
      });
    });
  });

  describe('Prometheus regular escaping', function() {
    it('should not escape simple string', function() {
      expect(prometheusRegularEscape('cryptodepression')).toEqual('cryptodepression');
    });
    it("should escape '", function() {
      expect(prometheusRegularEscape("looking'glass")).toEqual("looking\\\\'glass");
    });
    it('should escape multiple characters', function() {
      expect(prometheusRegularEscape("'looking'glass'")).toEqual("\\\\'looking\\\\'glass\\\\'");
    });
  });

  describe('Prometheus regexes escaping', function() {
    it('should not escape simple string', function() {
      expect(prometheusSpecialRegexEscape('cryptodepression')).toEqual('cryptodepression');
    });
    it('should escape $^*+?.()\\', function() {
      expect(prometheusSpecialRegexEscape("looking'glass")).toEqual("looking\\\\'glass");
      expect(prometheusSpecialRegexEscape('looking{glass')).toEqual('looking\\\\{glass');
      expect(prometheusSpecialRegexEscape('looking}glass')).toEqual('looking\\\\}glass');
      expect(prometheusSpecialRegexEscape('looking[glass')).toEqual('looking\\\\[glass');
      expect(prometheusSpecialRegexEscape('looking]glass')).toEqual('looking\\\\]glass');
      expect(prometheusSpecialRegexEscape('looking$glass')).toEqual('looking\\\\$glass');
      expect(prometheusSpecialRegexEscape('looking^glass')).toEqual('looking\\\\^glass');
      expect(prometheusSpecialRegexEscape('looking*glass')).toEqual('looking\\\\*glass');
      expect(prometheusSpecialRegexEscape('looking+glass')).toEqual('looking\\\\+glass');
      expect(prometheusSpecialRegexEscape('looking?glass')).toEqual('looking\\\\?glass');
      expect(prometheusSpecialRegexEscape('looking.glass')).toEqual('looking\\\\.glass');
      expect(prometheusSpecialRegexEscape('looking(glass')).toEqual('looking\\\\(glass');
      expect(prometheusSpecialRegexEscape('looking)glass')).toEqual('looking\\\\)glass');
      expect(prometheusSpecialRegexEscape('looking\\glass')).toEqual('looking\\\\\\\\glass');
    });
    it('should escape multiple special characters', function() {
      expect(prometheusSpecialRegexEscape('+looking$glass?')).toEqual('\\\\+looking\\\\$glass\\\\?');
    });
  });
});
