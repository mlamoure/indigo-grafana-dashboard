import { ResultTransformer } from '../result_transformer';

describe('Prometheus Result Transformer', () => {
  let ctx: any = {};

  beforeEach(() => {
    ctx.templateSrv = {
      replace: str => str,
    };
    ctx.resultTransformer = new ResultTransformer(ctx.templateSrv);
  });

  describe('When resultFormat is table', () => {
    var response = {
      status: 'success',
      data: {
        resultType: 'matrix',
        result: [
          {
            metric: { __name__: 'test', job: 'testjob' },
            values: [[1443454528, '3846']],
          },
          {
            metric: {
              __name__: 'test',
              instance: 'localhost:8080',
              job: 'otherjob',
            },
            values: [[1443454529, '3847']],
          },
        ],
      },
    };

    it('should return table model', () => {
      var table = ctx.resultTransformer.transformMetricDataToTable(response.data.result);
      expect(table.type).toBe('table');
      expect(table.rows).toEqual([
        [1443454528000, 'test', '', 'testjob', 3846],
        [1443454529000, 'test', 'localhost:8080', 'otherjob', 3847],
      ]);
      expect(table.columns).toEqual([
        { text: 'Time', type: 'time' },
        { text: '__name__' },
        { text: 'instance' },
        { text: 'job' },
        { text: 'Value' },
      ]);
    });

    it('should column title include refId if response count is more than 2', () => {
      var table = ctx.resultTransformer.transformMetricDataToTable(response.data.result, 2, 'B');
      expect(table.type).toBe('table');
      expect(table.columns).toEqual([
        { text: 'Time', type: 'time' },
        { text: '__name__' },
        { text: 'instance' },
        { text: 'job' },
        { text: 'Value #B' },
      ]);
    });
  });

  describe('When resultFormat is table and instant = true', () => {
    var response = {
      status: 'success',
      data: {
        resultType: 'vector',
        result: [
          {
            metric: { __name__: 'test', job: 'testjob' },
            value: [1443454528, '3846'],
          },
        ],
      },
    };

    it('should return table model', () => {
      var table = ctx.resultTransformer.transformMetricDataToTable(response.data.result);
      expect(table.type).toBe('table');
      expect(table.rows).toEqual([[1443454528000, 'test', 'testjob', 3846]]);
      expect(table.columns).toEqual([
        { text: 'Time', type: 'time' },
        { text: '__name__' },
        { text: 'job' },
        { text: 'Value' },
      ]);
    });
  });

  describe('When resultFormat is heatmap', () => {
    var response = {
      status: 'success',
      data: {
        resultType: 'matrix',
        result: [
          {
            metric: { __name__: 'test', job: 'testjob', le: '1' },
            values: [[1445000010, '10'], [1445000020, '10'], [1445000030, '0']],
          },
          {
            metric: { __name__: 'test', job: 'testjob', le: '2' },
            values: [[1445000010, '20'], [1445000020, '10'], [1445000030, '30']],
          },
          {
            metric: { __name__: 'test', job: 'testjob', le: '3' },
            values: [[1445000010, '30'], [1445000020, '10'], [1445000030, '40']],
          },
        ],
      },
    };

    it('should convert cumulative histogram to regular', () => {
      let result = [];
      let options = {
        format: 'heatmap',
        start: 1445000010,
        end: 1445000030,
        legendFormat: '{{le}}',
      };

      ctx.resultTransformer.transform(result, { data: response }, options);
      expect(result).toEqual([
        { target: '1', datapoints: [[10, 1445000010000], [10, 1445000020000], [0, 1445000030000]] },
        { target: '2', datapoints: [[10, 1445000010000], [0, 1445000020000], [30, 1445000030000]] },
        { target: '3', datapoints: [[10, 1445000010000], [0, 1445000020000], [10, 1445000030000]] },
      ]);
    });
  });

  describe('When resultFormat is time series', () => {
    it('should transform matrix into timeseries', () => {
      const response = {
        status: 'success',
        data: {
          resultType: 'matrix',
          result: [
            {
              metric: { __name__: 'test', job: 'testjob' },
              values: [[0, '10'], [1, '10'], [2, '0']],
            },
          ],
        },
      };
      let result = [];
      let options = {
        format: 'timeseries',
        start: 0,
        end: 2,
      };

      ctx.resultTransformer.transform(result, { data: response }, options);
      expect(result).toEqual([{ target: 'test{job="testjob"}', datapoints: [[10, 0], [10, 1000], [0, 2000]] }]);
    });

    it('should fill timeseries with null values', () => {
      const response = {
        status: 'success',
        data: {
          resultType: 'matrix',
          result: [
            {
              metric: { __name__: 'test', job: 'testjob' },
              values: [[1, '10'], [2, '0']],
            },
          ],
        },
      };
      let result = [];
      let options = {
        format: 'timeseries',
        step: 1,
        start: 0,
        end: 2,
      };

      ctx.resultTransformer.transform(result, { data: response }, options);
      expect(result).toEqual([{ target: 'test{job="testjob"}', datapoints: [[null, 0], [10, 1000], [0, 2000]] }]);
    });

    it('should align null values with step', () => {
      const response = {
        status: 'success',
        data: {
          resultType: 'matrix',
          result: [
            {
              metric: { __name__: 'test', job: 'testjob' },
              values: [[4, '10'], [8, '10']],
            },
          ],
        },
      };
      let result = [];
      let options = {
        format: 'timeseries',
        step: 2,
        start: 0,
        end: 8,
      };

      ctx.resultTransformer.transform(result, { data: response }, options);
      expect(result).toEqual([
        { target: 'test{job="testjob"}', datapoints: [[null, 0], [null, 2000], [10, 4000], [null, 6000], [10, 8000]] },
      ]);
    });
  });
});
